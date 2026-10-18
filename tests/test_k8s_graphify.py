#!/usr/bin/env python3
"""
Unit tests for .agent/skills/skill-graphify/scripts/k8s_graphify_extract.py.
Tests redaction security, secret scanning, edge generation, and Graphify JSON format.
"""

import json
import os
import sys
import unittest
from pathlib import Path

# Add skill-graphify scripts to sys.path
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-graphify" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import k8s_graphify_extract as kge  # noqa: E402

FAKE_B64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVowMTIzNDU2Nzg5YWJjZGVm"
FAKE_KEY = "-----BEGIN PRIVATE KEY-----\nMIIBVQIBADANBgkq\n-----END PRIVATE KEY-----"


def make_deployment():
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "cloud-boot-app-workload",
            "namespace": "cloud-boot-app",
            "labels": {"app.kubernetes.io/name": "cloud-boot-app"},
            "annotations": {"kubectl.kubernetes.io/last-applied-configuration": '{"password":"test-secret-value"}'},
            "managedFields": [{"manager": "kubectl", "fieldsV1": {"f:spec": {}}}],
        },
        "spec": {
            "replicas": 2,
            "selector": {"matchLabels": {"app.kubernetes.io/name": "cloud-boot-app"}},
            "template": {
                "metadata": {"labels": {"app.kubernetes.io/name": "cloud-boot-app"}},
                "spec": {
                    "containers": [
                        {
                            "name": "app",
                            "image": "cloud-boot-app:0.0.3",
                            "env": [
                                {"name": "PLAIN_ENV", "value": "plain-literal"},
                                {
                                    "name": "DB_PASSWORD",
                                    "valueFrom": {"secretKeyRef": {"name": "cloud-boot-db-secret", "key": "password"}},
                                },
                            ],
                        }
                    ]
                },
            },
        },
    }


class RedactionSecurityTests(unittest.TestCase):
    def test_secret_kind_omits_data_and_string_data(self):
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "type": "Opaque",
            "metadata": {"name": "db-creds", "namespace": "cloud-boot-app"},
            "data": {"password": FAKE_B64},
            "stringData": {"raw": "secret123"},
        }
        out = kge.redact(secret)
        self.assertEqual(out["metadata"]["name"], "db-creds")
        self.assertNotIn("data", out)
        self.assertNotIn("stringData", out)
        self.assertNotIn(FAKE_B64, json.dumps(out))
        self.assertNotIn("secret123", json.dumps(out))

    def test_strips_managed_fields_and_last_applied_config(self):
        dep = make_deployment()
        out = kge.redact(dep)
        dump = json.dumps(out)
        self.assertNotIn("managedFields", dump)
        self.assertNotIn("last-applied-configuration", dump)
        self.assertNotIn("test-secret-value", dump)

    def test_strips_env_literal_values_keeps_secret_refs(self):
        dep = make_deployment()
        out = kge.redact(dep)
        dump = json.dumps(out)
        self.assertNotIn("plain-literal", dump)
        self.assertIn("cloud-boot-db-secret", dump)

    def test_replaces_sensitive_leaf_keys(self):
        custom = {
            "apiVersion": "custom.io/v1",
            "kind": "CustomResource",
            "metadata": {"name": "test", "namespace": "default"},
            "spec": {"password": "my-secret-password", "apiToken": "tok_12345", "safeField": "visible_value"},
        }
        out = kge.redact(custom)
        self.assertEqual(out["spec"]["password"], kge.REDACTED)
        self.assertEqual(out["spec"]["apiToken"], kge.REDACTED)
        self.assertEqual(out["spec"]["safeField"], "visible_value")

    def test_strips_url_embedded_credentials(self):
        app = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Application",
            "metadata": {"name": "cba", "namespace": "argocd"},
            "spec": {"source": {"repoURL": "https://deployer:secret_token@github.com/org/repo.git", "path": "helm"}},
        }
        out = kge.redact(app)
        self.assertEqual(out["spec"]["source"]["repoURL"], "https://github.com/org/repo.git")


class SecretScanningTests(unittest.TestCase):
    def test_flags_base64_pem_and_credentials(self):
        self.assertTrue(bool(kge.scan_for_secrets({"key": FAKE_KEY})))
        self.assertTrue(bool(kge.scan_for_secrets({"blob": FAKE_B64})))
        self.assertTrue(bool(kge.scan_for_secrets({"password": "live_unredacted_password"})))

    def test_permits_redacted_placeholders(self):
        self.assertEqual(kge.scan_for_secrets({"password": kge.REDACTED}), [])

    def test_clean_deployment_passes_scan(self):
        dep = kge.redact(make_deployment())
        self.assertEqual(kge.scan_for_secrets(dep), [])


class GraphifyRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.objects = [
            kge.redact(make_deployment()),
            kge.redact(
                {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {"name": "cloud-boot-app-workload", "namespace": "cloud-boot-app"},
                    "spec": {
                        "selector": {"app.kubernetes.io/name": "cloud-boot-app"},
                        "ports": [{"port": 8090, "targetPort": 8090}],
                    },
                }
            ),
            kge.redact(
                {
                    "apiVersion": "networking.k8s.io/v1",
                    "kind": "Ingress",
                    "metadata": {"name": "cloud-boot-app", "namespace": "cloud-boot-app"},
                    "spec": {
                        "rules": [
                            {
                                "host": "cloud-boot.homelab.internal",
                                "http": {
                                    "paths": [
                                        {
                                            "path": "/",
                                            "pathType": "Prefix",
                                            "backend": {
                                                "service": {"name": "cloud-boot-app-workload", "port": {"number": 8090}}
                                            },
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            ),
            kge.redact(
                {
                    "apiVersion": "postgresql.acid.zalan.do/v1",
                    "kind": "postgresql",
                    "metadata": {"name": "cloud-boot-db", "namespace": "cloud-boot-app"},
                    "spec": {"teamId": "acid", "numberOfInstances": 1, "volume": {"size": "1Gi"}},
                }
            ),
            kge.redact(
                {
                    "apiVersion": "database.example.org/v1alpha1",
                    "kind": "CloudBootApp",
                    "metadata": {"name": "my-cloud-boot-app-local", "namespace": "default"},
                    "spec": {
                        "resourceRef": {
                            "apiVersion": "database.example.org/v1alpha1",
                            "kind": "XCloudBootApp",
                            "name": "my-cloud-boot-app-local-xd5kd",
                        }
                    },
                }
            ),
            kge.redact(
                {
                    "apiVersion": "database.example.org/v1alpha1",
                    "kind": "XCloudBootApp",
                    "metadata": {"name": "my-cloud-boot-app-local-xd5kd"},
                    "spec": {"compositionRef": {"name": "cloud-boot-app-local"}},
                }
            ),
        ]

    def test_builds_valid_graphify_schema(self):
        graph = kge.build_graphify_k8s_graph(self.objects)
        self.assertIn("directed", graph)
        self.assertIn("multigraph", graph)
        self.assertIn("nodes", graph)
        self.assertIn("links", graph)
        self.assertTrue(len(graph["nodes"]) >= 6)

    def test_extracts_service_selector_edge(self):
        graph = kge.build_graphify_k8s_graph(self.objects)
        links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in graph["links"]}
        self.assertIn(
            (
                "k8s:core/Service/cloud-boot-app/cloud-boot-app-workload",
                "selects",
                "k8s:apps/Deployment/cloud-boot-app/cloud-boot-app-workload",
            ),
            links,
        )

    def test_extracts_ingress_routing_edge(self):
        graph = kge.build_graphify_k8s_graph(self.objects)
        links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in graph["links"]}
        self.assertIn(
            (
                "k8s:networking.k8s.io/Ingress/cloud-boot-app/cloud-boot-app",
                "routes-to",
                "k8s:core/Service/cloud-boot-app/cloud-boot-app-workload",
            ),
            links,
        )

    def test_extracts_crossplane_composition_edge(self):
        graph = kge.build_graphify_k8s_graph(self.objects)
        links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in graph["links"]}
        self.assertIn(
            (
                "k8s:database.example.org/XCloudBootApp/_cluster_/my-cloud-boot-app-local-xd5kd",
                "uses-composition",
                "k8s:apiextensions.crossplane.io/Composition/_cluster_/cloud-boot-app-local",
            ),
            links,
        )

    def test_generic_secret_ref_and_resource_refs_edges(self):
        xr = kge.redact(
            {
                "apiVersion": "custom.example.org/v1",
                "kind": "XCustomPlatform",
                "metadata": {"name": "plat-1"},
                "spec": {
                    "compositionRef": {"name": "plat-comp"},
                    "writeConnectionSecretToRef": {"name": "plat-conn", "namespace": "cloud-boot-app"},
                    "resourceRefs": [
                        {"apiVersion": "apps/v1", "kind": "Deployment", "name": "cloud-boot-app-workload"}
                    ],
                },
            }
        )
        graph = kge.build_graphify_k8s_graph(self.objects + [xr])
        links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in graph["links"]}
        self.assertIn(
            (
                "k8s:custom.example.org/XCustomPlatform/_cluster_/plat-1",
                "uses-composition",
                "k8s:apiextensions.crossplane.io/Composition/_cluster_/plat-comp",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:custom.example.org/XCustomPlatform/_cluster_/plat-1",
                "references-secret",
                "k8s:core/Secret/cloud-boot-app/plat-conn",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:apps/Deployment/cloud-boot-app/cloud-boot-app-workload",
                "references-secret",
                "k8s:core/Secret/cloud-boot-app/cloud-boot-db-secret",
            ),
            links,
        )


class HardeningAndBridgeTests(unittest.TestCase):
    def test_write_graph_atomic_enforces_0600_and_blocks_leaks(self):
        import stat
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "clean.json"
            kge.write_graph_atomic(out, {"nodes": [], "links": []})
            self.assertEqual(stat.S_IMODE(os.stat(out).st_mode), 0o600)

            bad = Path(d) / "leaked.json"
            with self.assertRaises(kge.SecretLeakError):
                kge.write_graph_atomic(bad, {"nodes": [{"password": "raw-secret-value"}], "links": []})
            self.assertFalse(bad.exists())

    def test_prod_context_refused_unless_allowed(self):
        with self.assertRaises(SystemExit):
            kge.check_prod_context("gke_corp_us-central1_prod-cluster", allow_prod_read=False)
        kge.check_prod_context("gke_corp_us-central1_prod-cluster", allow_prod_read=True)
        kge.check_prod_context("k3s-homelab-dev", allow_prod_read=False)

    def test_dynamic_manifest_bridge_and_ast_enrichment(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            manifest = Path(d) / "k8s" / "custom-svc.yaml"
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                "apiVersion: v1\nkind: Service\nmetadata:\n  name: custom-svc\n"
                "  namespace: app\nspec:\n  ports: [{port: 80}]\n"
            )
            base_graph = {
                "nodes": [
                    {"id": "file:k8s/custom-svc.yaml", "label": "custom-svc.yaml", "source_file": str(manifest)},
                    {"id": "class:DataController", "label": "DataController", "source_file": "src/DataController.java"},
                ],
                "links": [],
            }
            k8s_graph = kge.build_graphify_k8s_graph(
                [
                    kge.redact(
                        {
                            "apiVersion": "v1",
                            "kind": "Service",
                            "metadata": {"name": "custom-svc", "namespace": "app"},
                            "spec": {"ports": [{"port": 80}]},
                        }
                    )
                ]
            )
            merged = kge.merge_graphify_graphs(base_graph, k8s_graph, manifest_dirs=[d])
            links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in merged["links"]}
            self.assertIn(
                ("file:k8s/custom-svc.yaml", "manifest-of", "k8s:core/Service/app/custom-svc"),
                links,
            )
            records = [
                {
                    "record_type": "controller_declaration",
                    "record_id": "src/DataController.java#DataController:10",
                    "path": "src/DataController.java",
                    "source_name": "DataController",
                    "source_scope": "web_layer",
                    "line": 10,
                    "extracted_data": {"class": "DataController"},
                }
            ]
            enriched = kge.enrich_with_ast_records(merged, records)
            ctrl_node = next(n for n in enriched["nodes"] if n["id"] == "class:DataController")
            self.assertEqual(ctrl_node["properties"]["ast_records"][0]["record_type"], "controller_declaration")

    def test_redacts_and_scans_lists_under_sensitive_keys(self):
        obj = {
            "apiVersion": "custom.io/v1",
            "kind": "SecretConfig",
            "metadata": {"name": "cfg", "namespace": "app"},
            "spec": {
                "passwords": ["hunter2", "s3cr3t"],
                "tokens": ["tok_a", "tok_b"],
            },
        }
        redacted = kge.redact(obj)
        self.assertEqual(redacted["spec"]["passwords"], [kge.REDACTED, kge.REDACTED])
        self.assertEqual(redacted["spec"]["tokens"], [kge.REDACTED, kge.REDACTED])
        self.assertEqual(kge.scan_for_secrets(redacted), [])
        # Unredacted list under sensitive key must be caught by scan_for_secrets
        self.assertTrue(bool(kge.scan_for_secrets(obj)))

    def test_context_propagates_to_kubectl_subprocess(self):
        captured_cmds = []

        def fake_run(cmd, **kwargs):
            captured_cmds.append(cmd)

            class R:
                returncode = 0
                stdout = '{"kind": "List", "items": []}'
                stderr = ""

            return R()

        orig_run = kge.subprocess.run
        kge.subprocess.run = fake_run
        try:
            kge.fetch_cluster_resources(namespace="app", context="staging-ctx", dynamic_discovery=False)
        finally:
            kge.subprocess.run = orig_run
        self.assertTrue(captured_cmds)
        for cmd in captured_cmds:
            self.assertIn("--context", cmd)
            self.assertEqual(cmd[cmd.index("--context") + 1], "staging-ctx")

    def test_enrich_with_ast_records_rejects_partial_filename_collision(self):
        graph = {
            "nodes": [
                {
                    "id": "file:user_controller.py",
                    "label": "user_controller.py",
                    "source_file": "src/user_controller.py",
                },
                {"id": "file:controller.py", "label": "controller.py", "source_file": "src/controller.py"},
            ],
            "links": [],
        }
        records = [
            {
                "record_type": "controller_declaration",
                "record_id": "controller.py#Base:1",
                "path": "controller.py",
                "source_name": "Base",
                "source_scope": "web_layer",
                "line": 1,
                "extracted_data": {},
            }
        ]
        enriched = kge.enrich_with_ast_records(graph, records)
        by_id = {n["id"]: n for n in enriched["nodes"]}
        self.assertNotIn("ast_records", by_id["file:user_controller.py"].get("properties", {}))
        self.assertIn("ast_records", by_id["file:controller.py"].get("properties", {}))

        # When multiple symbols exist in the same file, only the matching symbol gets the AST record
        multi_symbol_graph = {
            "nodes": [
                {"id": "class:Base", "label": "Base", "source_file": "src/controller.py"},
                {"id": "class:Helper", "label": "Helper", "source_file": "src/controller.py"},
            ],
            "links": [],
        }
        enriched_sym = kge.enrich_with_ast_records(multi_symbol_graph, records)
        sym_by_id = {n["id"]: n for n in enriched_sym["nodes"]}
        self.assertIn("ast_records", sym_by_id["class:Base"].get("properties", {}))
        self.assertNotIn("ast_records", sym_by_id["class:Helper"].get("properties", {}))

    def test_rbac_networkpolicy_and_domain_hyperedges(self):
        objs = [
            kge.redact(
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "order-service", "namespace": "app"},
                    "spec": {
                        "template": {
                            "metadata": {"labels": {"app": "order", "tier": "backend"}},
                            "spec": {"serviceAccountName": "order-sa"},
                        }
                    },
                }
            ),
            kge.redact(
                {
                    "apiVersion": "v1",
                    "kind": "ServiceAccount",
                    "metadata": {"name": "order-sa", "namespace": "app"},
                }
            ),
            kge.redact(
                {
                    "apiVersion": "rbac.authorization.k8s.io/v1",
                    "kind": "RoleBinding",
                    "metadata": {"name": "order-rb", "namespace": "app"},
                    "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "order-role"},
                    "subjects": [{"kind": "ServiceAccount", "name": "order-sa", "namespace": "app"}],
                }
            ),
            kge.redact(
                {
                    "apiVersion": "networking.k8s.io/v1",
                    "kind": "NetworkPolicy",
                    "metadata": {"name": "order-netpol", "namespace": "app"},
                    "spec": {
                        "podSelector": {"matchLabels": {"app": "order"}},
                        "ingress": [{"from": [{"podSelector": {"matchLabels": {"app": "gateway"}}}]}],
                    },
                }
            ),
            kge.redact(
                {
                    "apiVersion": "networking.k8s.io/v1",
                    "kind": "NetworkPolicy",
                    "metadata": {"name": "default-deny-all", "namespace": "app"},
                    "spec": {"podSelector": {}, "policyTypes": ["Ingress"]},
                }
            ),
            kge.redact(
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "api-gateway", "namespace": "app"},
                    "spec": {"template": {"metadata": {"labels": {"app": "gateway"}}}},
                }
            ),
        ]
        g = kge.build_graphify_k8s_graph(objs)
        links = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in g["links"]}
        self.assertIn(
            ("k8s:apps/Deployment/app/order-service", "uses-serviceaccount", "k8s:core/ServiceAccount/app/order-sa"),
            links,
        )
        self.assertIn(
            (
                "k8s:rbac.authorization.k8s.io/RoleBinding/app/order-rb",
                "grants-role",
                "k8s:rbac.authorization.k8s.io/Role/app/order-role",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:rbac.authorization.k8s.io/RoleBinding/app/order-rb",
                "binds-subject",
                "k8s:core/ServiceAccount/app/order-sa",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:networking.k8s.io/NetworkPolicy/app/order-netpol",
                "isolates-workload",
                "k8s:apps/Deployment/app/order-service",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:networking.k8s.io/NetworkPolicy/app/default-deny-all",
                "isolates-workload",
                "k8s:apps/Deployment/app/order-service",
            ),
            links,
        )
        self.assertIn(
            (
                "k8s:networking.k8s.io/NetworkPolicy/app/default-deny-all",
                "isolates-workload",
                "k8s:apps/Deployment/app/api-gateway",
            ),
            links,
        )
        self.assertIn(
            ("k8s:apps/Deployment/app/api-gateway", "allowed-by-netpol", "k8s:apps/Deployment/app/order-service"), links
        )

        import tempfile

        with tempfile.TemporaryDirectory() as d:
            doc_p = Path(d) / "ADR-001-order.md"
            doc_p.write_text(
                "# ADR 001: Order Service\nCovers OrderService and `order-service` deployment plus table `orders`.\n"
            )
            sql_p = Path(d) / "V1__init.sql"
            sql_p.write_text("CREATE TABLE orders (id BIGINT PRIMARY KEY);\n")
            g["nodes"].append(
                {
                    "id": "OrderService",
                    "label": "class: OrderService",
                    "file_type": "class",
                    "source_file": "OrderService.java",
                }
            )
            g_hyper = kge.build_domain_hyperedges(g, doc_dirs=[d])
            self.assertTrue(len(g_hyper["hyperedges"]) >= 1)
            he_nodes = set(g_hyper["hyperedges"][0]["nodes"])
            self.assertIn("OrderService", he_nodes)
            self.assertIn("k8s:apps/Deployment/app/order-service", he_nodes)
            merged_hyper = kge.merge_graphify_graphs(g_hyper, {"nodes": [], "links": []})
            self.assertTrue(len(merged_hyper.get("hyperedges", [])) >= 1)


if __name__ == "__main__":
    unittest.main()
