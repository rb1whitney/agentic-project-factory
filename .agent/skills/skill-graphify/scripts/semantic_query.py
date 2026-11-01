import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_query")

# Id namespaces that are path-style (k8s:<group>/<Kind>/<ns>/<name>), never dotted Class.method.
INFRA_PREFIXES = ("k8s:", "py:", "go:", "vault:")


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

    @staticmethod
    def _is_infra_id(node_id: str) -> bool:
        return node_id.startswith(INFRA_PREFIXES)

    @staticmethod
    def _kind_or_ns_name(node_id: str, first: str, last: str) -> bool:
        parts = node_id[4:].split("/")
        return len(parts) >= 3 and parts[-1] == last and first in (parts[1], parts[-2])

    def _matches(self, name: str) -> List[str]:
        """Exact id, else 'Class.<name>' methods, else 'Kind/name', else substring over infra ids (k8s:/vault:/py:/go:),
        else path suffix; code symbols are never substring-matched."""
        nodes = self.graph.get("nodes", {})
        if name in nodes:
            return [name]
        found = sorted(k for k in nodes if k.endswith("." + name))
        if found:
            return found
        if name.count("/") == 1:
            # 'Kind/name' or 'ns/name' against k8s:<group>/<Kind>/<ns>/<name>
            first, last = name.split("/")
            found = sorted(k for k in nodes if k.startswith("k8s:") and self._kind_or_ns_name(k, first, last))
            if found:
                return found
        needle = name.lower()
        infra = sorted(k for k in nodes if self._is_infra_id(k) and needle in k.lower())
        if infra:
            return infra
        return sorted(k for k in nodes if k.endswith(("/" + name, ":" + name)))

    def _owner(self, node_id: str) -> str:
        """Collapse 'Class.method' to 'Class' via rightmost dot so package/module prefixes stay intact."""
        nodes = self.graph.get("nodes", {})
        node = nodes.get(node_id)
        if node and node.get("type") in ("method", "constructor"):
            return node_id.rsplit(".", 1)[0]
        if node is None and "." in node_id and not node_id.startswith(INFRA_PREFIXES):
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

    def breakdown(self) -> str:
        """Node/edge type counts plus evidence boundary: schema-only vs live instances."""
        nodes = self.graph.get("nodes", {})
        edges = self.graph.get("edges", [])
        by_type: Dict[str, int] = {}
        status: Dict[str, int] = {}
        for info in nodes.values():
            by_type[str(info.get("type", "?"))] = by_type.get(str(info.get("type", "?")), 0) + 1
            if info.get("status"):
                status[str(info["status"])] = status.get(str(info["status"]), 0) + 1
        by_edge: Dict[str, int] = {}
        for e in edges:
            by_edge[str(e.get("type"))] = by_edge.get(str(e.get("type")), 0) + 1
        fmt = lambda d: ", ".join(f"{k}={v}" for k, v in sorted(d.items(), key=lambda kv: -kv[1])) or "none"  # noqa: E731
        k8s_nodes = [i for i in nodes if i.startswith("k8s:")]
        if k8s_nodes:
            live = sum(1 for i in k8s_nodes if nodes[i].get("status") not in (None, "Referenced", "Schema"))
            boundary = "live cluster state" if live else "schema/manifest only (no live instances)"
        else:
            boundary = "static AST"
        return "\n".join(
            [
                f"Nodes ({len(nodes)}): {fmt(by_type)}",
                f"Edges ({len(edges)}): {fmt(by_edge)}",
                f"Status: {fmt(status)}",
                f"Evidence boundary: {boundary}",
            ]
        )

    def query(self, keyword: str, limit: int = 25) -> str:
        found = self._matches(keyword)
        nodes = self.graph.get("nodes", {})
        lines = [self.breakdown(), "", f"Matches for '{keyword}': {len(found)}"]
        for m in found[:limit]:
            info = nodes[m]
            extra = f" status={info['status']}" if info.get("status") else ""
            lines.append(f"- {m} (type={info.get('type')}){extra}")
        if len(found) > limit:
            lines.append(f"... {len(found) - limit} more")
        return "\n".join(lines)

    def lineage(self, target: str, depth: int = 2) -> Dict[str, Any]:
        """Bidirectional BFS: upstream = who points at target, downstream = what target points at."""
        starts = self._matches(target)
        nodes = self.graph.get("nodes", {})
        out: Dict[str, List[str]] = {}
        inc: Dict[str, List[str]] = {}
        for e in self.graph.get("edges", []):
            u, v = str(e.get("from", "")), str(e.get("to", ""))
            out.setdefault(u, []).append(v)
            inc.setdefault(v, []).append(u)

        def walk(adj: Dict[str, List[str]]) -> Dict[str, int]:
            seen = {s: 0 for s in starts}
            frontier = list(starts)
            for d in range(1, depth + 1):
                nxt = []
                for cur in frontier:
                    for nb in sorted(set(adj.get(cur, []))):
                        if nb not in seen:
                            seen[nb] = d
                            nxt.append(nb)
                frontier = nxt
            return seen

        up, down = walk(inc), walk(out)
        keep = set(up) | set(down)
        edges = [
            e
            for e in self.graph.get("edges", [])
            if str(e.get("from")) in keep and str(e.get("to")) in keep
            and (str(e.get("from")) in up and str(e.get("to")) in up
                 or str(e.get("from")) in down and str(e.get("to")) in down)
        ]
        return {
            "targets": starts,
            "upstream": sorted(n for n in up if n not in starts),
            "downstream": sorted(n for n in down if n not in starts),
            "edges": [{"from": e["from"], "to": e["to"], "type": e.get("type")} for e in edges],
            "statuses": {n: nodes.get(n, {}).get("status") for n in keep if nodes.get(n, {}).get("status")},
        }

    def lineage_mermaid(self, target: str, depth: int = 2) -> str:
        lin = self.lineage(target, depth)
        ids: Dict[str, str] = {}

        def nid(n: str) -> str:
            return ids.setdefault(n, f"n{len(ids)}")

        lines = ["flowchart TD"]
        for e in lin["edges"]:
            lines.append(f"  {nid(e['from'])} -->|{e['type']}| {nid(e['to'])}")
        if not lin["edges"]:
            for t in lin["targets"]:
                nid(t)
        for n, i in ids.items():
            st = lin["statuses"].get(n)
            label = (n + (f" [{st}]" if st else "")).replace('"', "'")
            lines.append(f'  {i}["{label}"]')
            if n in lin["targets"]:
                lines.append(f"  style {i} stroke-width:3px")
        return "\n".join(lines)

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

    # query
    p_q = subparsers.add_parser("query")
    p_q.add_argument("keyword", help="Node id, suffix, Kind/name, or substring (k8s:/vault: ids)")

    # lineage
    p_l = subparsers.add_parser("lineage")
    p_l.add_argument("target")
    p_l.add_argument("--depth", type=int, default=2)
    p_l.add_argument("--mermaid", action="store_true", help="Emit a Mermaid flowchart TD block")

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
    elif args.command == "query":
        print(query.query(args.keyword))
    elif args.command == "lineage":
        if args.mermaid:
            print(query.lineage_mermaid(args.target, args.depth))
        else:
            print(json.dumps(query.lineage(args.target, args.depth), indent=2))
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
