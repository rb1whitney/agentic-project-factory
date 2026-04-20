import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tree_sitter import Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("graph_builder")


class GraphBuilder:
    def __init__(self, root_dir: str) -> None:
        self.root_dir: Path = Path(root_dir)
        self.symbol_table: Dict[str, Dict[str, Any]] = {}  # name -> {file, line, type}
        self.edges: List[Dict[str, str]] = []  # list of {from, to, type}
        self.parsers: Dict[str, Optional[Parser]] = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "yaml": self._setup_parser("yaml"),
        }

    def _setup_parser(self, lang_name: str) -> Optional[Parser]:
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            logger.debug(f"Failed to setup parser for {lang_name}: {e}")
            return None

    def build_graph(self) -> Dict[str, Any]:
        # Pass 1: Indexing all definitions
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                ext = path.suffix.lower()
                if ext == ".java":
                    self._index_java(path)
                elif ext in [".tf", ".hcl"]:
                    self._index_hcl(path)

        # Pass 2: Linking usages
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                ext = path.suffix.lower()
                if ext == ".java":
                    self._link_java(path)
                elif ext in [".tf", ".hcl"]:
                    self._link_hcl(path)

        return {"nodes": self.symbol_table, "edges": self.edges}

    def _index_java(self, path: Path) -> None:
        if not self.parsers.get("java"):
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = self.parsers["java"].parse(content)
        query = get_language("java").query("""
            (class_declaration name: (identifier) @name)
            (method_declaration name: (identifier) @name)
        """)
        for node, tag in query.captures(tree.root_node):
            try:
                name = content[node.start_byte:node.end_byte].decode("utf-8")
                self.symbol_table[name] = {
                    "file": str(path.relative_to(self.root_dir)),
                    "line": node.start_point[0] + 1,
                    "type": tag,
                }
            except UnicodeDecodeError:
                continue

    def _index_hcl(self, path: Path) -> None:
        if not self.parsers.get("hcl"):
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = self.parsers["hcl"].parse(content)
        # HCL definitions are usually blocks (resource, variable, module, etc.)
        query = get_language("hcl").query("""
            (block (identifier) @type (string_lit) @name)
        """)
        for node, tag in query.captures(tree.root_node):
            try:
                name = content[node.start_byte:node.end_byte].decode("utf-8").strip('"')
                self.symbol_table[name] = {
                    "file": str(path.relative_to(self.root_dir)),
                    "line": node.start_point[0] + 1,
                    "type": tag,
                }
            except UnicodeDecodeError:
                continue

    def _link_java(self, path: Path) -> None:
        if not self.parsers.get("java"):
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = self.parsers["java"].parse(content)
        query = get_language("java").query("(method_invocation name: (identifier) @call)")
        for node, tag in query.captures(tree.root_node):
            try:
                name = content[node.start_byte:node.end_byte].decode("utf-8")
                if name in self.symbol_table:
                    self.edges.append({
                        "from": str(path.relative_to(self.root_dir)),
                        "to": name,
                        "type": "calls",
                    })
            except UnicodeDecodeError:
                continue

    def _link_hcl(self, path: Path) -> None:
        if not self.parsers.get("hcl"):
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = self.parsers["hcl"].parse(content)
        query = get_language("hcl").query("(variable_expr (identifier) @usage)")
        for node, tag in query.captures(tree.root_node):
            try:
                name = content[node.start_byte:node.end_byte].decode("utf-8")
                if name in self.symbol_table:
                    self.edges.append({
                        "from": str(path.relative_to(self.root_dir)),
                        "to": name,
                        "type": "uses",
                    })
            except UnicodeDecodeError:
                continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a semantic relationship graph.")
    parser.add_argument("dir", help="Directory to analyze")
    parser.add_argument("--output", default="relationship_graph.json", help="Output file")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logger.error(f"Provided path is not a directory: {args.dir}")
        sys.exit(1)

    builder = GraphBuilder(args.dir)
    logger.info(f"Building graph for {args.dir}...")
    graph = builder.build_graph()

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        logger.info(f"Graph built with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.")
    except IOError as e:
        logger.error(f"Failed to write graph to {args.output}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
