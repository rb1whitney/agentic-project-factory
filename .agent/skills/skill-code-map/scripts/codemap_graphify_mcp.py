#!/usr/bin/env python3
"""
codemap_graphify_mcp.py - Unified Local Graph & ast-grep MCP Server.

Exposes deterministic code/cluster knowledge graph tools and Tree-sitter / ast-grep
structural tools over stdio JSON-RPC 2.0 (Model Context Protocol) and direct Python API.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import auto_context as ac  # noqa: E402
import graph_builder as gb  # noqa: E402
import semantic_query as sq  # noqa: E402


def _sexp(node: Any) -> str:
    """Format Tree-sitter node as S-expression across tree-sitter API versions."""
    if hasattr(node, "sexp"):
        return node.sexp()
    kids = " ".join(_sexp(c) for c in getattr(node, "children", []) if getattr(c, "is_named", True))
    return f"({node.type} {kids})" if kids else f"({node.type})"


class CodeMapGraphifyMCP:
    def __init__(
        self,
        graph: Optional[Dict[str, Any]] = None,
        graph_path: Optional[str] = None,
        src_dir: Optional[str] = None,
    ) -> None:
        if graph is not None:
            self.graph = graph
        elif graph_path and Path(graph_path).is_file():
            self.graph = json.loads(Path(graph_path).read_text(encoding="utf-8"))
        elif src_dir and Path(src_dir).is_dir():
            self.graph = gb.GraphBuilder(src_dir).build_graph()
        else:
            self.graph = {"nodes": {}, "edges": []}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "graph_context_lens",
                "description": (
                    "Rank files/symbols for a task using Personalized PageRank (PPR) and binary-search token packing."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "max_tokens": {"type": "integer", "default": 2000},
                        "top": {"type": "integer", "default": 10},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "graph_diff_impact",
                "description": (
                    "Compute blast radius of a unified git diff partitioned into "
                    "production symbols, test suites, and infra."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"diff_text": {"type": "string"}},
                    "required": ["diff_text"],
                },
            },
            {
                "name": "graph_shortest_path",
                "description": "Find level-order BFS shortest path between two code/K8s/Vault nodes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                    },
                    "required": ["source", "target"],
                },
            },
            {
                "name": "graph_architecture_report",
                "description": (
                    "Generate GRAPH_REPORT.md with God nodes, subsystem communities, and Post-Order Tarjan SCC cycles."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "ast_dump_tree",
                "description": (
                    "Parse a code snippet with Tree-sitter and dump its AST S-expression before writing ast-grep rules."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string"},
                        "code": {"type": "string"},
                    },
                    "required": ["language", "code"],
                },
            },
            {
                "name": "ast_test_rule",
                "description": "Validate an inline ast-grep YAML rule against a code snippet and return JSON matches.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "rule_yaml": {"type": "string"},
                        "code": {"type": "string"},
                        "extension": {"type": "string", "default": ".py"},
                    },
                    "required": ["rule_yaml", "code"],
                },
            },
            {
                "name": "graph_lineage",
                "description": (
                    "Bidirectional N-hop lineage of a node (id, suffix, Kind/name or keyword) with statuses, "
                    "Mermaid flowchart and evidence boundary."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "depth": {"type": "integer", "default": 2},
                    },
                    "required": ["target"],
                },
            },
            {
                "name": "graph_query_symbol",
                "description": (
                    "Symbol lookup: definition, usages, outbound dependencies and impact, plus node/edge breakdown."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
            {
                "name": "graph_env_diff",
                "description": (
                    "Compare two environment layers (Terraform tfvars, Helm values-<env>, Kustomize overlays, Hiera "
                    "appenv): keys only in A, only in B, and differing values. Sensitive values are redacted."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "root": {"type": "string"},
                        "env_a": {"type": "string"},
                        "env_b": {"type": "string"},
                    },
                    "required": ["root", "env_a", "env_b"],
                },
            },
            {
                "name": "graph_state_drift",
                "description": (
                    "IaC-vs-live drift report via state_graph.py. Offline only: pass live_k8s (JSON snapshot path); "
                    "never contacts a cluster from MCP."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "k8s_dirs": {"type": "array", "items": {"type": "string"}},
                        "live_k8s": {"type": "string"},
                        "format": {"type": "string", "enum": ["json", "graphify"], "default": "json"},
                    },
                    "required": ["k8s_dirs", "live_k8s"],
                },
            },
            {
                "name": "graph_k8s_extract",
                "description": (
                    "Build a Graphify K8s graph with k8s_graphify_extract.py from an offline object snapshot "
                    "(live_k8s) or a --cache-dir (no_live). Output graph becomes this server's active graph."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "live_k8s": {"type": "string"},
                        "cache_dir": {"type": "string"},
                        "catalog": {"type": "string"},
                    },
                },
            },
            {
                "name": "well_architected_audit",
                "description": (
                    "Run 6-Pillar Well-Architected Code Audit (SEC, REL, OPS, PERF, COST, SUS) over a Python/Java/Go "
                    "directory with optional PR diff scoping and Kodus-style Markdown policies."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target_dir": {"type": "string"},
                        "diff_text": {"type": "string"},
                        "policies_dir": {"type": "string"},
                    },
                    "required": ["target_dir"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "graph_context_lens":
            lens = ac.ContextLens(self.graph)
            task = arguments["task"]
            max_tokens = int(arguments.get("max_tokens", 2000))
            top = int(arguments.get("top", 10))
            return {
                "ranked": lens.rank(task, top=top),
                "packed": lens.pack_context(task, max_tokens=max_tokens),
            }
        if name == "graph_diff_impact":
            q = sq.SemanticQuery.from_dict(self.graph)
            return q.diff_impact(arguments.get("diff_text", ""))
        if name == "graph_shortest_path":
            q = sq.SemanticQuery.from_dict(self.graph)
            path = q.shortest_path(arguments["source"], arguments["target"])
            return {"path": path, "hops": max(0, len(path) - 1)}
        if name == "graph_lineage":
            q = sq.SemanticQuery.from_dict(self.graph)
            depth = int(arguments.get("depth", 2))
            res = q.lineage(arguments["target"], depth)
            res["mermaid"] = q.lineage_mermaid(arguments["target"], depth)
            res["breakdown"] = q.breakdown()
            return res
        if name == "graph_query_symbol":
            q = sq.SemanticQuery.from_dict(self.graph)
            sym = arguments["name"]
            return {
                "breakdown": q.breakdown(),
                "definition": q.find_definition(sym),
                "usages": q.find_usages(sym),
                "dependencies": q.trace_dependencies(sym),
                "impact": q.impact(sym),
            }
        if name == "graph_env_diff":
            import state_graph as sgm

            return sgm.env_diff(Path(arguments["root"]), arguments["env_a"], arguments["env_b"])
        if name == "graph_state_drift":
            cmd = [sys.executable, str(SCRIPT_DIR / "state_graph.py"), "drift", "--no-live-vault"]
            cmd += ["--k8s", *arguments["k8s_dirs"], "--live-k8s", arguments["live_k8s"]]
            cmd += ["--format", arguments.get("format", "json")]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                return {"error": res.stderr.strip()[-2000:]}
            return json.loads(res.stdout)
        if name == "graph_k8s_extract":
            script = SCRIPT_DIR.parent.parent / "skill-graphify" / "scripts" / "k8s_graphify_extract.py"
            with tempfile.TemporaryDirectory() as d:
                out = Path(d) / "graph.json"
                cmd = [sys.executable, str(script), "--out", str(out)]
                if arguments.get("live_k8s"):
                    cmd += ["--live-k8s", arguments["live_k8s"]]
                elif arguments.get("cache_dir"):
                    cmd += ["--no-live", "--cache-dir", arguments["cache_dir"]]
                else:
                    raise ValueError("graph_k8s_extract needs live_k8s or cache_dir (MCP never queries a cluster)")
                if arguments.get("catalog"):
                    cmd += ["--catalog", arguments["catalog"]]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    return {"error": (res.stderr or res.stdout).strip()[-2000:]}
                self.graph = json.loads(out.read_text(encoding="utf-8"))
            return {
                "nodes": len(self.graph.get("nodes", [])),
                "links": len(self.graph.get("links", [])),
                "diagnostics": self.graph.get("diagnostics", []),
            }
        if name == "graph_architecture_report":
            norm = gb.from_graphify(self.graph)
            return {
                "report_markdown": gb.generate_graph_report(self.graph),
                "cycles": gb.find_cycles_postorder(norm.get("nodes", {}), norm.get("edges", [])),
            }
        if name == "ast_dump_tree":
            from tree_sitter_languages import get_parser

            lang = arguments["language"]
            code = arguments["code"]
            parser = get_parser(lang)
            root = parser.parse(code.encode("utf-8")).root_node
            return {
                "language": lang,
                "sexp": _sexp(root),
                "child_types": [c.type for c in root.children],
            }
        if name == "ast_test_rule":
            raw_ext = str(arguments.get("extension", ".py"))
            clean_ext = re.sub(r"[^A-Za-z0-9]", "", raw_ext) or "py"
            ext = "." + clean_ext
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                rule_file = root / "rule.yml"
                src_file = root / f"snippet{ext}"
                rule_file.write_text(arguments["rule_yaml"], encoding="utf-8")
                src_file.write_text(arguments["code"], encoding="utf-8")
                res = subprocess.run(
                    ["ast-grep", "scan", "--json", "-r", str(rule_file), str(src_file)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0 and not res.stdout.strip():
                    return {"matches": [], "count": 0, "error": res.stderr.strip()}
                matches = json.loads(res.stdout) if res.stdout.strip() else []
                out_res: Dict[str, Any] = {"matches": matches, "count": len(matches)}
                if res.stderr.strip():
                    out_res["stderr"] = res.stderr.strip()
                return out_res
        if name == "well_architected_audit":
            import well_architected_audit as waa

            report = waa.audit_directory(
                arguments["target_dir"],
                diff_text=arguments.get("diff_text"),
                policies_dir=arguments.get("policies_dir"),
            )
            report["markdown"] = waa.render_well_architected_markdown(report)
            return report
        raise ValueError(f"Unknown MCP tool: {name}")

    def handle_rpc(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params") or {}
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "codemap-graphify-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}
        if method == "tools/call":
            try:
                out = self.call_tool(params.get("name", ""), params.get("arguments") or {})
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(out, indent=2)}]},
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
        if req_id is not None:
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Run unified CodeMap + Graphify + ast-grep stdio MCP server.")
    ap.add_argument("--graph", default=None, help="Path to relationship_graph.json or Graphify graph.json")
    ap.add_argument("--src", default=None, help="Source directory to index on startup")
    args = ap.parse_args()
    srv = CodeMapGraphifyMCP(graph_path=args.graph, src_dir=args.src)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue
        resp = srv.handle_rpc(payload)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
