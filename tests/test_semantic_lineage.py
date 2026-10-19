#!/usr/bin/env python3
"""Tests for semantic_query K8s-style matching, query breakdown, lineage and the MCP lineage tools."""

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import codemap_graphify_mcp as mcp  # noqa: E402
import semantic_query as sq  # noqa: E402

ING = "k8s:networking.k8s.io/Ingress/operations/grafana"
SVC = "k8s:core/Service/operations/grafana-alloy-metrics"
POD = "k8s:core/Pod/operations/grafana-alloy-0"
SA = "k8s:core/ServiceAccount/operations/alloy"

GRAPH = {
    "nodes": [
        {"id": ING, "properties": {"type": "Ingress", "status": "Active"}},
        {"id": SVC, "properties": {"type": "Service", "status": "Active"}},
        {"id": POD, "properties": {"type": "Pod", "status": "CrashLoopBackOff"}},
        {"id": SA, "properties": {"type": "ServiceAccount", "status": "Active"}},
    ],
    "links": [
        {"source": ING, "target": SVC, "relation": "routes-to"},
        {"source": SVC, "target": POD, "relation": "routes-to-pod"},
        {"source": POD, "target": SA, "relation": "runs-as"},
    ],
}


class MatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.q = sq.SemanticQuery.from_dict(GRAPH)

    def test_suffix_name(self) -> None:
        self.assertEqual(self.q._matches("grafana-alloy-metrics"), [SVC])

    def test_kind_slash_name(self) -> None:
        self.assertEqual(self.q._matches("Service/grafana-alloy-metrics"), [SVC])

    def test_ns_slash_name(self) -> None:
        self.assertEqual(self.q._matches("operations/alloy"), [SA])

    def test_substring_infra_only(self) -> None:
        self.assertEqual(set(self.q._matches("grafana")), {ING, SVC, POD})

    def test_code_symbols_not_substring_matched(self) -> None:
        q = sq.SemanticQuery.from_dict({"nodes": {"Foo.bar": {"type": "method"}}, "edges": []})
        self.assertEqual(q._matches("ba"), [])


class LineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.q = sq.SemanticQuery.from_dict(GRAPH)

    def test_both_directions(self) -> None:
        lin = self.q.lineage("Service/grafana-alloy-metrics", depth=2)
        self.assertEqual(lin["upstream"], [ING])
        self.assertEqual(lin["downstream"], sorted([POD, SA]))

    def test_depth_limits(self) -> None:
        lin = self.q.lineage(SVC, depth=1)
        self.assertEqual(lin["downstream"], [POD])

    def test_mermaid_has_status(self) -> None:
        m = self.q.lineage_mermaid(SVC, depth=2)
        self.assertTrue(m.startswith("flowchart TD"))
        self.assertIn("[CrashLoopBackOff]", m)

    def test_breakdown_boundary(self) -> None:
        self.assertIn("live cluster state", self.q.breakdown())
        ref = {"id": "k8s:core/Service/a/b", "properties": {"status": "Referenced"}}
        schema = sq.SemanticQuery.from_dict({"nodes": [ref]})
        self.assertIn("no live instances", schema.breakdown())


class McpTests(unittest.TestCase):
    def test_tools_listed_and_callable(self) -> None:
        srv = mcp.CodeMapGraphifyMCP(graph=GRAPH)
        names = {t["name"] for t in srv.list_tools()}
        self.assertTrue({"graph_lineage", "graph_query_symbol"} <= names)
        out = srv.call_tool("graph_lineage", {"target": "grafana-alloy-metrics"})
        self.assertIn("mermaid", out)
        self.assertEqual(out["upstream"], [ING])
        sym = srv.call_tool("graph_query_symbol", {"name": "grafana-alloy-metrics"})
        self.assertIn("Definition", sym["definition"])


if __name__ == "__main__":
    unittest.main()
