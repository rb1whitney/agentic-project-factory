import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_query")


class SemanticQuery:
    def __init__(self, graph_file: str) -> None:
        if not os.path.exists(graph_file):
            logger.error(f"Graph file not found: {graph_file}")
            sys.exit(1)

        try:
            with open(graph_file, "r", encoding="utf-8") as f:
                self.graph: Dict[str, Any] = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse graph file: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            sys.exit(1)

    @classmethod
    def from_dict(cls, graph: Dict[str, Any]) -> "SemanticQuery":
        """Wrap an in-memory graph (as returned by GraphBuilder.build_graph) without a file round trip."""
        self = cls.__new__(cls)
        self.graph = graph
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
        """Collapse 'Class.method' to 'Class'. File-path ids (HCL) and unknown ids pass through."""
        node = self.graph.get("nodes", {}).get(node_id)
        if node and node.get("type") in ("method", "constructor"):
            return node_id.split(".")[0]
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
            if e.get("from") == target or e.get("file") == target or str(e.get("from", "")).startswith(target + ".")
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
        return "\n".join(
            [f"Impact of changing '{name}':"] + [f"- {n} (depth {d}, via {via[n]})" for d, n in hits]
        )


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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
