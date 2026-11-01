#!/usr/bin/env python3
"""Unmanaged live K8s/Vault nodes get unique k8s:// / vault:// sources so auto_context ranks them individually."""

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import auto_context as ac  # noqa: E402
import state_graph as sg  # noqa: E402

REPORT = {
    "k8s_drift": {
        "unmanaged": [
            "apps/v1/Deployment/app/rogue",
            "v1/Service/app/stray-svc",
            "rbac.authorization.k8s.io/v1/ClusterRole//wild",
        ],
        "drifted": [],
        "missing": [],
    },
    "vault_drift": {"unmanaged": ["vault::policy:stray"], "drifted": [], "missing": []},
}


class LiveUriTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = sg.report_to_graphify(REPORT, {}, {}, [])
        self.by_id = {n["id"]: n for n in self.graph["nodes"]}

    def test_uri_helper(self) -> None:
        self.assertEqual(sg._live_uri("k8s:apps/Deployment/app/rogue"), "k8s://app/deployment/rogue")
        self.assertEqual(
            sg._live_uri("k8s:rbac.authorization.k8s.io/ClusterRole/_cluster_/wild"), "k8s://cluster/clusterrole/wild"
        )

    def test_unique_sources(self) -> None:
        srcs = [n["source_file"] for n in self.graph["nodes"]]
        self.assertEqual(len(srcs), len(set(srcs)))
        self.assertNotIn("k8s-live", srcs)
        self.assertNotIn("vault-live", srcs)
        self.assertEqual(self.by_id["k8s:apps/Deployment/app/rogue"]["source_file"], "k8s://app/deployment/rogue")
        self.assertTrue(self.by_id["vault::policy:stray"]["source_file"].startswith("vault://"))

    def test_ranking_and_pack_are_per_resource(self) -> None:
        lens = ac.ContextLens(self.graph)
        ranked = lens.rank("investigate rogue deployment", top=5)
        self.assertEqual(ranked[0]["file"], "k8s://app/deployment/rogue")
        packed = lens.pack_context("investigate rogue deployment", max_tokens=500)
        self.assertIn("k8s://app/deployment/rogue", packed["included_files"])
        self.assertIn("drift_status=unmanaged", packed["packed_text"])
        self.assertNotIn("stray-svc", packed["packed_text"].split("## ")[1])


if __name__ == "__main__":
    unittest.main()
