import os
import json
import argparse
from pathlib import Path
from tree_sitter_languages import get_language
from tree_sitter import Parser

class RepoAnalyzer:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.parsers = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "yaml": self._setup_parser("yaml")
        }
        self.symbol_map = {}

    def _setup_parser(self, lang_name):
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            print(f"Warning: Could not setup parser for {lang_name}: {e}")
            return None

    def analyze(self):
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                ext = path.suffix.lower()
                if ext == ".java":
                    self._parse_java(path)
                elif ext in [".tf", ".hcl"]:
                    self._parse_hcl(path)
                elif ext in [".yaml", ".yml"]:
                    self._parse_yaml_ansible(path)
        
        return self.symbol_map

    def _parse_java(self, path):
        content = path.read_bytes()
        tree = self.parsers["java"].parse(content)
        root = tree.root_node
        
        # Simple extraction of classes and methods
        symbols = []
        query_str = """
        (class_declaration name: (identifier) @class_name)
        (method_declaration name: (identifier) @method_name)
        """
        query = get_language("java").query(query_str)
        captures = query.captures(root)
        
        for node, tag in captures:
            symbols.append({
                "type": tag,
                "name": content[node.start_byte:node.end_byte].decode("utf-8"),
                "line": node.start_point[0] + 1
            })
        
        if symbols:
            self.symbol_map[str(path.relative_to(self.root_dir))] = symbols

    def _parse_hcl(self, path):
        if not self.parsers["hcl"]: return
        content = path.read_bytes()
        tree = self.parsers["hcl"].parse(content)
        root = tree.root_node
        
        # Extract blocks (resource, module, variable)
        symbols = []
        query_str = """
        (block (identifier) @block_type (string_lit) @block_name)
        (block (identifier) @block_type_no_name)
        """
        query = get_language("hcl").query(query_str)
        captures = query.captures(root)
        
        for node, tag in captures:
            symbols.append({
                "type": tag,
                "name": content[node.start_byte:node.end_byte].decode("utf-8").strip('"'),
                "line": node.start_point[0] + 1
            })
        
        if symbols:
            self.symbol_map[str(path.relative_to(self.root_dir))] = symbols

    def _parse_yaml_ansible(self, path):
        # High level YAML analysis to identify K8s or Ansible
        if not self.parsers["yaml"]: return
        content = path.read_bytes()
        tree = self.parsers["yaml"].parse(content)
        # For YAML, we often just want top level keys (kind, name, hosts, tasks)
        # This is high-level context building
        symbols = []
        # Basic extraction of top level keys
        # ... (Implementation simplified for brevity)
        symbols.append({"type": "yaml_file", "name": path.name, "line": 1})
        self.symbol_map[str(path.relative_to(self.root_dir))] = symbols

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="Directory to analyze")
    parser.add_argument("--output", default="symbol_map.json", help="Output JSON file")
    args = parser.parse_args()
    
    analyzer = RepoAnalyzer(args.dir)
    symbol_map = analyzer.analyze()
    
    with open(args.output, "w") as f:
        json.dump(symbol_map, f, indent=2)
    print(f"Analysis complete. Symbol map saved to {args.output}")
