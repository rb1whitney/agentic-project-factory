import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_query")


def _normalize_graph_schema(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Accept both skill-code-map {nodes: dict, edges: list} and Graphify {nodes: list, links: list}."""
    if isinstance(raw.get("nodes"), dict) and "edges" in raw:
        return raw
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in raw.get("nodes", []):
        if not isinstance(n, dict) or not n.get("id"):
            continue
        nid = n["id"]
        props = dict(n.get("properties") or {})
        entry: Dict[str, Any] = {
            "file": n.get("source_file") or props.get("file", ""),
            "line": props.get("line", 1),
            "type": props.get("type") or n.get("file_type", "symbol"),
        }
        for k, v in props.items():
            if k not in entry:
                entry[k] = v
        nodes[nid] = entry
    edges: List[Dict[str, Any]] = []
    for lnk in raw.get("links", raw.get("edges", [])):
        frm = lnk.get("source", lnk.get("from"))
        to = lnk.get("target", lnk.get("to"))
        typ = lnk.get("relation", lnk.get("type", "relates"))
        if frm and to:
            edges.append(
                {
                    "from": frm,
                    "to": to,
                    "type": typ,
                    "file": lnk.get("file") or nodes.get(frm, {}).get("file", ""),
                    "confidence_score": float(lnk.get("confidence_score", 1.0)),
                    "weight": float(lnk.get("weight", 1.0)),
                }
            )
    return {"nodes": nodes, "edges": edges, "stats": raw.get("graph", {}).get("stats", {})}


class SemanticQuery:
    def __init__(self, graph_file: str) -> None:
        if not os.path.exists(graph_file):
            logger.error(f"Graph file not found: {graph_file}")
            sys.exit(1)

        try:
            with open(graph_file, "r", encoding="utf-8") as f:
                self.graph: Dict[str, Any] = _normalize_graph_schema(json.load(f))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse graph file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            sys.exit(1)

    @classmethod
    def from_dict(cls, graph: Dict[str, Any]) -> "SemanticQuery":
        """Wrap an in-memory graph (CodeMap or Graphify schema) without a file round trip."""
        self = cls.__new__(cls)
        self.graph = _normalize_graph_schema(graph)
        return self

    def owner(self, node_id: str) -> str:
        """Public form of _owner: collapse 'Class.method' to 'Class'."""
        return self._owner(node_id)

    def _matches(self, name: str) -> List[str]:
        """Exact node id, else every 'Class.<name>' method (bare method names are ambiguous)."""
        nodes = self.graph.get("nodes", {})
        if name in nodes:
            return [name]
        return sorted(k for k in nodes if k.endswith("." + name))

    def _owner(self, node_id: str) -> str:
        """Collapse 'Class.method' to 'Class' via rightmost dot so package/module prefixes stay intact."""
        nodes = self.graph.get("nodes", {})
        node = nodes.get(node_id)
        if node and node.get("type") in ("method", "constructor"):
            return node_id.rsplit(".", 1)[0]
        if node is None and "." in node_id and not node_id.startswith(("k8s:", "py:", "go:", "vault:")):
            prefix = node_id.rsplit(".", 1)[0]
            if prefix in nodes or "." not in prefix:
                return prefix
        return node_id

    def find_definition(self, name: str) -> str:
        found = self._matches(name)
        if not found:
            return f"Symbol '{name}' not found."
        nodes = self.graph.get("nodes", {})
        return "\n".join(
            f"Definition of '{m}': {nodes[m].get('file')} at line {nodes[m].get('line')} (Type: {nodes[m].get('type')})"
            for m in found
        )

    def find_usages(self, name: str) -> str:
        targets = set(self._matches(name)) or {name}
        seen = set()
        res: List[str] = []
        for e in self.graph.get("edges", []):
            key = (e.get("from"), e.get("type"), e.get("to"))
            if e.get("to") in targets and key not in seen:
                seen.add(key)
                res.append(f"- Used in {e.get('from')} (Type: {e.get('type')})")
        if not res:
            return f"No usages found for '{name}'."
        return "\n".join([f"Usages of '{name}':"] + res)

    def trace_dependencies(self, target: str) -> str:
        """Outbound edges of a file path, a class (including its methods), or a single method."""
        edges = self.graph.get("edges", [])
        deps = [
            e
            for e in edges
            if e.get("from") == target
            or e.get("file") == target
            or self._owner(str(e.get("from", ""))) == target
            or str(e.get("from", "")).startswith(target + ".")
        ]

        if not deps:
            return f"No outbound dependencies found for {target}."

        res: List[str] = [f"Dependencies of {target}:"]
        seen = set()
        for d in deps:
            key = (d.get("from"), d.get("to"), d.get("type"))
            if key in seen:
                continue
            seen.add(key)
            origin = "" if d.get("from") == target else f" [from {d.get('from')}]"
            res.append(f"- Depends on {d.get('to')} (Type: {d.get('type')}){origin}")
        return "\n".join(res)

    def impact(self, name: str) -> str:
        """Transitive blast radius: every class that reaches `name` through any edge, nearest first."""
        matches = self._matches(name) or [name]
        start = {self._owner(m) for m in matches}
        reverse: Dict[str, set] = {}
        for e in self.graph.get("edges", []):
            src, dst = self._owner(str(e.get("from"))), self._owner(str(e.get("to")))
            if src != dst:
                reverse.setdefault(dst, set()).add(src)

        depth = {s: 0 for s in start}
        via: Dict[str, str] = {}
        frontier = list(start)
        while frontier:
            nxt = []
            for cur in frontier:
                for dep in sorted(reverse.get(cur, ())):
                    if dep not in depth:
                        depth[dep] = depth[cur] + 1
                        via[dep] = cur
                        nxt.append(dep)
            frontier = nxt

        hits = sorted((d, n) for n, d in depth.items() if n not in start)
        if not hits:
            return f"No dependents found for '{name}'."
        return "\n".join([f"Impact of changing '{name}':"] + [f"- {n} (depth {d}, via {via[n]})" for d, n in hits])

    def shortest_path(self, src: str, dst: str, directed: bool = True) -> List[str]:
        """Level-order BFS shortest path between two symbols/resources across directed graph edges."""
        s_nodes = self._matches(src) or [src]
        d_nodes = set(self._matches(dst) or [dst])
        adj: Dict[str, List[str]] = {}
        for e in self.graph.get("edges", []):
            u, v = str(e.get("from", "")), str(e.get("to", ""))
            uo, vo = self._owner(u), self._owner(v)
            for a, b in ((u, v), (uo, vo)):
                if a and b and a != b:
                    adj.setdefault(a, []).append(b)
                    if not directed:
                        adj.setdefault(b, []).append(a)

        parent: Dict[str, Optional[str]] = {s: None for s in s_nodes}
        frontier = list(s_nodes)
        while frontier:
            nxt = []
            for cur in frontier:
                if cur in d_nodes or self._owner(cur) in d_nodes:
                    path: List[str] = []
                    step: Optional[str] = cur
                    while step is not None:
                        path.append(step)
                        step = parent.get(step)
                    return list(reversed(path))
                for nbr in sorted(set(adj.get(cur, []))):
                    if nbr not in parent:
                        parent[nbr] = cur
                        nxt.append(nbr)
            frontier = nxt
        return []

    def diff_impact(self, diff_text: str) -> Dict[str, Any]:
        """Map unified git diff hunks to modified AST symbols and partition transitive dependents."""
        import re
        from pathlib import Path

        modified_files: Dict[str, List[Tuple[int, int]]] = {}
        cur_file: str = ""
        hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                cur_file = line[6:].strip()
                modified_files.setdefault(cur_file, [])
            elif line.startswith("@@ ") and cur_file:
                m = hunk_re.match(line)
                if m:
                    start = int(m.group(1))
                    cnt = int(m.group(2)) if m.group(2) is not None else 1
                    modified_files[cur_file].append((start, start + max(cnt, 1) - 1))

        nodes = self.graph.get("nodes", {})
        by_file_syms: Dict[str, List[Tuple[int, str, Dict[str, Any]]]] = {}
        for nid, info in nodes.items():
            nfile = str(info.get("file", ""))
            if not nfile:
                continue
            matched_f = next(
                (
                    mf
                    for mf in modified_files
                    if nfile == mf or Path(nfile).parts[-len(Path(mf).parts) :] == Path(mf).parts
                ),
                None,
            )
            if matched_f is not None:
                by_file_syms.setdefault(matched_f, []).append((int(info.get("line", 1)), nid, info))

        modified_symbols: List[str] = []
        for mf, sym_list in by_file_syms.items():
            hunks = modified_files.get(mf, [])
            ordered = sorted(sym_list, key=lambda x: (x[0], x[1]))
            if not hunks or len(ordered) == 1:
                modified_symbols.extend(nid for _, nid, _ in ordered)
                continue
            # Partition into fine-grained (method/constructor) vs container (class/module) symbols
            methods = [(ln, nid) for ln, nid, inf in ordered if inf.get("type") in ("method", "constructor")]
            containers = [(ln, nid) for ln, nid, inf in ordered if inf.get("type") not in ("method", "constructor")]

            def _overlapping(items: List[Tuple[int, str]]) -> List[str]:
                hits: List[str] = []
                for idx, (s_line, nid) in enumerate(items):
                    e_line = (items[idx + 1][0] - 1) if (idx + 1 < len(items) and items[idx + 1][0] > s_line) else 10**9
                    if any(hs <= e_line and he >= s_line for hs, he in hunks):
                        hits.append(nid)
                return hits

            m_hits = _overlapping(methods) if methods else []
            c_hits = _overlapping(containers) if containers else []
            if m_hits:
                modified_symbols.extend(m_hits)
            elif c_hits:
                modified_symbols.extend(c_hits)
            else:
                modified_symbols.append(ordered[0][1])

        modified_set = set(modified_symbols) | {
            self._owner(s) for s in modified_symbols if len(by_file_syms.get(nodes.get(s, {}).get("file", ""), [])) <= 1
        }

        reverse: Dict[str, set] = {}
        for e in self.graph.get("edges", []):
            u, v = str(e.get("from", "")), str(e.get("to", ""))
            uo, vo = self._owner(u), self._owner(v)
            if u != v:
                reverse.setdefault(v, set()).add(u)
            if uo != vo:
                reverse.setdefault(vo, set()).add(uo)
            if uo != v:
                reverse.setdefault(v, set()).add(uo)

        depth = {s: 0 for s in modified_set}
        frontier = list(modified_set)
        while frontier:
            nxt = []
            for cur in frontier:
                for dep in sorted(reverse.get(cur, ())):
                    if dep not in depth:
                        depth[dep] = depth[cur] + 1
                        nxt.append(dep)
            frontier = nxt

        impacted_prod: List[str] = []
        impacted_tests: List[str] = []
        impacted_infra: List[str] = []

        for sym, d in sorted(depth.items(), key=lambda kv: (kv[1], kv[0])):
            if d == 0:
                continue
            f = str(nodes.get(sym, {}).get("file", ""))
            fname = Path(f).name.lower() if f else sym.lower()
            if "test" in fname or "/tests/" in f or f.startswith("tests/"):
                if f and f not in impacted_tests:
                    impacted_tests.append(f)
                elif not f and sym not in impacted_tests:
                    impacted_tests.append(sym)
            elif sym.startswith(("k8s:", "vault:")) or f.endswith((".tf", ".yaml", ".yml")):
                impacted_infra.append(sym)
            else:
                impacted_prod.append(sym)

        return {
            "modified_files": sorted(modified_files.keys()),
            "modified_symbols": sorted(modified_symbols),
            "impacted_production": impacted_prod,
            "impacted_tests": impacted_tests,
            "impacted_infra": impacted_infra,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Query semantic relationship graph.")
    parser.add_argument("--graph", default="relationship_graph.json", help="Graph file")
    subparsers = parser.add_subparsers(dest="command")

    # def
    p_def = subparsers.add_parser("find-definition")
    p_def.add_argument("name")

    # usage
    p_usage = subparsers.add_parser("find-usages")
    p_usage.add_argument("name")

    # trace
    p_trace = subparsers.add_parser("trace-dependencies")
    p_trace.add_argument("file", help="File path, class name, or Class.method")

    # impact
    p_impact = subparsers.add_parser("impact")
    p_impact.add_argument("name", help="Class or Class.method; lists transitive dependents")

    # shortest-path
    p_sp = subparsers.add_parser("shortest-path")
    p_sp.add_argument("src")
    p_sp.add_argument("dst")
    p_sp.add_argument("--undirected", action="store_true", help="Ignore edge direction during BFS")

    # diff-impact
    p_diff = subparsers.add_parser("diff-impact")
    p_diff.add_argument("--git-ref", default="HEAD", help="Git ref for git diff (default: HEAD)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    query = SemanticQuery(args.graph)
    if args.command == "find-definition":
        print(query.find_definition(args.name))
    elif args.command == "find-usages":
        print(query.find_usages(args.name))
    elif args.command == "trace-dependencies":
        print(query.trace_dependencies(args.file))
    elif args.command == "impact":
        print(query.impact(args.name))
    elif args.command == "shortest-path":
        p = query.shortest_path(args.src, args.dst, directed=not args.undirected)
        print(" -> ".join(p) if p else f"No path between '{args.src}' and '{args.dst}'.")
    elif args.command == "diff-impact":
        import subprocess

        res = subprocess.run(["git", "diff", args.git_ref], capture_output=True, text=True)
        print(json.dumps(query.diff_impact(res.stdout), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
