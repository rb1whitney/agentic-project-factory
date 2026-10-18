import argparse
import hashlib
import importlib.util
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tree_sitter import Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("code_mapper")

# Bump when the shape of a cache entry or an extractor changes; stale entries are re-indexed, never trusted.
CACHE_SCHEMA = 2
MAX_FILE_BYTES = 5 * 1024 * 1024  # generated blobs above this add parse time and no structure


class CodeMapper:
    def __init__(self, root_dir: str, cache_dir: str = ".ast_cache") -> None:
        self.root_dir: Path = Path(root_dir)
        self.cache_dir: Path = self.root_dir / cache_dir
        self.cache_file: Path = self.cache_dir / "context_map.json"
        self.os_cache: Dict[str, Any] = {}
        self.catalogs: Dict[str, str] = {}
        self.io_workers: int = 32  # latency-bound syscalls; not CPU parallelism
        self.max_file_bytes: int = MAX_FILE_BYTES
        self.parse_errors: List[str] = []  # files whose tree contains ERROR nodes (symbols may be partial)
        self.skipped_large: List[str] = []
        self.missing_parsers: set = set()  # languages with files present but no usable grammar
        self._queries: Dict[Tuple[str, str], Any] = {}
        self.graph_files: Optional[List[Path]] = None  # set by map_repo; lets the graph builder skip a second walk
        self.last_updated_count: int = 0
        self.last_pruned_count: int = 0
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

    def _query(self, lang: str, source: str) -> Any:
        """Compile each (language, query) once; per-file compilation dominated runtime on large Go trees."""
        key = (lang, source)
        if key not in self._queries:
            self._queries[key] = get_language(lang).query(source)
        return self._queries[key]

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.os_cache = json.load(f)
                if not isinstance(self.os_cache, dict):
                    raise json.JSONDecodeError("cache root is not an object", "", 0)
            except json.JSONDecodeError as e:
                logger.error(f"Cache file is corrupted: {e}. Starting fresh.")
                self.os_cache = {}

    def _save_cache(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        tmp = self.cache_file.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.os_cache, f, indent=2)
            os.replace(tmp, self.cache_file)  # atomic: an interrupted run cannot leave a truncated cache
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

    def _walk_files(self, skip_dirs: set) -> List[Path]:
        """Breadth-first directory walk, one scandir per directory, run concurrently.

        Mirrors os.walk(followlinks=False) with in-place pruning: symlinked directories are neither
        descended nor listed as files. Listing latency (not CPU) dominates on WSL /mnt/d mounts.
        """

        def scan(directory: Path) -> Tuple[List[Path], List[Path]]:
            files: List[Path] = []
            subdirs: List[Path] = []
            try:
                with os.scandir(directory) as it:
                    for entry in it:
                        if entry.is_dir():
                            if entry.is_symlink() or entry.name in skip_dirs or entry.name.startswith("temp_"):
                                continue
                            subdirs.append(Path(entry.path))
                        else:
                            files.append(Path(entry.path))
            except OSError as e:
                logger.debug(f"Skipping unreadable directory {directory}: {e}")
            return files, subdirs

        found: List[Path] = []
        frontier: List[Path] = [self.root_dir]
        with ThreadPoolExecutor(max_workers=self.io_workers) as pool:
            while frontier:
                nxt: List[Path] = []
                for files, subdirs in pool.map(scan, frontier):
                    found.extend(files)
                    nxt.extend(subdirs)
                frontier = nxt
        return found

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
            "vendor",
        }
        valid_exts = {".java", ".tf", ".hcl", ".rs", ".yaml", ".yml", ".py", ".go"}
        graph_exts = {".java", ".tf", ".hcl", ".go", ".mod", ".py"}
        self.graph_files = []

        # Phase 1: walk (directory listing only, no per-file syscalls).
        candidates: List[Path] = []
        for path in self._walk_files(skip_dirs):
            ext = path.suffix.lower()
            if ext in graph_exts:
                self.graph_files.append(path)
            if ext in valid_exts:
                candidates.append(path)

        # Phase 2: stat everything concurrently. Per-file stat latency (about 2 ms on WSL /mnt/d)
        # dominated warm runs; it is I/O-bound and releases the GIL, so threads scale here.
        def safe_stat(path: Path) -> Optional[list]:
            try:
                st = path.stat()
            except OSError:
                return None
            if st.st_size > self.max_file_bytes:
                self.skipped_large.append(str(path.relative_to(self.root_dir)))
                return None
            return [st.st_mtime_ns, st.st_size]

        with ThreadPoolExecutor(max_workers=self.io_workers) as pool:
            stamps = list(pool.map(safe_stat, candidates))

        # Fast path: unchanged (mtime, size) means no read at all.
        changed: List[Tuple[Path, str, list]] = []
        for path, stamp in zip(candidates, stamps):
            if stamp is None:
                continue
            rel_path = str(path.relative_to(self.root_dir))
            cached = self.os_cache.get(rel_path)
            if not (cached and cached.get("stat") == stamp and cached.get("v") == CACHE_SCHEMA):
                changed.append((path, rel_path, stamp))

        # Phase 3: hash only changed files (also concurrent), then index them serially.
        with ThreadPoolExecutor(max_workers=self.io_workers) as pool:
            hashes = list(pool.map(self.get_hash, [c[0] for c in changed]))

        for (path, rel_path, stamp), current_hash in zip(changed, hashes):
            if not current_hash:
                continue
            cached = self.os_cache.get(rel_path)
            if cached is None or cached.get("hash") != current_hash or cached.get("v") != CACHE_SCHEMA:
                self._index_file(path, rel_path, current_hash)
                updated_count += 1
            if rel_path in self.os_cache:
                self.os_cache[rel_path]["stat"] = stamp

        # Drop entries for files that were deleted, moved, now skipped, or are no longer indexable.
        live = {str(p.relative_to(self.root_dir)) for p in candidates}
        stale = [k for k in self.os_cache if k not in live or k in self.skipped_large]
        for k in stale:
            del self.os_cache[k]

        self.last_updated_count = updated_count
        self.last_pruned_count = len(stale)
        self._save_cache()
        if self.skipped_large:
            logger.warning(f"{len(self.skipped_large)} file(s) over {self.max_file_bytes} bytes skipped")
        if self.parse_errors:
            logger.warning(f"{len(self.parse_errors)} file(s) had syntax errors; symbols may be partial")
        if self.missing_parsers:
            logger.warning(f"No grammar available for: {', '.join(sorted(self.missing_parsers))}; files not indexed")
        logger.info(f"Mapping complete. {updated_count} files re-indexed, {len(stale)} stale entries pruned.")
        return self.os_cache

    def is_warm_noop(self, markdown_path: str, graph_path: Optional[str] = None) -> bool:
        """Return True when zero files were updated or pruned and target output artifacts exist and are non-empty."""
        if self.last_updated_count != 0 or self.last_pruned_count != 0:
            return False
        if not (os.path.isfile(markdown_path) and os.path.getsize(markdown_path) > 0):
            return False
        if graph_path is not None and not (os.path.isfile(graph_path) and os.path.getsize(graph_path) > 0):
            return False
        return True

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
            if not parser and lang_key != "yaml":
                self.missing_parsers.add(lang_key)
            if parser:
                tree = parser.parse(content)
                if tree:
                    # YAML symbols come from PyYAML; helm templates and negative fixtures fail the grammar by design.
                    if tree.root_node.has_error and lang_key != "yaml":
                        self.parse_errors.append(rel_path)
                    if lang_key == "python":
                        query_str = (
                            "(class_definition name: (identifier) @type) (function_definition name: (identifier) @func)"
                        )
                        query = self._query(lang_key, query_str)
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
                            "(method_declaration) @method"
                        )
                        query = self._query(lang_key, query_str)
                        for node, tag in query.captures(tree.root_node):
                            if tag == "method":
                                # Receiver-qualified so methods of different types do not collapse into one name.
                                name_node = node.child_by_field_name("name")
                                recv = node.child_by_field_name("receiver")
                                if name_node is None:
                                    continue
                                name = content[name_node.start_byte : name_node.end_byte].decode(
                                    "utf-8", errors="ignore"
                                )
                                rtype = ""
                                if recv is not None:
                                    tnodes = self._query(lang_key, "(type_identifier) @t").captures(recv)
                                    if tnodes:
                                        n = tnodes[0][0]
                                        rtype = content[n.start_byte : n.end_byte].decode("utf-8", errors="ignore")
                                symbols["functions"].append(f"{rtype}.{name}" if rtype else name)
                                continue
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
                        query = self._query(lang_key, query_str)
                        for node, tag in query.captures(tree.root_node):
                            name = content[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")
                            if tag == "name":
                                symbols["types"].append(name)
                            else:
                                symbols["functions"].append(name)

                    elif lang_key == "hcl":
                        # Terraform blocks: resource, data, module, variable, output
                        query_str = "(block) @block"
                        query = self._query(lang_key, query_str)
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
                        query = self._query(lang_key, query_str)
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
            "v": CACHE_SCHEMA,
            "hash": file_hash,
            "public_types": symbols["types"],
            "public_functions": symbols["functions"],
            "declarations": symbols["declarations"],
        }

    def attach_catalog(self, persist_graph: bool = False, graph_output: Optional[str] = None) -> None:
        """Populate per-file Java catalogs (routes, injections, resolved calls) from the semantic graph."""
        builder_path = Path(__file__).with_name("graph_builder.py")
        spec = importlib.util.spec_from_file_location("graph_builder", str(builder_path))
        if spec is None or spec.loader is None:
            logger.error("graph_builder.py not found next to code_mapper.py; catalog skipped")
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        graph = module.GraphBuilder(str(self.root_dir)).build_graph(files=self.graph_files)
        self.catalogs = module.render_catalog(graph)
        if persist_graph or graph_output:
            target = Path(graph_output) if graph_output else (self.root_dir / "relationship_graph.json")
            tmp = target.with_suffix(".json.tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(graph, f, indent=2)
                os.replace(tmp, target)
            except IOError as e:
                logger.error(f"Failed to persist relationship graph to {target}: {e}")

    def serialize_markdown(self, output_file: str = "code_map.md") -> None:
        target = Path(output_file)
        tmp = target.with_suffix(".md.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write("# Repository Code Map\n\n")
                for path, data in self.os_cache.items():
                    f.write(f"### {path}\n")
                    if data.get("public_types"):
                        f.write(f"- **Public Types**: {', '.join(data['public_types'])}\n")
                    if data.get("public_functions"):
                        f.write(f"- **Public Functions**: {', '.join(data['public_functions'])}\n")
                    if data.get("declarations"):
                        f.write(f"- **Declarations**: {', '.join(data['declarations'])}\n")
                    if self.catalogs.get(path):
                        f.write("- **Catalog**:\n")
                        for line in self.catalogs[path].splitlines():
                            f.write(f"    {line}\n")
                    f.write("\n")
            os.replace(tmp, target)
            logger.info(f"Serialized markdown map to {output_file}")
        except IOError as e:
            logger.error(f"Failed to serialize markdown map: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Map a repository to AST representations.")
    parser.add_argument("dir", help="Directory to map")
    parser.add_argument("--force", action="store_true", help="Force graph and markdown rebuild even when cache is warm")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logger.error(f"Provided path is not a directory: {args.dir}")
        exit(1)

    md_out = os.path.join(args.dir, "code_map.md")
    graph_out = os.path.join(args.dir, "relationship_graph.json")
    mapper = CodeMapper(args.dir)
    mapper.map_repo()
    if not args.force and mapper.is_warm_noop(md_out, graph_out):
        logger.info("Cache warm (0 files changed); skipping graph rebuild and markdown serialization.")
        return
    mapper.attach_catalog(persist_graph=True, graph_output=graph_out)
    mapper.serialize_markdown(md_out)


if __name__ == "__main__":
    main()
