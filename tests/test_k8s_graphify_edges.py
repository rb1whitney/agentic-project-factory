#!/usr/bin/env python3
"""Tests for scoped/batched kubectl planning and production K8s edges + diagnostics in k8s_graphify_extract."""

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-graphify" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import k8s_graphify_extract as kg  # noqa: E402

NS = "ops"


def meta(name: str, ns: str = NS) -> dict:
    return {"name": name, "namespace": ns}


class PlanTests(unittest.TestCase):
    def test_namespaced_uses_n_not_A(self) -> None:
        qs = kg.plan_queries(["pods", "services"], ["nodes"], NS, False)
        self.assertEqual(qs[0][:4], ["get", "pods,services", "-n", NS])
        self.assertNotIn("-A", qs[0])
        self.assertEqual(qs[1][1], "nodes")
        self.assertNotIn("-n", qs[1])

    def test_all_namespaces_flag(self) -> None:
        qs = kg.plan_queries(["pods"], [], None, True)
        self.assertIn("-A", qs[0])

    def test_batching(self) -> None:
        names = [f"r{i}.example.org" for i in range(30)]
        qs = kg.plan_queries(names, [], NS, False, batch_size=12)
        self.assertEqual(len(qs), 3)
        self.assertIn(kg.REQUEST_TIMEOUT, qs[0])

    def test_batch_failure_falls_back_per_kind(self) -> None:
        calls = []

        def fake(args, kubeconfig=None, context=None):
            calls.append(args[1])
            return None if "," in args[1] else ({"kind": "List", "items": []} if args[1] == "a" else None)

        orig = kg.run_kubectl
        kg.run_kubectl = fake
        try:
            out = kg._run_batch(["get", "a,b", "-o", "json"], None, None)
        finally:
            kg.run_kubectl = orig
        self.assertEqual(calls, ["a,b", "a", "b"])
        self.assertEqual(len(out), 1)


class EdgeTests(unittest.TestCase):
    def build(self, objs):
        g = kg.build_graphify_k8s_graph(objs)
        rels = {(lk["source"], lk["relation"], lk["target"]) for lk in g["links"]}
        return g, rels, {n["id"]: n for n in g["nodes"]}

    def test_endpoints_to_pod_and_counts(self) -> None:
        svc = {"apiVersion": "v1", "kind": "Service", "metadata": meta("web"), "spec": {}}
        pod = {"apiVersion": "v1", "kind": "Pod", "metadata": meta("web-0"), "status": {"phase": "Running"}}
        ep = {
            "apiVersion": "v1", "kind": "Endpoints", "metadata": meta("web"),
            "subsets": [{"addresses": [{"targetRef": {"kind": "Pod", "name": "web-0", "namespace": NS}}],
                         "notReadyAddresses": [{"targetRef": {"kind": "Pod", "name": "gone"}}]}],
        }
        g, rels, nodes = self.build([svc, pod, ep])
        s, p = "k8s:core/Service/ops/web", "k8s:core/Pod/ops/web-0"
        self.assertIn((s, "routes-to-pod", p), rels)
        self.assertEqual(nodes[s]["properties"]["endpoints_ready"], 1)
        self.assertEqual(nodes[s]["properties"]["endpoints_not_ready"], 1)

    def test_mounts_and_missing_target(self) -> None:
        dep = {
            "apiVersion": "apps/v1", "kind": "Deployment", "metadata": meta("app"),
            "spec": {"template": {"metadata": {"labels": {"a": "b"}}, "spec": {
                "serviceAccountName": "ghost",
                "volumes": [{"configMap": {"name": "cfg"}}, {"persistentVolumeClaim": {"claimName": "data"}}],
                "containers": [{"name": "c", "envFrom": [{"configMapRef": {"name": "envcfg"}}]}],
            }}},
        }
        g, rels, nodes = self.build([dep])
        d = "k8s:apps/Deployment/ops/app"
        self.assertIn((d, "mounts-configmap", "k8s:core/ConfigMap/ops/cfg"), rels)
        self.assertIn((d, "mounts-configmap", "k8s:core/ConfigMap/ops/envcfg"), rels)
        self.assertIn((d, "mounts-pvc", "k8s:core/PersistentVolumeClaim/ops/data"), rels)
        self.assertEqual(nodes["k8s:core/ServiceAccount/ops/ghost"]["properties"]["status"], "MISSING_TARGET")
        self.assertEqual(nodes["k8s:core/PersistentVolumeClaim/ops/data"]["properties"]["status"], "MISSING_TARGET")
        self.assertEqual(nodes["k8s:core/ConfigMap/ops/cfg"]["properties"]["status"], "Unverified (Redacted Kind)")
        codes = {(x["code"], x["node"]) for x in g["diagnostics"]}
        self.assertIn(("missing-target", "k8s:core/ServiceAccount/ops/ghost"), codes)
        self.assertNotIn(("missing-target", "k8s:core/ConfigMap/ops/cfg"), codes)

    def test_present_target_not_flagged(self) -> None:
        sa = {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": meta("ok")}
        dep = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": meta("app"),
               "spec": {"template": {"spec": {"serviceAccountName": "ok"}}}}
        g, _, _ = self.build([sa, dep])
        self.assertEqual(g["diagnostics"], [])

    def test_webhook_and_mesh(self) -> None:
        svc = {"apiVersion": "v1", "kind": "Service", "metadata": meta("vault-webhook")}
        wh = {"apiVersion": "admissionregistration.k8s.io/v1", "kind": "MutatingWebhookConfiguration",
              "metadata": {"name": "vault"},
              "webhooks": [{"clientConfig": {"service": {"name": "vault-webhook", "namespace": NS}}}]}
        dr = {"apiVersion": "networking.istio.io/v1", "kind": "DestinationRule", "metadata": meta("dr"),
              "spec": {"host": "vault-webhook.ops.svc.cluster.local",
                       "trafficPolicy": {"tls": {"mode": "ISTIO_MUTUAL"}}}}
        vs = {"apiVersion": "networking.istio.io/v1", "kind": "VirtualService", "metadata": meta("vs"),
              "spec": {"http": [{"route": [{"destination": {"host": "vault-webhook"}}]}]}}
        _, rels, _ = self.build([svc, wh, dr, vs])
        s = "k8s:core/Service/ops/vault-webhook"
        self.assertIn(("k8s:admissionregistration.k8s.io/MutatingWebhookConfiguration/_cluster_/vault",
                       "intercepts-workloads", s), rels)
        self.assertIn(("k8s:networking.istio.io/DestinationRule/ops/dr", "applies-mtls-policy", s), rels)
        self.assertIn(("k8s:networking.istio.io/VirtualService/ops/vs", "mesh-routes-to", s), rels)

    def test_pod_readiness_properties(self) -> None:
        pod = {"apiVersion": "v1", "kind": "Pod", "metadata": meta("p"), "status": {
            "phase": "Running",
            "containerStatuses": [{"ready": True, "restartCount": 2}, {"ready": False, "restartCount": 1}],
            "initContainerStatuses": [{"state": {"terminated": {"exitCode": 0}}}]}}
        _, _, nodes = self.build([pod])
        props = nodes["k8s:core/Pod/ops/p"]["properties"]
        self.assertEqual((props["containers_ready"], props["restart_count"], props["init"]), ("1/2", 3, "ok"))

    def test_no_hardcoded_demo_edge(self) -> None:
        self.assertNotIn("cloud-boot-db", Path(kg.__file__).read_text())


if __name__ == "__main__":
    unittest.main()
