import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from tree_sitter import Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("code_mapper")


class CodeMapper:
    def __init__(self, root_dir: str, cache_dir: str = ".ast_cache") -> None:
        self.root_dir: Path = Path(root_dir)
        self.cache_dir: Path = self.root_dir / cache_dir
        self.cache_file: Path = self.cache_dir / "context_map.json"
        self.os_cache: Dict[str, Any] = {}
        self.parsers: Dict[str, Optional[Parser]] = {
            "python": self._setup_parser("python"),
            "java": self._setup_parser("java"),
            "go": self._setup_parser("go"),
            "hcl": self._setup_parser("hcl"),
            "rust": self._setup_parser("rust"),
            "yaml": self._setup_parser("yaml"),
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
        skip_dirs = {
            ".git",
            ".venv",
            "venv",
            "node_modules",
            "target",
            "build",
            "dist",
            "__pycache__",
            ".ast_cache",
            "temp_",
            "skills",
        }
        valid_exts = {".java", ".tf", ".hcl", ".rs", ".yaml", ".yml", ".py", ".go"}

        for root, dirs, files in os.walk(self.root_dir):
            # Prune skipped directories in-place to avoid descending into large trees like .venv
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith("temp_")]

            for file in files:
                path = Path(root) / file
                ext = path.suffix.lower()
                if ext in valid_exts:
                    rel_path = str(path.relative_to(self.root_dir))
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

        lang_key = (
            "python"
            if ext == ".py"
            else "java"
            if ext == ".java"
            else "go"
            if ext == ".go"
            else "hcl"
            if ext in [".tf", ".hcl"]
            else "rust"
            if ext == ".rs"
            else "yaml"
        )

        symbols: Dict[str, list[str]] = {"types": [], "functions": [], "declarations": []}
        try:
            parser = self.parsers.get(lang_key)
            if parser:
                tree = parser.parse(content)
                if tree:
                    if lang_key == "python":
                        query_str = (
                            "(class_definition name: (identifier) @type) "
                            "(function_definition name: (identifier) @func)"
                        )
                        query = get_language(lang_key).query(query_str)
                        for node, tag in query.captures(tree.root_node):
                            name = content[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
                            if tag == "type":
                                symbols["types"].append(name)
                            else:
                                symbols["functions"].append(name)

                    elif lang_key == "go":
                        query_str = (
                            "(type_spec name: (type_identifier) @type) "
                            "(function_declaration name: (identifier) @func) "
                            "(method_declaration name: (field_identifier) @func)"
                        )
                        query = get_language(lang_key).query(query_str)
                        for node, tag in query.captures(tree.root_node):
                            name = content[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
                            if tag == "type":
                                symbols["types"].append(name)
                            else:
                                symbols["functions"].append(name)

                    elif lang_key == "java":
                        query_str = (
                            "(class_declaration name: (identifier) @name) "
                            "(interface_declaration name: (identifier) @name) "
                            "(method_declaration name: (identifier) @func)"
                        )
                        query = get_language(lang_key).query(query_str)
                        for node, tag in query.captures(tree.root_node):
                            name = content[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
                            if tag == "name":
                                symbols["types"].append(name)
                            else:
                                symbols["functions"].append(name)

                    elif lang_key == "hcl":
                        # Terraform blocks: resource, data, module, variable, output
                        query_str = "(block) @block"
                        query = get_language(lang_key).query(query_str)
                        for node, _ in query.captures(tree.root_node):
                            tokens = []
                            for c in node.children:
                                if c.type in ("identifier", "string_lit"):
                                    val = content[c.start_byte : c.end_byte].decode("utf-8", errors="ignore").strip('"')
                                    tokens.append(val)
                            if len(tokens) >= 3 and tokens[0] in ("resource", "data"):
                                symbols["declarations"].append(f"{tokens[0]}:{tokens[1]}/{tokens[2]}")
                            elif len(tokens) >= 2:
                                symbols["declarations"].append(f"{tokens[0]}:{tokens[1]}")

                    elif lang_key == "rust":
                        query_str = (
                            "(struct_item name: (type_identifier) @name) "
                            "(function_item name: (identifier) @name) "
                            "(trait_item name: (type_identifier) @name)"
                        )
                        query = get_language(lang_key).query(query_str)
                        for node, tag in query.captures(tree.root_node):
                            name = content[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
                            if "type" in tag or "struct" in tag or "trait" in tag:
                                symbols["types"].append(name)
                            else:
                                symbols["functions"].append(name)

                    elif lang_key == "yaml":
                        # Inspect YAML text for Kubernetes and Ansible semantic signatures
                        text = content.decode("utf-8", errors="ignore")
                        if "apiVersion:" in text and "kind:" in text:
                            # Kubernetes manifest
                            import yaml as pyyaml

                            try:
                                docs = list(pyyaml.safe_load_all(text))
                                for doc in docs:
                                    if isinstance(doc, dict):
                                        kind = doc.get("kind", "Unknown")
                                        meta = doc.get("metadata", {})
                                        name = meta.get("name") if isinstance(meta, dict) else None
                                        ns = meta.get("namespace", "default") if isinstance(meta, dict) else "default"
                                        if name:
                                            symbols["declarations"].append(f"k8s:{kind}/{ns}/{name}")
                                        else:
                                            symbols["declarations"].append(f"k8s:{kind}")
                            except Exception:
                                pass
                        elif "hosts:" in text or "tasks:" in text or "roles:" in text:
                            # Ansible playbook/task list
                            import yaml as pyyaml

                            try:
                                docs = list(pyyaml.safe_load_all(text))
                                for doc in docs:
                                    if isinstance(doc, list):
                                        for item in doc:
                                            if isinstance(item, dict):
                                                if "name" in item:
                                                    symbols["declarations"].append(f"ansible:play/{item['name']}")
                                                elif "hosts" in item:
                                                    symbols["declarations"].append(f"ansible:hosts/{item['hosts']}")
                                    elif isinstance(doc, dict):
                                        if "tasks" in doc:
                                            symbols["declarations"].append("ansible:tasks")
                            except Exception:
                                pass
        except Exception as e:
            logger.warning(f"Error parsing or querying {rel_path}: {e}")

        self.os_cache[rel_path] = {
            "hash": file_hash,
            "summary": "AI Summary Pending...",  # Placeholder for Agentic Synthesis
            "when_to_use": "Use Case Pending...",  # Placeholder for Agentic Synthesis
            "public_types": symbols["types"],
            "public_functions": symbols["functions"],
            "declarations": symbols["declarations"],
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
                    if data.get("declarations"):
                        f.write(f"- **Declarations**: {', '.join(data['declarations'])}\n")
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
