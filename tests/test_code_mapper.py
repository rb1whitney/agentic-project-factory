#!/usr/bin/env python3
"""Characterization tests for skill-code-map code_mapper.py hardening and the Python graph."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import code_mapper as cm  # noqa: E402
import graph_builder as gb  # noqa: E402


def write(root: Path, rel: str, text) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text)


class MapperBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def map(self):
        m = cm.CodeMapper(str(self.root))
        return m, m.map_repo()


class GoSymbolTests(MapperBase):
    def test_methods_carry_receiver_type(self):
        write(
            self.root,
            "a/a.go",
            "package a\n\ntype Pod struct{}\ntype Sched interface{}\n\n"
            'func (p *Pod) Run() {}\nfunc (Pod) Name() string { return "" }\nfunc New() *Pod { return nil }\n',
        )
        _, cache = self.map()
        entry = cache["a/a.go"]
        self.assertEqual(sorted(entry["public_types"]), ["Pod", "Sched"])
        self.assertEqual(sorted(entry["public_functions"]), ["New", "Pod.Name", "Pod.Run"])


class CacheTests(MapperBase):
    def test_deleted_files_are_pruned(self):
        write(self.root, "a.py", "def f(): pass\n")
        write(self.root, "b.py", "def g(): pass\n")
        self.map()
        (self.root / "b.py").unlink()
        _, cache = self.map()
        self.assertIn("a.py", cache)
        self.assertNotIn("b.py", cache)

    def test_legacy_cache_without_schema_version_is_reindexed(self):
        write(self.root, "a.py", "def f(): pass\n")
        m, _ = self.map()
        cache_file = self.root / ".ast_cache" / "context_map.json"
        data = json.loads(cache_file.read_text())
        for entry in data.values():
            entry.pop("v", None)
            entry["public_functions"] = ["STALE"]
        cache_file.write_text(json.dumps(data))
        _, cache = self.map()
        self.assertEqual(cache["a.py"]["public_functions"], ["f"])

    def test_corrupt_cache_recovers(self):
        write(self.root, "a.py", "def f(): pass\n")
        (self.root / ".ast_cache").mkdir()
        (self.root / ".ast_cache" / "context_map.json").write_text("{not json")
        _, cache = self.map()
        self.assertEqual(cache["a.py"]["public_functions"], ["f"])

    def test_warm_cache_skips_graph_rebuild_and_persists_relationship_graph(self):
        write(self.root, "a.py", "def f():\n    return 1\n")
        m1 = cm.CodeMapper(str(self.root))
        m1.map_repo()
        self.assertEqual(m1.last_updated_count, 1)
        m1.attach_catalog(persist_graph=True)
        m1.serialize_markdown(str(self.root / "code_map.md"))
        self.assertTrue((self.root / "code_map.md").is_file())
        self.assertTrue((self.root / "relationship_graph.json").is_file())

        m2 = cm.CodeMapper(str(self.root))
        m2.map_repo()
        self.assertEqual(m2.last_updated_count, 0)
        self.assertEqual(m2.last_pruned_count, 0)
        self.assertTrue(
            m2.is_warm_noop(
                str(self.root / "code_map.md"),
                str(self.root / "relationship_graph.json"),
            )
        )


class RobustnessTests(MapperBase):
    def test_syntax_error_and_binary_content_do_not_abort(self):
        write(self.root, "bad.go", "package x\nfunc (((( {{{\n")
        write(self.root, "bin.py", b"\xff\xfe\x00\x00def f(:\n")
        write(self.root, "ok.go", "package x\nfunc Ok() {}\n")
        m, cache = self.map()
        self.assertEqual(cache["ok.go"]["public_functions"], ["Ok"])
        self.assertIn("bad.go", m.parse_errors)

    def test_oversized_file_is_skipped(self):
        write(self.root, "huge.go", "package x\n// " + "a" * 64 + "\n")
        m = cm.CodeMapper(str(self.root))
        m.max_file_bytes = 16
        cache = m.map_repo()
        self.assertNotIn("huge.go", cache)
        self.assertIn("huge.go", m.skipped_large)

    def test_vendor_dir_skipped(self):
        write(self.root, "vendor/x/x.go", "package x\nfunc V() {}\n")
        write(self.root, "src/s.go", "package s\nfunc S() {}\n")
        _, cache = self.map()
        self.assertEqual(sorted(cache), ["src/s.go"])

    def test_missing_parser_is_reported_not_silent(self):
        write(self.root, "a.go", "package a\nfunc A() {}\n")
        m = cm.CodeMapper(str(self.root))
        m.parsers["go"] = None
        m.map_repo()
        self.assertIn("go", m.missing_parsers)


class PythonGraphTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.root = root
        write(root, "lib/__init__.py", "")
        write(root, "lib/core/__init__.py", "")
        write(root, "lib/core/base.py", "class Base:\n    pass\n\ndef helper():\n    pass\n")
        write(
            root,
            "lib/core/client.py",
            "import os\nfrom .base import Base\nfrom projects.vault.lib.core import base as b\n"
            "class Client(Base):\n    def get(self):\n        pass\n",
        )
        write(root, "lib/auth/__init__.py", "")
        write(
            root,
            "lib/auth/factory.py",
            "from projects.vault.lib.core.client import Client\nfrom lib.core import base\n",
        )
        write(root, "bin/ctl.py", "from lib.auth.factory import *\nimport requests\n")
        files = [p for p in root.rglob("*") if p.is_file()]
        self.graph = gb.GraphBuilder(str(root)).build_graph(files=files)
        self.edges = {(e["from"], e["to"], e["type"]) for e in self.graph["edges"]}

    def tearDown(self):
        self._tmp.cleanup()

    def test_module_nodes(self):
        n = self.graph["nodes"]["py:lib.core.client"]
        self.assertEqual(n["type"], "py-module")
        self.assertEqual(n["classes"], ["Client"])
        self.assertEqual(n["file"], "lib/core/client.py")

    def test_relative_import_resolves(self):
        self.assertIn(("py:lib.core.client", "py:lib.core.base", "imports"), self.edges)

    def test_foreign_prefix_resolves_by_suffix(self):
        self.assertIn(("py:lib.auth.factory", "py:lib.core.client", "imports"), self.edges)

    def test_from_package_import_submodule(self):
        self.assertIn(("py:lib.auth.factory", "py:lib.core.base", "imports"), self.edges)

    def test_external_imports_emit_no_edge(self):
        self.assertFalse(any(t == "py:requests" or t == "py:os" for _, t, _ in self.edges))

    def test_inheritance_edge(self):
        self.assertIn(("py:lib.core.client", "py:lib.core.base", "inherits"), self.edges)

    def test_graphify_roundtrip_and_auto_context_on_graphify_schema(self):
        import auto_context as ac
        import semantic_query as sq

        g_json = gb.to_graphify(self.graph, name="test-py-graph")
        self.assertTrue(g_json["directed"])
        self.assertTrue(isinstance(g_json["nodes"], list))
        self.assertTrue(isinstance(g_json["links"], list))
        self.assertTrue(any(lnk["relation"] == "imports" for lnk in g_json["links"]))

        # SemanticQuery directly on Graphify schema
        q = sq.SemanticQuery.from_dict(g_json)
        self.assertIn("lib/core/client.py", q.find_definition("py:lib.core.client"))
        self.assertIn("py:lib.auth.factory", q.find_usages("py:lib.core.client"))
        self.assertIn("py:lib.auth.factory", q.impact("py:lib.core.base"))

        # ContextLens directly on Graphify schema
        lens = ac.ContextLens(g_json)
        ranked = lens.rank("refactor Base in lib.core.base")
        files = [r["file"] for r in ranked]
        self.assertIn("lib/core/base.py", files)
        self.assertIn("lib/core/client.py", files)
        # 2-hop forward dependency: ctl -> factory -> client -> base
        ranked_ctl = lens.rank("update bin.ctl entrypoint")
        ctl_files = [r["file"] for r in ranked_ctl]
        self.assertIn("lib/core/client.py", ctl_files)

    def test_semantic_query_owner_preserves_dotted_qualifiers_and_k8s_seeds(self):
        import auto_context as ac
        import semantic_query as sq

        synthetic = {
            "nodes": {
                "com.example.OrderService": {"file": "OrderService.java", "line": 1, "type": "class"},
                "com.example.OrderService.doWork": {"file": "OrderService.java", "line": 10, "type": "method"},
                "k8s:networking.k8s.io/Ingress/app/main-ingress": {
                    "file": "k8s/ingress.yaml",
                    "line": 1,
                    "type": "k8s_resource",
                },
            },
            "edges": [],
        }
        q = sq.SemanticQuery.from_dict(synthetic)
        self.assertEqual(q.owner("com.example.OrderService.doWork"), "com.example.OrderService")
        self.assertEqual(q.owner("py:lib.core.client"), "py:lib.core.client")

        lens = ac.ContextLens(synthetic)
        ranked = lens.rank("configure main-ingress routing")
        self.assertEqual([r["file"] for r in ranked], ["k8s/ingress.yaml"])

        # Confidence-weighted BFS: EXTRACTED (1.0) outranks AMBIGUOUS (0.5) dependent
        weighted_graph = {
            "directed": True,
            "nodes": [
                {"id": "Core", "source_file": "Core.java", "file_type": "class"},
                {"id": "HighConfCaller", "source_file": "High.java", "file_type": "class"},
                {"id": "LowConfCaller", "source_file": "Low.java", "file_type": "class"},
            ],
            "links": [
                {
                    "source": "HighConfCaller",
                    "target": "Core",
                    "relation": "calls",
                    "confidence_score": 1.0,
                    "weight": 1.0,
                },
                {
                    "source": "LowConfCaller",
                    "target": "Core",
                    "relation": "calls",
                    "confidence_score": 0.5,
                    "weight": 1.0,
                },
            ],
        }
        w_ranked = ac.ContextLens(weighted_graph).rank("refactor Core")
        self.assertEqual([r["file"] for r in w_ranked], ["Core.java", "High.java", "Low.java"])

    def test_java_block_scoped_locals_do_not_collide_across_sibling_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, "Alpha.java", "public class Alpha { public void run() {} }\n")
            write(root, "Beta.java", "public class Beta { public void run() {} }\n")
            write(
                root,
                "Caller.java",
                "public class Caller {\n"
                "  public void test() {\n"
                "    { Alpha svc = new Alpha(); svc.run(); }\n"
                "    { Beta svc = new Beta(); svc.run(); }\n"
                "  }\n"
                "}\n",
            )
            g = gb.GraphBuilder(str(root)).build_graph()
            calls = {(e["from"], e["to"]) for e in g["edges"] if e["type"] == "calls"}
            self.assertIn(("Caller.test", "Alpha.run"), calls)
            self.assertIn(("Caller.test", "Beta.run"), calls)

    def test_ppr_and_token_budget_binary_search_packing(self):
        import auto_context as ac

        lens = ac.ContextLens(self.graph)
        ppr_scores = lens.ppr({"py:lib.core.base"})
        self.assertGreater(ppr_scores.get("py:lib.core.base", 0.0), ppr_scores.get("py:bin.ctl", 0.0))
        self.assertGreater(ppr_scores.get("py:lib.core.client", 0.0), 0.0)

        ranked = lens.rank("refactor Base in lib.core.base")
        self.assertTrue(any("ppr" in r for r in ranked))

        packed = lens.pack_context("refactor Base in lib.core.base", max_tokens=120)
        self.assertIn("lib/core/base.py", packed["packed_text"])
        self.assertLessEqual(packed["estimated_tokens"], 120)
        self.assertTrue(len(packed["included_files"]) >= 1)

        zero_packed = lens.pack_context("refactor Base in lib.core.base", max_tokens=0)
        self.assertEqual(zero_packed["included_files"], [])
        self.assertEqual(zero_packed["packed_text"], "")

    def test_git_cochange_mining_injects_inferred_edges(self):
        sample_log = (
            "COMMIT:a1\n"
            "lib/core/client.py\n"
            "config/settings.yaml\n"
            "\n"
            "COMMIT:a2\n"
            "lib/core/client.py\n"
            "config/settings.yaml\n"
            "\n"
            "COMMIT:a3\n"
            "lib/core/client.py\n"
            "config/settings.yaml\n"
            "lib/auth/factory.py\n"
        )
        nodes_copy = json.loads(json.dumps(self.graph["nodes"]))
        co_edges = gb.parse_git_log_cochanges(sample_log, min_cochanges=2, min_jaccard=0.5, nodes=nodes_copy)
        self.assertTrue(
            any(
                {e["from"], e["to"]} == {"py:lib.core.client", "config/settings.yaml"}
                and e["type"] == "co-changes-with"
                and e["confidence"] == "INFERRED"
                and e["confidence_score"] >= 0.66
                for e in co_edges
            )
        )
        self.assertIn("config/settings.yaml", nodes_copy)

    def test_diff_impact_and_shortest_path(self):
        import semantic_query as sq

        q = sq.SemanticQuery.from_dict(self.graph)
        path = q.shortest_path("py:bin.ctl", "py:lib.core.base")
        self.assertEqual(path, ["py:bin.ctl", "py:lib.auth.factory", "py:lib.core.base"])
        # Reverse directed path does not exist unless undirected=True
        self.assertEqual(q.shortest_path("py:lib.core.base", "py:bin.ctl", directed=True), [])
        self.assertEqual(
            q.shortest_path("py:lib.core.base", "py:bin.ctl", directed=False),
            ["py:lib.core.base", "py:lib.auth.factory", "py:bin.ctl"],
        )

        sample_diff = "--- a/lib/core/base.py\n+++ b/lib/core/base.py\n@@ -1,1 +1,2 @@\n class Base: pass\n+    x = 1\n"
        g_with_test = json.loads(json.dumps(self.graph))
        g_with_test["nodes"]["py:tests.test_factory"] = {
            "file": "tests/test_factory.py",
            "line": 1,
            "type": "py-module",
        }
        g_with_test["nodes"]["py:lib.core.base.far_fn"] = {
            "file": "lib/core/base.py",
            "line": 200,
            "end_line": 210,
            "type": "method",
        }
        g_with_test["edges"].append({"from": "py:tests.test_factory", "to": "py:lib.auth.factory", "type": "imports"})
        qt = sq.SemanticQuery.from_dict(g_with_test)
        impact_res = qt.diff_impact(sample_diff)
        self.assertIn("py:lib.core.base", impact_res["modified_symbols"])
        self.assertNotIn("py:lib.core.base.far_fn", impact_res["modified_symbols"])
        self.assertIn("py:lib.core.client", impact_res["impacted_production"])
        self.assertIn("tests/test_factory.py", impact_res["impacted_tests"])

    def test_tarjan_postorder_cycles_communities_and_graph_report(self):
        cyclic_graph = {
            "nodes": {
                "A": {"file": "A.java", "line": 1, "type": "class"},
                "B": {"file": "B.java", "line": 1, "type": "class"},
                "C": {"file": "C.java", "line": 1, "type": "class"},
                "Isolated": {"file": "Iso.java", "line": 1, "type": "class"},
            },
            "edges": [
                {"from": "A", "to": "B", "type": "calls"},
                {"from": "B", "to": "C", "type": "calls"},
                {"from": "C", "to": "A", "type": "calls"},
            ],
        }
        cycles = gb.find_cycles_postorder(cyclic_graph["nodes"], cyclic_graph["edges"])
        self.assertEqual(len(cycles), 1)
        self.assertEqual(set(cycles[0]), {"A", "B", "C"})

        comms = gb.detect_communities(cyclic_graph["nodes"], cyclic_graph["edges"])
        self.assertEqual(comms["A"], comms["B"])
        self.assertEqual(comms["B"], comms["C"])
        self.assertNotEqual(comms["A"], comms["Isolated"])

        report_md = gb.generate_graph_report(cyclic_graph)
        self.assertIn("Circular Dependencies", report_md)
        self.assertIn("A -> B -> C -> A", report_md)

        # Figure-8 SCC (A <-> B and B <-> C, no edge C -> A) formats as SCC without fabricating C -> A
        figure8_graph = {
            "nodes": cyclic_graph["nodes"],
            "edges": [
                {"from": "A", "to": "B", "type": "calls"},
                {"from": "B", "to": "A", "type": "calls"},
                {"from": "B", "to": "C", "type": "calls"},
                {"from": "C", "to": "B", "type": "calls"},
            ],
        }
        fig8_md = gb.generate_graph_report(figure8_graph)
        self.assertIn("SCC (3 nodes):", fig8_md)

    def test_mcp_server_tools_roundtrip(self):
        import codemap_graphify_mcp as mcp

        srv = mcp.CodeMapGraphifyMCP(graph=self.graph)
        tools = srv.list_tools()
        tool_names = {t["name"] for t in tools}
        self.assertIn("graph_context_lens", tool_names)
        self.assertIn("graph_diff_impact", tool_names)
        self.assertIn("graph_shortest_path", tool_names)
        self.assertIn("ast_dump_tree", tool_names)

        sp = srv.call_tool("graph_shortest_path", {"source": "py:bin.ctl", "target": "py:lib.core.base"})
        self.assertIn("py:lib.core.base", sp["path"])

        ast_out = srv.call_tool("ast_dump_tree", {"language": "python", "code": "def hello(x):\n    return x + 1\n"})
        self.assertIn("function_definition", ast_out["sexp"])

        rule_err = srv.call_tool(
            "ast_test_rule",
            {"rule_yaml": "invalid: [yaml", "code": "x = 1\n", "extension": "../py"},
        )
        self.assertEqual(rule_err["count"], 0)
        self.assertTrue("error" in rule_err or "stderr" in rule_err)


if __name__ == "__main__":
    unittest.main()
