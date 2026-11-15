"""Tests for .agent/skills/skill-code-map/scripts/graph_registry.py (local store, routing outcomes, safety)."""

import gzip
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".agent/skills/skill-code-map/scripts/graph_registry.py"
spec = importlib.util.spec_from_file_location("graph_registry", SCRIPT)
gr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gr)


def make_graph(files, hub_label=None):
    """Synthetic node_link graph. files: {source_file: [labels]}; every symbol gets 2 structural edges."""
    nodes, links = [], []
    for sf, labels in files.items():
        for lab in labels:
            nid = f"{sf}:{lab}"
            nodes.append({"id": nid, "label": lab, "source_file": sf})
    for i, n in enumerate(nodes):
        nxt = nodes[(i + 1) % len(nodes)]["id"]
        links.append({"source": n["id"], "target": nxt, "relation": "calls"})
        links.append({"source": n["id"], "target": nodes[(i + 2) % len(nodes)]["id"], "relation": "contains"})
    return {
        "directed": True,
        "multigraph": False,
        "graph": {"graphify_version": "0.0-test"},
        "nodes": nodes,
        "links": links,
    }


def run(args, store):
    return subprocess.run([sys.executable, str(SCRIPT), "--store", str(store), *args], capture_output=True, text=True)


class TestGraphRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = self.root / "store"

    def publish(self, repo, files, sha="abc1234", readme=""):
        g = self.root / f"{repo}.json"
        g.write_text(json.dumps(make_graph(files)))
        rr = self.root / f"{repo}-src"
        rr.mkdir(exist_ok=True)
        (rr / "README.md").write_text(readme)
        return run(["publish", "--repo", repo, "--sha", sha, "--graph", str(g), "--repo-root", str(rr)], self.store)

    def test_01_publish_writes_immutable_snapshot_latest_and_catalog(self):
        p = self.publish("alpha", {"src/billing.py": ["Invoice", "Ledger", "charge"]})
        self.assertEqual(p.returncode, 0, p.stderr)
        snap = self.store / "graphs/alpha/abc1234/graph.json.gz"
        self.assertTrue(snap.is_file())
        self.assertEqual(json.loads(gzip.decompress(snap.read_bytes()))["graph"]["graphify_version"], "0.0-test")
        self.assertEqual(json.loads((self.store / "graphs/alpha/latest.json").read_text())["sha"], "abc1234")
        cat = json.loads((self.store / "catalog/alpha.json").read_text())
        self.assertEqual(cat["repo"], "alpha")
        self.assertEqual(oct(snap.stat().st_mode & 0o777), "0o600")
        before = snap.read_bytes()
        again = self.publish("alpha", {"src/other.py": ["x1", "x2", "x3"]})
        self.assertIn("exists", again.stdout)
        self.assertEqual(snap.read_bytes(), before, "published snapshot must never be rewritten")

    def test_02_rejects_path_traversal_and_bucket_uris(self):
        g = self.root / "g.json"
        g.write_text(json.dumps(make_graph({"a.py": ["one", "two", "three"]})))
        bad = run(["publish", "--repo", "../evil", "--sha", "abc", "--graph", str(g)], self.store)
        self.assertEqual(bad.returncode, 2)
        self.assertFalse((self.root / "evil").exists())
        s3 = subprocess.run(
            [sys.executable, str(SCRIPT), "--store", "s3://bucket/x", "route", "q"], capture_output=True, text=True
        )
        self.assertEqual(s3.returncode, 2)
        self.assertIn("not implemented", s3.stderr)

    def test_03_route_outcomes_confident_ambiguous_no_match(self):
        self.publish(
            "billing", {"src/invoice.py": ["Invoice", "Ledger", "charge"]}, readme="payment invoice ledger service"
        )
        self.publish(
            "scheduler", {"src/cron.py": ["CronJob", "Trigger", "tick"]}, readme="cron trigger scheduler service"
        )
        self.publish("twin", {"src/invoice_cron.py": ["Invoice", "CronJob", "sync"]}, readme="invoice cron service")
        conf = run(["route", "--floor", "0.1", "--ratio", "1.2", "--json", "ledger charge"], self.store)
        self.assertEqual(conf.returncode, 0, conf.stderr)
        self.assertEqual(json.loads(conf.stdout)["candidates"][0]["repo"], "billing")
        amb = run(["route", "--floor", "0.1", "--ratio", "5", "--json", "invoice cron"], self.store)
        self.assertEqual(amb.returncode, 3)
        self.assertGreaterEqual(len(json.loads(amb.stdout)["candidates"]), 2)
        none = run(["route", "--floor", "0.1", "--json", "weather forecast radar"], self.store)
        self.assertEqual(none.returncode, 4)
        self.assertIn("billing", json.loads(none.stdout)["indexed_repos"])

    def test_04_hubs_skip_tests_generated_externals_and_annotation_like_nodes(self):
        nodes = [
            {"id": i, "label": i, "source_file": sf}
            for i, sf in {
                "RealClass": "src/real.py",
                "TestHelper": "tests/test_x.py",
                "Annot": "src/annot.py",
                "Bundle": "web/chunk-AB12.js",
                "Ext": "",
            }.items()
        ]
        links = []
        for _ in range(5):
            for t in ("RealClass", "TestHelper", "Annot", "Bundle", "Ext"):
                links.append({"source": "other", "target": t, "relation": "references"})
        for t in ("RealClass", "TestHelper", "Bundle", "Ext"):
            links += [
                {"source": t, "target": "other", "relation": "contains"},
                {"source": t, "target": "other", "relation": "calls"},
            ]
        nodes.append({"id": "other", "label": "other", "source_file": "src/o.py"})
        self.assertEqual(gr.hubs(nodes, links), ["RealClass"])

    def test_05_fetch_caches_and_query_passes_graph_path(self):
        self.publish("alpha", {"src/billing.py": ["Invoice", "Ledger", "charge"]})
        cache = self.root / "cache"
        f = run(["fetch", "--repo", "alpha", "--cache", str(cache)], self.store)
        self.assertEqual(f.returncode, 0, f.stderr)
        path = Path(f.stdout.strip())
        self.assertTrue(path.is_file())
        self.assertEqual(json.loads(path.read_text())["graph"]["graphify_version"], "0.0-test")
        q = run(
            [
                "query",
                "--repo",
                "alpha",
                "--cache",
                str(cache),
                "--graphify-bin",
                "/bin/echo",
                "--op",
                "query",
                "what calls charge",
            ],
            self.store,
        )
        self.assertEqual(q.returncode, 0, q.stderr)
        self.assertIn("--graph", q.stdout)
        self.assertIn(str(path), q.stdout)
        self.assertIn("alpha@abc1234", q.stderr)


if __name__ == "__main__":
    unittest.main()
