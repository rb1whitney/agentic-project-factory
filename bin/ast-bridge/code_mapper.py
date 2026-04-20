import os
import json
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from tree_sitter_languages import get_language
from tree_sitter import Parser

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("code_mapper")

class CodeMapper:
    def __init__(self, root_dir: str, cache_dir: str = ".ast_cache") -> None:
        self.root_dir: Path = Path(root_dir)
        self.cache_dir: Path = self.root_dir / cache_dir
        self.cache_file: Path = self.cache_dir / "context_map.json"
        self.os_cache: Dict[str, Any] = {}
        self.parsers: Dict[str, Optional[Parser]] = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "rust": self._setup_parser("rust"),
            "yaml": self._setup_parser("yaml")
        }
        self._load_cache()

    def _setup_parser(self, lang_name: str) -> Optional[Parser]:
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            logger.debug(f"Failed to setup parser for {lang_name}: {e}")
            return None

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.os_cache = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Cache file is corrupted: {e}. Starting fresh.")
                self.os_cache = {}

    def _save_cache(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.os_cache, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache: {e}")

    def get_hash(self, file_path: Path) -> str:
        h = hashlib.blake2b()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    h.update(chunk)
            return h.hexdigest()
        except IOError as e:
            logger.error(f"Could not read {file_path} for hashing: {e}")
            return ""

    def map_repo(self) -> Dict[str, Any]:
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
                    if not current_hash:
                        continue
                    
                    if rel_path not in self.os_cache or self.os_cache[rel_path].get("hash") != current_hash:
                        self._index_file(path, rel_path, current_hash)
                        updated_count += 1
        
        self._save_cache()
        logger.info(f"Mapping complete. {updated_count} files re-indexed.")
        return self.os_cache

    def _index_file(self, path: Path, rel_path: str, file_hash: str) -> None:
        ext = path.suffix.lower()
        try:
            content = path.read_bytes()
        except IOError as e:
            logger.error(f"Failed to read file content for {rel_path}: {e}")
            return

        lang_key = "java" if ext == ".java" else "hcl" if ext in [".tf", ".hcl"] else "rust" if ext == ".rs" else "yaml"
        
        symbols: Dict[str, list[str]] = {"types": [], "functions": []}
        try:
            parser = self.parsers.get(lang_key)
            if parser:
                tree = parser.parse(content)
                if tree:
                    # Language-specific queries for public symbols
                    query_str = ""
                    if lang_key == "java":
                        query_str = "(class_declaration name: (identifier) @name) (method_declaration name: (identifier) @name)"
                    elif lang_key == "rust":
                        query_str = "(struct_item name: (type_identifier) @name) (function_item name: (identifier) @name) (trait_item name: (type_identifier) @name)"
                    elif lang_key == "hcl":
                        query_str = "(block (identifier) @type (string_lit) @name) (variable_expr (identifier) @name)"
                    
                    if query_str:
                        query = get_language(lang_key).query(query_str)
                        for node, tag in query.captures(tree.root_node):
                            try:
                                name = content[node.start_byte:node.end_byte].decode("utf-8").strip('"')
                                if "type" in tag:
                                    symbols["types"].append(name)
                                else:
                                    symbols["functions"].append(name)
                            except UnicodeDecodeError:
                                continue
        except Exception as e:
            logger.warning(f"Error parsing or querying {rel_path}: {e}")

        self.os_cache[rel_path] = {
            "hash": file_hash,
            "summary": "AI Summary Pending...",  # Placeholder for Agentic Synthesis
            "when_to_use": "Use Case Pending...", # Placeholder for Agentic Synthesis
            "public_types": symbols["types"],
            "public_functions": symbols["functions"]
        }

    def serialize_markdown(self, output_file: str = "code_map.md") -> None:
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# Repository Code Map\n\n")
                for path, data in self.os_cache.items():
                    f.write(f"### {path}\n")
                    f.write(f"- **Summary**: {data['summary']}\n")
                    f.write(f"- **When to Use**: {data['when_to_use']}\n")
                    if data.get("public_types"): 
                        f.write(f"- **Public Types**: {', '.join(data['public_types'])}\n")
                    if data.get("public_functions"): 
                        f.write(f"- **Public Functions**: {', '.join(data['public_functions'])}\n")
                    f.write("\n")
            logger.info(f"Serialized markdown map to {output_file}")
        except IOError as e:
            logger.error(f"Failed to serialize markdown map: {e}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Map a repository to AST representations.")
    parser.add_argument("dir", help="Directory to map")
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        logger.error(f"Provided path is not a directory: {args.dir}")
        exit(1)

    mapper = CodeMapper(args.dir)
    mapper.map_repo()
    mapper.serialize_markdown(os.path.join(args.dir, "code_map.md"))

if __name__ == "__main__":
    main()
