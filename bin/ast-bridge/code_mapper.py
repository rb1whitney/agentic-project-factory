import os
import json
import hashlib
import argparse
from pathlib import Path
from tree_sitter_languages import get_language
from tree_sitter import Parser

class CodeMapper:
    def __init__(self, root_dir, cache_dir=".ast_cache"):
        self.root_dir = Path(root_dir)
        self.cache_dir = self.root_dir / cache_dir
        self.cache_file = self.cache_dir / "context_map.json"
        self.os_cache = {}
        self.parsers = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "rust": self._setup_parser("rust"),
            "yaml": self._setup_parser("yaml")
        }
        self._load_cache()

    def _setup_parser(self, lang_name):
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception:
            return None

    def _load_cache(self):
        if self.cache_file.exists():
            with open(self.cache_file, "r") as f:
                self.os_cache = json.load(f)

    def _save_cache(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self.os_cache, f, indent=2)

    def get_hash(self, file_path):
        h = hashlib.blake2b()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    def map_repo(self):
        updated_count = 0
        skip_patterns = ["/temp_", "/.ast_cache/", "/.git/", "/node_modules/", "/skills/"]
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                rel_path = str(path.relative_to(self.root_dir))
                if any(p in "/" + rel_path for p in skip_patterns):
                    continue
                
                ext = path.suffix.lower()
                if ext in [".java", ".tf", ".hcl", ".rs", ".yaml", ".yml", ".py"]:
                    current_hash = self.get_hash(path)
                    
                    if rel_path not in self.os_cache or self.os_cache[rel_path].get("hash") != current_hash:
                        self._index_file(path, rel_path, current_hash)
                        updated_count += 1
        
        self._save_cache()
        print(f"Mapping complete. {updated_count} files re-indexed.")
        return self.os_cache

    def _index_file(self, path, rel_path, file_hash):
        ext = path.suffix.lower()
        content = path.read_bytes()
        lang_key = "java" if ext == ".java" else "hcl" if ext in [".tf", ".hcl"] else "rust" if ext == ".rs" else "yaml"
        
        symbols = {"types": [], "functions": []}
        try:
            if self.parsers.get(lang_key):
                tree = self.parsers[lang_key].parse(content)
                if not tree: return
                
                # Language-specific queries for public symbols
                if lang_key == "java":
                    query_str = "(class_declaration name: (identifier) @name) (method_declaration name: (identifier) @name)"
                elif lang_key == "rust":
                    query_str = "(struct_item name: (type_identifier) @name) (function_item name: (identifier) @name) (trait_item name: (type_identifier) @name)"
                elif lang_key == "hcl":
                    query_str = "(block (identifier) @type (string_lit) @name) (variable_expr (identifier) @name)"

                else:
                    query_str = ""
                
                if query_str:
                    query = get_language(lang_key).query(query_str)
                    for node, tag in query.captures(tree.root_node):
                        try:
                            name = content[node.start_byte:node.end_byte].decode("utf-8").strip('"')
                            if "type" in tag: symbols["types"].append(name)
                            else: symbols["functions"].append(name)
                        except Exception: continue

        except Exception as e:
            print(f"Error indexing {rel_path}: {e}")

        self.os_cache[rel_path] = {
            "hash": file_hash,
            "summary": "AI Summary Pending...",  # Placeholder for Agentic Synthesis
            "when_to_use": "Use Case Pending...", # Placeholder for Agentic Synthesis
            "public_types": symbols["types"],
            "public_functions": symbols["functions"]
        }

    def serialize_markdown(self, output_file="code_map.md"):
        with open(output_file, "w") as f:
            f.write("# Repository Code Map\n\n")
            for path, data in self.os_cache.items():
                f.write(f"### {path}\n")
                f.write(f"- **Summary**: {data['summary']}\n")
                f.write(f"- **When to Use**: {data['when_to_use']}\n")
                if data["public_types"]: f.write(f"- **Public Types**: {', '.join(data['public_types'])}\n")
                if data["public_functions"]: f.write(f"- **Public Functions**: {', '.join(data['public_functions'])}\n")
                f.write("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("dir", help="Directory to map")
    args = parser.parse_args()
    
    mapper = CodeMapper(args.dir)
    mapper.map_repo()
    mapper.serialize_markdown(os.path.join(args.dir, "code_map.md"))
