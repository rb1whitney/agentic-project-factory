import os
import json
import argparse
from pathlib import Path
from tree_sitter_languages import get_language
from tree_sitter import Parser

class GraphBuilder:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.symbol_table = {}  # name -> {file, line, type}
        self.edges = []         # list of (source_id, target_id, type)
        self.parsers = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "yaml": self._setup_parser("yaml")
        }

    def _setup_parser(self, lang_name):
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception:
            return None

    def build_graph(self):
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

    def _index_java(self, path):
        content = path.read_bytes()
        tree = self.parsers["java"].parse(content)
        query = get_language("java").query("""
            (class_declaration name: (identifier) @name)
            (method_declaration name: (identifier) @name)
        """)
        for node, tag in query.captures(tree.root_node):
            name = content[node.start_byte:node.end_byte].decode("utf-8")
            self.symbol_table[name] = {
                "file": str(path.relative_to(self.root_dir)),
                "line": node.start_point[0] + 1,
                "type": tag
            }

    def _index_hcl(self, path):
        content = path.read_bytes()
        tree = self.parsers["hcl"].parse(content)
        query = get_language("hcl").query("""
            (block (identifier) @type (string_lit) @name)
            (variable (identifier) @name)
        """)
        for node, tag in query.captures(tree.root_node):
            name = content[node.start_byte:node.end_byte].decode("utf-8").strip('"')
            self.symbol_table[name] = {
                "file": str(path.relative_to(self.root_dir)),
                "line": node.start_point[0] + 1,
                "type": tag
            }

    def _link_java(self, path):
        content = path.read_bytes()
        tree = self.parsers["java"].parse(content)
        query = get_language("java").query("(method_invocation name: (identifier) @call)")
        for node, tag in query.captures(tree.root_node):
            name = content[node.start_byte:node.end_byte].decode("utf-8")
            if name in self.symbol_table:
                self.edges.append({
                    "from": str(path.relative_to(self.root_dir)),
                    "to": name,
                    "type": "calls"
                })

    def _link_hcl(self, path):
        content = path.read_bytes()
        tree = self.parsers["hcl"].parse(content)
        query = get_language("hcl").query("(variable_expr (identifier) @usage)")
        for node, tag in query.captures(tree.root_node):
            name = content[node.start_byte:node.end_byte].decode("utf-8")
            if name in self.symbol_table:
                self.edges.append({
                    "from": str(path.relative_to(self.root_dir)),
                    "to": name,
                    "type": "uses"
                })

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="Directory to analyze")
    parser.add_argument("--output", default="relationship_graph.json", help="Output file")
    args = parser.parse_args()
    
    builder = GraphBuilder(args.dir)
    graph = builder.build_graph()
    
    with open(args.output, "w") as f:
        json.dump(graph, f, indent=2)
    print(f"Graph built with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.")
