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

    def find_definition(self, name: str) -> str:
        nodes = self.graph.get("nodes", {})
        node = nodes.get(name)
        if node:
            return f"Definition of '{name}': {node.get('file')} at line {node.get('line')} (Type: {node.get('type')})"
        return f"Symbol '{name}' not found."

    def find_usages(self, name: str) -> str:
        edges = self.graph.get("edges", [])
        usages = [e for e in edges if e.get("to") == name]
        if not usages:
            return f"No usages found for '{name}'."

        res: List[str] = [f"Usages of '{name}':"]
        for u in usages:
            res.append(f"- Used in {u.get('from')} (Type: {u.get('type')})")
        return "\n".join(res)

    def trace_dependencies(self, file_path: str) -> str:
        edges = self.graph.get("edges", [])
        deps = [e for e in edges if e.get("from") == file_path]
        if not deps:
            return f"No outbound dependencies found for {file_path}."

        res: List[str] = [f"Dependencies of {file_path}:"]
        for d in deps:
            res.append(f"- Depends on {d.get('to')} (Type: {d.get('type')})")
        return "\n".join(res)


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
    p_trace.add_argument("file")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
