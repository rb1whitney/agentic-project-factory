#!/usr/bin/env python3
"""Characterization tests for skill-code-map/scripts/k8s_catalog.py (pure functions, no cluster)."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import k8s_catalog as kc  # noqa: E402

FAKE_B64 = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVowMTIzNDU2Nzg5YWJjZGVm"


class RedactionTests(unittest.TestCase):
    def test_secret_kind_keeps_only_identity(self):
        out = kc.redact(
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "type": "Opaque",
                "metadata": {"name": "s", "namespace": "n"},
                "data": {"password": FAKE_B64},
                "stringData": {"x": "y"},
            }
        )
        self.assertEqual(out["metadata"]["name"], "s")
        self.assertNotIn("data", out)
        self.assertNotIn("stringData", out)
        self.assertNotIn(FAKE_B64, json.dumps(out))

    def test_strips_managed_fields_and_last_applied(self):
        out = kc.redact(
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "web",
                    "namespace": "app",
                    "annotations": {"kubectl.kubernetes.io/last-applied-configuration": '{"password":"hunter2"}'},
                    "managedFields": [{"manager": "kubectl"}],
                },
                "spec": {"replicas": 2},
            }
        )
        blob = json.dumps(out)
        for bad in ("managedFields", "last-applied", "hunter2"):
            self.assertNotIn(bad, blob)
        self.assertEqual(out["spec"]["replicas"], 2)

    def test_env_values_dropped_secret_ref_name_kept(self):
        out = kc.redact(
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "web"},
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "c",
                                    "image": "web:1",
                                    "env": [
                                        {"name": "PLAIN", "value": "literal-value"},
                                        {
                                            "name": "DB_PASS",
                                            "valueFrom": {"secretKeyRef": {"name": "db-creds", "key": "password"}},
                                        },
                                    ],
                                }
                            ]
                        }
                    }
                },
            }
        )
        blob = json.dumps(out)
        self.assertNotIn("literal-value", blob)
        self.assertIn("db-creds", blob)

    def test_sensitive_leaf_keys_replaced(self):
        spec = kc.redact(
            {
                "apiVersion": "example.org/v1",
                "kind": "Thing",
                "metadata": {"name": "t"},
                "spec": {"password": "p4ss", "apiKey": "k", "tlsSecretName": "tls-cert", "name": "ok"},
            }
        )["spec"]
        self.assertEqual(spec["password"], kc.REDACTED)
        self.assertEqual(spec["apiKey"], kc.REDACTED)
        self.assertEqual(spec["tlsSecretName"], "tls-cert")
        self.assertEqual(spec["name"], "ok")

    def test_url_credentials_stripped(self):
        out = kc.redact(
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {"name": "a"},
                "spec": {"source": {"repoURL": "https://user:tok3n@github.com/o/r.git", "path": "crossplane"}},
            }
        )
        self.assertEqual(out["spec"]["source"]["repoURL"], "https://github.com/o/r.git")
        self.assertEqual(out["spec"]["source"]["path"], "crossplane")


class SecretScanTests(unittest.TestCase):
    def test_flags_pem_base64_and_jwt(self):
        pem = "-----BEGIN PRIVATE KEY-----\nMIIB\n-----END PRIVATE KEY-----"
        self.assertTrue(kc.scan_for_secrets({"a": pem}))
        self.assertTrue(kc.scan_for_secrets({"a": {"b": [FAKE_B64]}}))
        self.assertTrue(kc.scan_for_secrets({"a": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"}))

    def test_flags_sensitive_key_with_live_value(self):
        self.assertTrue(kc.scan_for_secrets({"password": "hunter2"}))
        self.assertFalse(kc.scan_for_secrets({"password": kc.REDACTED}))

    def test_redacted_secret_is_clean(self):
        obj = {"apiVersion": "v1", "kind": "Secret", "metadata": {"name": "s"}, "data": {"password": FAKE_B64}}
        self.assertEqual(kc.scan_for_secrets(kc.redact(obj)), [])

    def test_hex_hash_label_not_flagged(self):
        self.assertEqual(
            kc.scan_for_secrets({"labels": {"crossplane.io/composition-hash": "0c8be18" * 9 + "abcd"}}), []
        )

    def test_image_digest_and_ref_names_not_flagged(self):
        self.assertEqual(kc.scan_for_secrets({"image": "x@sha256:" + "a" * 64, "tlsSecretName": "tls"}), [])


class OpenApiTests(unittest.TestCase):
    DOC = {
        "components": {
            "schemas": {
                "io.example.v2.Widget": {
                    "x-kubernetes-group-version-kind": [{"group": "example.org", "version": "v2", "kind": "Widget"}],
                    "properties": {
                        "spec": {
                            "properties": {
                                "compositionRef": {"properties": {"name": {"type": "string"}}},
                                "writeConnectionSecretToRef": {"properties": {"name": {"type": "string"}}},
                                "size": {"type": "string"},
                                "owner": {"$ref": "#/components/schemas/io.example.v2.Owner"},
                            }
                        }
                    },
                },
                "io.example.v2.Owner": {"properties": {"secretRef": {"properties": {"name": {"type": "string"}}}}},
            }
        }
    }

    def test_gvk_and_ref_fields(self):
        entry = kc.parse_openapi_v3(self.DOC)["example.org/Widget"]
        self.assertEqual(entry["versions"], ["v2"])
        for f in ("spec.compositionRef", "spec.writeConnectionSecretToRef", "spec.owner.secretRef"):
            self.assertIn(f, entry["ref_fields"])
        self.assertNotIn("spec.size", entry["ref_fields"])

    def test_merge_and_crd_overlay(self):
        merged = kc.merge_catalogs(
            [
                kc.parse_openapi_v3(self.DOC),
                {"example.org/Widget": {"versions": ["v1"], "ref_fields": ["spec.compositionRef"]}},
            ]
        )
        self.assertEqual(merged["example.org/Widget"]["versions"], ["v1", "v2"])
        kc.apply_crd_overlay(
            merged,
            {
                "items": [
                    {
                        "spec": {
                            "group": "example.org",
                            "scope": "Namespaced",
                            "names": {"kind": "Widget", "plural": "widgets"},
                            "versions": [
                                {"name": "v1", "served": True, "storage": False},
                                {"name": "v2", "served": True, "storage": True},
                            ],
                        }
                    }
                ]
            },
        )
        w = merged["example.org/Widget"]
        self.assertEqual((w["storage_version"], w["scope"], w["plural"]), ("v2", "Namespaced", "widgets"))

    def test_node_key_ignores_version(self):
        self.assertEqual(kc.gk("apps/v1", "Deployment"), "apps/Deployment")
        self.assertEqual(kc.gk("v1", "Service"), "core/Service")
        self.assertEqual(kc.gk("example.org/v2", "Widget"), kc.gk("example.org/v1", "Widget"))


class EdgeTests(unittest.TestCase):
    def edges(self):
        raw = [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": "web",
                    "namespace": "app",
                    "ownerReferences": [
                        {"apiVersion": "argoproj.io/v1alpha1", "kind": "Application", "name": "web-app"}
                    ],
                },
                "spec": {
                    "template": {
                        "metadata": {"labels": {"app": "web"}},
                        "spec": {
                            "containers": [
                                {
                                    "name": "c",
                                    "env": [
                                        {
                                            "name": "P",
                                            "valueFrom": {"secretKeyRef": {"name": "db-creds", "key": "password"}},
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                },
            },
            {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {"name": "web-svc", "namespace": "app"},
                "spec": {"selector": {"app": "web"}},
            },
            {
                "apiVersion": "networking.k8s.io/v1",
                "kind": "Ingress",
                "metadata": {"name": "ing", "namespace": "app"},
                "spec": {"rules": [{"http": {"paths": [{"backend": {"service": {"name": "web-svc"}}}]}}]},
            },
            {
                "apiVersion": "example.org/v1",
                "kind": "Widget",
                "metadata": {"name": "w", "namespace": "app"},
                "spec": {
                    "compositionRef": {"name": "comp-a"},
                    "resourceRefs": [{"apiVersion": "v1", "kind": "Service", "name": "web-svc"}],
                },
            },
            {
                "apiVersion": "apiextensions.crossplane.io/v1",
                "kind": "Composition",
                "metadata": {"name": "comp-a"},
                "spec": {"compositeTypeRef": {"apiVersion": "example.org/v1", "kind": "Widget"}},
            },
            {
                "apiVersion": "argoproj.io/v1alpha1",
                "kind": "Application",
                "metadata": {"name": "web-app", "namespace": "argocd"},
                "spec": {
                    "destination": {"namespace": "app"},
                    "source": {"repoURL": "https://github.com/o/r.git", "path": "p"},
                },
            },
        ]
        return {(e["from"], e["type"], e["to"]) for e in kc.build_edges([kc.redact(o) for o in raw])}

    def test_owner_reference(self):
        self.assertIn(("apps/Deployment/app/web", "owned-by", "argoproj.io/Application/app/web-app"), self.edges())

    def test_service_selects_workload_by_labels(self):
        self.assertIn(("core/Service/app/web-svc", "selects", "apps/Deployment/app/web"), self.edges())

    def test_ingress_routes_to_service(self):
        self.assertIn(("networking.k8s.io/Ingress/app/ing", "routes-to", "core/Service/app/web-svc"), self.edges())

    def test_secret_reference_by_name(self):
        self.assertIn(("apps/Deployment/app/web", "references-secret", "core/Secret/app/db-creds"), self.edges())

    def test_crossplane_edges(self):
        e = self.edges()
        self.assertIn(
            ("example.org/Widget/app/w", "uses-composition", "apiextensions.crossplane.io/Composition//comp-a"), e
        )
        self.assertIn(("example.org/Widget/app/w", "composes", "core/Service/app/web-svc"), e)
        self.assertIn(
            ("apiextensions.crossplane.io/Composition//comp-a", "composes-type", "kind:example.org/Widget"), e
        )

    def test_argocd_edges(self):
        e = self.edges()
        self.assertIn(("argoproj.io/Application/argocd/web-app", "deploys-to", "core/Namespace//app"), e)
        self.assertIn(("argoproj.io/Application/argocd/web-app", "sources-from", "repo:https://github.com/o/r.git"), e)


class CollectTests(unittest.TestCase):
    """collect() with kubectl mocked: verifies Secrets are never listed and output is clean."""

    def test_collect_never_lists_secrets_and_is_clean(self):
        calls = []

        def fake(*args):
            calls.append(args)
            if args[:2] == ("api-resources", "--verbs=list"):
                return "deployments.apps\nsecrets\nservices\nwidgets.example.org\nconfigmaps\n"
            if args[:2] == ("get", "--raw"):
                return json.dumps({"paths": {}}) if args[2] == "/openapi/v3" else json.dumps({"items": []})
            res = args[1]
            items = {
                "deployments.apps": [
                    {
                        "apiVersion": "apps/v1",
                        "kind": "Deployment",
                        "metadata": {"name": "web", "namespace": "app"},
                        "spec": {"template": {"spec": {"containers": [{"env": [{"name": "A", "value": "hunter2"}]}]}}},
                    }
                ],
                "services": [
                    {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "s", "namespace": "other"}, "spec": {}}
                ],
                "widgets.example.org": [],
            }.get(res, [])
            return json.dumps({"items": items})

        original = kc._kubectl
        kc._kubectl = fake
        try:
            graph = kc.collect(groups=["core", "apps", "example.org"], namespaces=["app"])
        finally:
            kc._kubectl = original
        listed = [a[1] for a in calls if a[0] == "get" and a[1] != "--raw"]
        self.assertNotIn("secrets", listed)
        self.assertNotIn("configmaps", listed)  # core group requested, but configmaps hold arbitrary data
        self.assertEqual(list(graph["nodes"]), ["apps/Deployment/app/web"])  # namespace filter applied
        self.assertEqual(kc.scan_for_secrets(graph), [])


class CacheWriteTests(unittest.TestCase):
    def test_writes_0600(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sub" / "cache.json"
            kc.write_cache(p, {"nodes": {}, "edges": []})
            self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600)

    def test_refuses_when_secret_survives(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "cache.json"
            with self.assertRaises(kc.SecretLeakError):
                kc.write_cache(p, {"nodes": {"x": {"password": "hunter2"}}, "edges": []})
            self.assertFalse(p.exists())

    def test_to_graphify_exports_valid_node_link_schema(self):
        raw = [
            kc.redact(
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "metadata": {"name": "web", "namespace": "app"},
                    "spec": {"template": {"metadata": {"labels": {"app": "web"}}}},
                }
            ),
            kc.redact(
                {
                    "apiVersion": "v1",
                    "kind": "Service",
                    "metadata": {"name": "web-svc", "namespace": "app"},
                    "spec": {"selector": {"app": "web"}},
                }
            ),
        ]
        cat_graph = {
            "catalog": {"apps/Deployment": {"versions": ["v1"], "ref_fields": []}},
            "nodes": {
                kc.node_id(o["apiVersion"], o["kind"], o["metadata"].get("namespace", ""), o["metadata"]["name"]): o
                for o in raw
            },
            "edges": kc.build_edges(raw),
            "stats": {"kinds": 1, "objects": 2},
        }
        g = kc.to_graphify(cat_graph)
        self.assertTrue(g["directed"])
        self.assertEqual(len(g["nodes"]), 2)
        node_ids = {n["id"] for n in g["nodes"]}
        self.assertIn("k8s:apps/Deployment/app/web", node_ids)
        self.assertIn("k8s:core/Service/app/web-svc", node_ids)
        self.assertEqual(len(g["links"]), 1)
        self.assertEqual(g["links"][0]["relation"], "selects")
        self.assertEqual(g["links"][0]["source"], "k8s:core/Service/app/web-svc")
        self.assertEqual(g["links"][0]["target"], "k8s:apps/Deployment/app/web")

    def test_prod_context_refused_in_k8s_catalog(self):
        with self.assertRaises(SystemExit):
            kc.check_prod_context("arn:aws:eks:us-east-1:111:cluster/prod-main", allow_prod_read=False)
        kc.check_prod_context("arn:aws:eks:us-east-1:111:cluster/prod-main", allow_prod_read=True)
        xr = kc.redact(
            {
                "apiVersion": "database.example.org/v1alpha1",
                "kind": "XCloudBootApp",
                "metadata": {"name": "xr-1"},
                "spec": {
                    "resourceRefs": [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "web", "namespace": "app"}]
                },
            }
        )
        edges = kc.build_edges([xr])
        self.assertIn(
            {"from": "database.example.org/XCloudBootApp//xr-1", "to": "apps/Deployment/app/web", "type": "composes"},
            edges,
        )


if __name__ == "__main__":
    unittest.main()
