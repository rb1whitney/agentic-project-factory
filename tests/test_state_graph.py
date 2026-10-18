#!/usr/bin/env python3
"""Characterization tests for skill-code-map/scripts/state_graph.py (IaC vs live Kubernetes/Vault). No network."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state_graph as sg  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


DEPLOY = """
apiVersion: apps/v1
kind: Deployment
metadata: {name: web, namespace: app, labels: {app: web}}
spec:
  replicas: 3
  template:
    metadata:
      annotations: {vault.hashicorp.com/role: web-role}
    spec:
      containers:
      - {name: web, image: "nginx:1.25", env: [{name: A, value: "1"}]}
---
apiVersion: v1
kind: Secret
metadata: {name: creds, namespace: app}
stringData: {password: hunter2}
---
apiVersion: v1
kind: ServiceAccount
metadata: {name: web-sa, namespace: app}
"""


class K8sDesiredTests(unittest.TestCase):
    def test_loads_multidoc_and_strips_secret_payload(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d), "k/web.yaml", DEPLOY)
            write(Path(d), "k/helm/templates/x.yaml", "kind: {{ .Values.k }}\n")
            desired = sg.load_k8s_desired([d])
        self.assertIn("apps/v1/Deployment/app/web", desired)
        self.assertEqual(len(desired), 3)
        self.assertNotIn("hunter2", json.dumps(desired))


class SubsetDiffTests(unittest.TestCase):
    def test_extra_live_fields_ignored_changed_fields_reported(self):
        d = {"spec": {"replicas": 3, "template": {"spec": {"containers": [{"name": "web", "image": "nginx:1.25"}]}}}}
        live = {
            "spec": {
                "replicas": 2,
                "paused": False,
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "sidecar", "image": "x"},
                            {"name": "web", "image": "nginx:1.26", "imagePullPolicy": "Always"},
                        ]
                    }
                },
            }
        }
        ch = {c["path"]: (c["desired"], c["live"]) for c in sg.subset_diff(d, live)}
        self.assertEqual(ch["spec.replicas"], (3, 2))
        self.assertEqual(ch["spec.template.spec.containers[web].image"], ("nginx:1.25", "nginx:1.26"))
        self.assertEqual(len(ch), 2)

    def test_sensitive_values_redacted_in_report(self):
        ch = sg.subset_diff({"spec": {"password": "a"}}, {"spec": {"password": "b"}})
        self.assertEqual(ch[0]["desired"], sg.REDACTED)
        self.assertEqual(ch[0]["live"], sg.REDACTED)

    def test_missing_live_key_reported(self):
        ch = sg.subset_diff({"spec": {"a": 1}}, {"spec": {}})
        self.assertEqual(ch[0]["live"], "<absent>")


class K8sDriftTests(unittest.TestCase):
    def test_missing_drifted_unmanaged(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d), "web.yaml", DEPLOY)
            desired = sg.load_k8s_desired([d])
        live = [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "web", "namespace": "app", "labels": {"app": "web"}},
                "spec": {
                    "replicas": 1,
                    "template": {
                        "spec": {
                            "containers": [{"name": "web", "image": "nginx:1.25", "env": [{"name": "A", "value": "1"}]}]
                        }
                    },
                },
            },
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": "creds", "namespace": "app"},
                "data": {"password": "c2VjcmV0"},
            },
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "rogue", "namespace": "app"},
                "spec": {},
            },
        ]
        res = sg.diff_k8s(desired, live)
        self.assertEqual(res["missing"], ["v1/ServiceAccount/app/web-sa"])
        self.assertEqual([x["id"] for x in res["drifted"]], ["apps/v1/Deployment/app/web"])
        self.assertEqual(res["unmanaged"], ["apps/v1/Deployment/app/rogue"])
        self.assertNotIn("c2VjcmV0", json.dumps(res))

    def test_fetch_strips_secret_data_immediately(self):
        def runner(args):
            return json.dumps(
                {
                    "items": [
                        {
                            "apiVersion": "v1",
                            "kind": "Secret",
                            "metadata": {"name": "s", "namespace": "a"},
                            "data": {"k": "dg=="},
                            "stringData": {"k": "v"},
                        }
                    ]
                }
            )

        live = sg.fetch_k8s_live({"v1/Secret": ["a"]}, runner=runner)
        self.assertNotIn("data", live[0])
        self.assertNotIn("stringData", live[0])


class VaultDesiredTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write(
            self.root,
            "admin/_acl_policies.yaml",
            """
api_paths:
- api_path: v1/sys/policy/app-read
  api_action: post
  api_payload:
    path:
      secret/data/app: {capabilities: [read, list]}
- api_path: v1/sys/policy/mixed
  api_action: post
  api_payload:
    path:
      secret/data/x: {capabilities: [read, update]}
""",
        )
        write(
            self.root,
            "admin/_secret_engines.yaml",
            """
api_paths:
- api_path: v1/sys/mounts/kv-app
  api_action: post
  api_payload: {type: kv, description: app, config: {default_lease_ttl: 24h}}
- api_path: v1/transit/keys/k1
  api_action: post
  api_payload: {type: aes256-gcm96, exportable: true, allow_plaintext_backup: true}
""",
        )
        write(
            self.root,
            "admin/_auth_methods.yaml",
            """
api_paths:
- api_path: v1/sys/auth/kubernetes
  api_action: post
  api_payload: {type: kubernetes}
- api_path: v1/auth/kubernetes/role/web-role
  api_action: post
  api_payload:
    bound_service_account_names: [web-sa, ghost-sa]
    bound_service_account_namespaces: [app]
    token_policies: [app-read]
- api_path: v1/auth/kubernetes/role/wild
  api_action: post
  api_payload: {bound_service_account_names: ["*"], bound_service_account_namespaces: ["*"]}
- api_path: v1/auth/ldap/config
  api_action: post
  api_payload: {insecure_tls: true, url: ldaps://x}
""",
        )
        write(
            self.root,
            "admin/_audit_devices.yaml",
            """
api_paths:
- api_path: v1/sys/audit/file
  api_action: post
  api_payload: {type: file, options: {file_path: /tmp/audit.log}}
""",
        )
        write(
            self.root,
            "app/kv/db.yaml",
            """
api_paths:
- api_path: v1/app/data/db
  api_action: post
  api_payload: {data: {user: "vault:v1:abc", password: "plaintext!"}}
""",
        )
        write(
            self.root,
            "contexts.yaml",
            (
                "clusters:\n  prod:\n    api_url: vault.corp.example\n"
                "    api_protocol: http\n    key_encrypt: false\n"
                "  local:\n    api_url: localhost\n"
                "    api_protocol: http\n    key_encrypt: false\n"
            ),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_classification(self):
        d = sg.load_vault_desired(self.root)
        ids = set(d)
        self.assertIn("vault::policy:app-read", ids)
        self.assertIn("vault::mount:kv-app", ids)
        self.assertIn("vault::auth:kubernetes", ids)
        self.assertIn("vault::auth_role:kubernetes/web-role", ids)
        self.assertIn("vault::audit:file", ids)

    def test_lint_opinions(self):
        rules = {(f["rule"], f["severity"]) for f in sg.lint_vault(self.root)}
        self.assertIn(("policy-read-write-mix", "repo-rule"), rules)
        self.assertIn(("mount-ttl-over-1h", "repo-rule"), rules)
        self.assertIn(("plaintext-secret", "repo-rule"), rules)
        self.assertIn(("insecure-tls", "advisory"), rules)
        self.assertIn(("transit-key-exportable", "advisory"), rules)
        self.assertIn(("audit-log-in-tmp", "advisory"), rules)
        self.assertIn(("wildcard-k8s-role-binding", "advisory"), rules)

    def test_lint_contexts_flags_remote_http_only(self):
        hits = [f for f in sg.lint_vault(self.root) if f["rule"] in ("cleartext-transport", "key-material-unencrypted")]
        self.assertTrue(all("prod" in f["message"] for f in hits))
        self.assertEqual(len(hits), 2)

    def test_policy_parse_json_and_hcl(self):
        hcl = (
            'path "secret/data/app" {\n  capabilities = ["read", "list"]\n}\npath "sys/*" { capabilities = ["deny"] }\n'
        )
        self.assertEqual(sg.parse_policy(hcl), {"secret/data/app": ["list", "read"], "sys/*": ["deny"]})
        js = json.dumps({"path": {"a/*": {"capabilities": ["read"]}}})
        self.assertEqual(sg.parse_policy(js), {"a/*": ["read"]})

    def test_vault_drift(self):
        desired = sg.load_vault_desired(self.root)
        live = {
            "policy": {
                "app-read": 'path "secret/data/app" { capabilities = ["read"] }',
                "stray": "",
                "default": "",
                "root": "",
            },
            "mount": {
                "kv-app/": {"type": "kv", "description": "app", "config": {"default_lease_ttl": 86400}},
                "sys/": {"type": "system"},
                "extra/": {"type": "kv"},
            },
            "auth": {"token/": {"type": "token"}},
            "audit": {},
            "auth_role": {},
        }
        res = sg.diff_vault(desired, live)
        self.assertIn("vault::policy:stray", res["unmanaged"])
        self.assertIn("vault::mount:extra", res["unmanaged"])
        self.assertNotIn("vault::policy:default", res["unmanaged"])
        self.assertNotIn("vault::mount:sys", res["unmanaged"])
        self.assertIn("vault::auth:kubernetes", res["missing"])
        drift = {x["id"]: x["changes"] for x in res["drifted"]}
        self.assertEqual(drift["vault::policy:app-read"][0]["path"], "secret/data/app")
        self.assertNotIn("vault::mount:kv-app", drift)  # 24h == 86400s

    def test_fetch_vault_live_uses_read_only_verbs(self):
        calls = []

        def runner(args, ns):
            calls.append(args)
            key = " ".join(args)
            if key == "list sys/policies/acl":
                return ["a"]
            if key == "read sys/policies/acl/a":
                return {"data": {"policy": "x"}}
            return {"data": {}}

        sg.fetch_vault_live("", runner=runner)
        self.assertTrue(all(a[0] in ("read", "list") for a in calls))


class CrossCheckTests(unittest.TestCase):
    def test_vault_roles_vs_cluster_and_workload_annotations(self):
        vdesired = {
            "vault::auth_role:kubernetes/web-role": {
                "kind": "auth_role",
                "name": "kubernetes/web-role",
                "payload": {
                    "bound_service_account_names": ["web-sa", "ghost-sa"],
                    "bound_service_account_namespaces": ["app"],
                },
            },
        }
        with tempfile.TemporaryDirectory() as d:
            write(Path(d), "web.yaml", DEPLOY)
            kdesired = sg.load_k8s_desired([d])
        live = [{"apiVersion": "v1", "kind": "ServiceAccount", "metadata": {"name": "web-sa", "namespace": "app"}}]
        f = sg.cross_check(vdesired, kdesired, live)
        msgs = [x["message"] for x in f]
        self.assertTrue(any("ghost-sa" in m and "app" in m for m in msgs))
        self.assertFalse(any("web-sa" in m and "missing" in m for m in msgs))
        vd2 = {}
        f2 = sg.cross_check(vd2, kdesired, live)
        self.assertTrue(any("web-role" in x["message"] for x in f2))


class ClusterHealthTests(unittest.TestCase):
    def test_findings(self):
        pods = [
            {
                "kind": "Pod",
                "metadata": {"name": "p1", "namespace": "a"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {"name": "c", "ready": False, "state": {"waiting": {"reason": "CrashLoopBackOff"}}}
                    ],
                },
            },
            {
                "kind": "Pod",
                "metadata": {"name": "p2", "namespace": "a"},
                "status": {"phase": "Running", "containerStatuses": [{"name": "c", "ready": True}]},
            },
            {
                "kind": "Deployment",
                "metadata": {"name": "d", "namespace": "a"},
                "spec": {"replicas": 3},
                "status": {"readyReplicas": 1},
            },
            {
                "kind": "Node",
                "metadata": {"name": "n1"},
                "status": {"conditions": [{"type": "Ready", "status": "False"}]},
            },
            {
                "kind": "PersistentVolumeClaim",
                "metadata": {"name": "v", "namespace": "a"},
                "status": {"phase": "Pending"},
            },
            {"kind": "Service", "metadata": {"name": "s", "namespace": "a"}, "spec": {"selector": {"app": "none"}}},
        ]
        f = {(x["kind"], x["id"]) for x in sg.cluster_health(pods)}
        self.assertIn(("pod-unready", "a/p1"), f)
        self.assertNotIn(("pod-unready", "a/p2"), f)
        self.assertIn(("workload-underreplicated", "a/d"), f)
        self.assertIn(("node-not-ready", "n1"), f)
        self.assertIn(("pvc-pending", "a/v"), f)
        self.assertIn(("service-no-endpoints-selector", "a/s"), f)


class StateGraphifyExportTests(unittest.TestCase):
    def test_report_to_graphify_models_drift_and_cross_checks(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d), "web.yaml", DEPLOY)
            kdesired = sg.load_k8s_desired([d])
        vdesired = {
            "vault::auth_role:kubernetes/web-role": {
                "kind": "auth_role",
                "name": "kubernetes/web-role",
                "namespace": "",
                "payload": {
                    "bound_service_account_names": ["web-sa", "ghost-sa"],
                    "bound_service_account_namespaces": ["app"],
                    "token_policies": ["app-read"],
                },
                "file": "auth.yaml",
            }
        }
        live_k8s = [
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "web", "namespace": "app", "labels": {"app": "web"}},
                "spec": {"replicas": 1},
            }
        ]
        report = {
            "k8s_drift": sg.diff_k8s(kdesired, live_k8s),
            "cross_check": sg.cross_check(vdesired, kdesired, live_k8s),
            "vault_lint": [
                {
                    "rule": "insecure-tls",
                    "severity": "advisory",
                    "file": "auth.yaml",
                    "message": "ldap: insecure_tls true",
                }
            ],
        }
        g = sg.report_to_graphify(report, kdesired, vdesired, live_k8s)
        self.assertTrue(g["directed"])
        by_id = {n["id"]: n for n in g["nodes"]}
        self.assertEqual(by_id["k8s:apps/Deployment/app/web"]["properties"]["drift_status"], "drifted")
        self.assertEqual(by_id["k8s:core/ServiceAccount/app/web-sa"]["properties"]["drift_status"], "missing")
        rels = {(lnk["source"], lnk["relation"], lnk["target"]) for lnk in g["links"]}
        self.assertIn(("k8s:apps/Deployment/app/web", "uses-vault-role", "vault::auth_role:kubernetes/web-role"), rels)
        self.assertIn(
            ("vault::auth_role:kubernetes/web-role", "binds-serviceaccount", "k8s:core/ServiceAccount/app/web-sa"), rels
        )
        self.assertIn(("vault::auth_role:kubernetes/web-role", "has-lint-finding", "lint:insecure-tls:0"), rels)
        self.assertTrue(any(n["file_type"] == "cross_check" for n in g["nodes"]))

    def test_desired_secret_strips_last_applied_annotations(self):
        with tempfile.TemporaryDirectory() as d:
            write(
                Path(d),
                "sec.yaml",
                "apiVersion: v1\nkind: Secret\nmetadata:\n  name: s\n  namespace: app\n"
                '  annotations:\n    kubectl.kubernetes.io/last-applied-configuration: \'{"data":{"pw":"hunter2"}}\'\n'
                "stringData:\n  pw: hunter2\n",
            )
            desired = sg.load_k8s_desired([d])
        self.assertNotIn("hunter2", json.dumps(desired))


if __name__ == "__main__":
    unittest.main()
