#!/usr/bin/env python3
"""Shared safety constants, schema-driven reference edges, and offline --cache-dir/--no-live in the extractor."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".agent" / "skills"
EXTRACT = ROOT / "skill-graphify" / "scripts" / "k8s_graphify_extract.py"
sys.path.insert(0, str(ROOT / "skill-graphify" / "scripts"))
sys.path.insert(0, str(ROOT / "skill-code-map" / "scripts"))

import k8s_catalog as kc  # noqa: E402
import k8s_graphify_extract as kg  # noqa: E402

OBJS = [
    {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "ops"}},
    {
        "apiVersion": "db.example.org/v1",
        "kind": "Database",
        "metadata": {"name": "main", "namespace": "ops"},
        "spec": {"storageClassRef": {"name": "fast"}, "backupRefs": [{"name": "nightly", "kind": "Backup"}]},
    },
    {"apiVersion": "storage.k8s.io/v1", "kind": "StorageClass", "metadata": {"name": "fast"}},
    {"apiVersion": "db.example.org/v1", "kind": "Backup", "metadata": {"name": "nightly", "namespace": "ops"}},
    {"apiVersion": "v1", "kind": "Service", "metadata": {"name": "nightly", "namespace": "ops"}},
]
CATALOG = {"db.example.org/Database": {"ref_fields": ["spec.storageClassRef", "spec.backupRefs"]}}


class SharedDefinitionTests(unittest.TestCase):
    def test_constants_are_the_catalog_objects(self) -> None:
        self.assertIs(kg.NEVER_LIST, kc.NEVER_LIST)
        self.assertIs(kg.CLUSTER_SCOPED_KINDS, kc.CLUSTER_SCOPED_KINDS)
        self.assertIs(kg.check_prod_context, kc.check_prod_context)
        self.assertIs(kg.SecretLeakError, kc.SecretLeakError)


class SchemaRefTests(unittest.TestCase):
    def setUp(self) -> None:
        g = kg.build_graphify_k8s_graph(OBJS)
        self.out = kg.schema_ref_edges(g, OBJS, CATALOG)
        self.rels = {(lk["source"], lk["relation"], lk["target"]) for lk in self.out["links"]}
        self.src = "k8s:db.example.org/Database/ops/main"

    def test_cluster_scoped_and_kind_filtered_targets(self) -> None:
        self.assertIn((self.src, "references", "k8s:storage.k8s.io/StorageClass/_cluster_/fast"), self.rels)
        self.assertIn((self.src, "references", "k8s:db.example.org/Backup/ops/nightly"), self.rels)

    def test_kind_mismatch_not_linked(self) -> None:
        self.assertNotIn((self.src, "references", "k8s:core/Service/ops/nightly"), self.rels)

    def test_no_catalog_entry_no_edges(self) -> None:
        g = kg.build_graphify_k8s_graph(OBJS)
        self.assertEqual(len(kg.schema_ref_edges(g, OBJS, {})["links"]), len(g["links"]))


class OfflineCacheTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(EXTRACT), *args], capture_output=True, text=True)

    def test_no_live_requires_cache(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            res = self.run_cli("--no-live", "--cache-dir", d, "--out", str(Path(d) / "g.json"))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("objects.json", res.stderr)

    def test_cache_roundtrip_offline_with_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            dd = Path(d)
            cache = dd / "cache"
            (dd / "live.json").write_text(json.dumps(OBJS))
            (dd / "cat.json").write_text(json.dumps({"catalog": CATALOG}))
            # live-k8s run fills nothing (cache only written for real kubectl fetches); seed it like a live run would.
            cache.mkdir()
            kg.write_graph_atomic(cache / "objects.json", OBJS)
            self.assertEqual(oct(os.stat(cache / "objects.json").st_mode & 0o777), "0o600")
            out = dd / "g.json"
            res = self.run_cli(
                "--no-live", "--cache-dir", str(cache), "--catalog", str(dd / "cat.json"), "--out", str(out)
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            links = json.loads(out.read_text())["links"]
            self.assertTrue(any(lk["relation"] == "references" for lk in links))


if __name__ == "__main__":
    unittest.main()
