import argparse
import collections
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tree_sitter import Parser
from tree_sitter_languages import get_language

sys.path.insert(0, str(Path(__file__).resolve().parent))
from safe_io import clean_text, clean_tree, git_argv, is_secret, readable, write_atomic  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("graph_builder")


# Same exclusions as code_mapper.py; keeps repo-wide runs (session start) from walking vendor trees.
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "build",
    "dist",
    "__pycache__",
    ".ast_cache",
    "skills",
    "vendor",
}


SOURCE_SUFFIXES = {".java", ".go", ".py", ".tf", ".hcl", ".tfvars", ".yaml", ".yml"}


class GraphBuilder:
    def __init__(self, root_dir: str) -> None:
        self.root_dir: Path = Path(root_dir)
        self.symbol_table: Dict[str, Dict[str, Any]] = {}  # name -> {file, line, type}
        self.edges: List[Dict[str, str]] = []  # list of {from, to, type, file}
        self._queries: Dict[Tuple[str, str], Any] = {}
        self.java_classes: Dict[str, Dict[str, Any]] = {}  # class node id -> parse info
        self._java_by_name: Dict[str, List[str]] = {}  # name within its file (`Outer.Inner`) -> node ids
        self._java_by_fqn: Dict[str, List[str]] = {}  # `pkg.Outer.Inner` -> node ids
        self._java_ambiguous: Set[Tuple[str, str]] = set()  # (file, reference) left unlinked, not guessed
        self._java_resolved: Dict[Tuple[str, str], Optional[str]] = {}  # (class, reference) -> node id
        self._edge_keys: Set[Tuple[str, str, str]] = set()
        self.stats: Dict[str, int] = {"calls_resolved": 0, "calls_unresolved": 0}
        self.skipped_files: List[str] = []  # unreadable inputs, so an answer can say what is missing
        self._java_trees: Dict[str, Any] = {}
        self._keep_trees = True
        self.parsers: Dict[str, Optional[Parser]] = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "go": self._setup_parser("go"),
            "python": self._setup_parser("python"),
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

    def _query(self, lang: str, source: str) -> Any:
        """Compile each (language, query) once; compiling per file dominated HCL runtime."""
        key = (lang, source)
        if key not in self._queries:
            self._queries[key] = get_language(lang).query(source)
        return self._queries[key]

    def build_graph(self, files: Optional[List[Path]] = None) -> Dict[str, Any]:
        """Build the graph. Pass `files` (e.g. from code_mapper's walk) to avoid walking the tree twice."""
        if files is None:
            files = []
            for dirpath, dirs, names in os.walk(self.root_dir):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("temp_")]
                files.extend(Path(dirpath) / n for n in names)
        allowed = []
        for f in files:
            if SKIP_DIRS.intersection(f.relative_to(self.root_dir).parts[:-1]):
                continue
            if readable(f, self.root_dir):
                allowed.append(f)
            elif f.suffix.lower() in SOURCE_SUFFIXES:
                self.skipped_files.append(clean_text(f.relative_to(self.root_dir)))
        files = allowed
        java_files = [p for p in files if p.suffix.lower() == ".java"]
        hcl_files = [p for p in files if p.suffix.lower() in (".tf", ".hcl")]
        tfvars_files = [p for p in files if p.suffix.lower() == ".tfvars"]

        self._build_go(files)
        self._build_python(files)

        # Pass 1: index all definitions (Java needs the full class set before linking).
        # Each file is parsed exactly once; the trees are reused by pass 2.
        self._keep_trees = len(java_files) <= self.KEEP_TREES_MAX_FILES
        java_units = [u for u in (self._parse_java(p) for p in java_files) if u]
        self._java_trees = {u["rel"]: u.pop("tree") for u in java_units if u["tree"] is not None}
        self._index_java_units(java_units)
        self._record_java_gaps(java_units)
        hcl_units = [u for u in (self._parse_hcl(p) for p in hcl_files) if u]
        for unit in hcl_units:
            self._index_hcl(unit)

        self._index_tf_modules_json(hcl_files)

        # Pass 2: link usages
        self._link_java_units(java_units)
        self._java_trees = {}
        for unit in hcl_units:
            self._link_hcl(unit)
        for p in tfvars_files:
            self._index_tfvars(p)

        # `throw new X()` is already a throws edge; drop the redundant uses-type twin.
        thrown = {(e["from"], e["to"]) for e in self.edges if e["type"] == "throws"}
        self.edges = [e for e in self.edges if not (e["type"] == "uses-type" and (e["from"], e["to"]) in thrown)]

        return {
            "nodes": self.symbol_table,
            "edges": self.edges,
            "stats": self.stats,
            "skipped_files": self.skipped_files,
        }

    # --- Go: package-level graph (nodes = directories, edges = in-repo imports) ----
    # Import paths resolve through every go.mod found (root + staging modules), longest
    # module prefix first. External/stdlib imports resolve to nothing and emit no edge.
    # _test.go files and vendor/ are excluded: they are not part of the runtime architecture.

    def _build_go(self, files: List[Path]) -> None:
        parser = self.parsers.get("go")
        files = [p for p in files if not SKIP_DIRS.intersection(p.relative_to(self.root_dir).parts[:-1])]
        go_files = [p for p in files if p.suffix == ".go" and not p.name.endswith("_test.go")]
        if not parser or not go_files:
            return
        modules: List[Tuple[str, str]] = []  # (module path, rel dir)
        for p in files:
            if p.name == "go.mod":
                try:
                    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                        if line.startswith("module "):
                            rel = str(p.parent.relative_to(self.root_dir))
                            modules.append((line.split(None, 1)[1].strip().strip('"'), "" if rel == "." else rel))
                            break
                except OSError:
                    continue
        modules.sort(key=lambda m: -len(m[1]))  # deepest module dir wins (nested staging modules)
        imp_q = self._query("go", "(import_spec path: (interpreted_string_literal) @imp)")
        type_q = self._query("go", "(type_spec name: (type_identifier) @name type: _ @kind)")
        pkg_imports: Dict[str, Set[str]] = {}
        cobra_pending: List[Tuple[str, str, str, str]] = []  # (parent func id, qualifier, callee name, file)
        for path in go_files:
            try:
                src = path.read_bytes()
            except IOError:
                continue
            root = parser.parse(src).root_node
            rel_dir = str(path.parent.relative_to(self.root_dir))
            rel_dir = "" if rel_dir == "." else rel_dir
            nid = "go:" + (rel_dir or ".")
            node = self.symbol_table.get(nid)
            if node is None:
                mod = next(
                    ((m, d) for m, d in modules if rel_dir == d or rel_dir.startswith(d + "/" if d else "")), None
                )
                ipath = ""
                if mod:
                    sub = rel_dir[len(mod[1]) :].lstrip("/")
                    ipath = mod[0] + ("/" + sub if sub else "")
                node = {
                    "file": rel_dir,
                    "line": 1,
                    "type": "go-package",
                    "package": "",
                    "import_path": ipath,
                    "interfaces": [],
                    "structs": [],
                    "files": 0,
                }
                self.symbol_table[nid] = node
            node["files"] += 1
            for child in root.children:
                if child.type == "package_clause" and not node["package"]:
                    node["package"] = self._txt(child, src).split(None, 1)[1].strip()
            for n, tag in type_q.captures(root):
                if tag == "name":
                    name, kind = self._txt(n, src), None
                    nxt = n.next_named_sibling
                    kind = nxt.type if nxt else ""
                    if kind == "interface_type":
                        node["interfaces"].append(name)
                    elif kind == "struct_type":
                        node["structs"].append(name)
            pkg_imports.setdefault(nid, set()).update(self._txt(n, src).strip('"`') for n, _ in imp_q.captures(root))
            self._go_functions(root, src, nid, str(path.relative_to(self.root_dir)), cobra_pending)
        by_ipath = {
            n["import_path"]: nid
            for nid, n in self.symbol_table.items()
            if n.get("type") == "go-package" and n["import_path"]
        }
        for nid, imps in pkg_imports.items():
            for imp in sorted(imps):
                target = by_ipath.get(imp)
                if target and target != nid:
                    self._add_edge(nid, target, "imports", self.symbol_table[nid]["file"])
        self._link_cobra(cobra_pending)

    # Exported functions/methods become nodes (public API surface); `parent.AddCommand(NewXCmd(...))` inside a
    # function emits parent-func -> NewXCmd "adds-command" edges. Call sites in general are not tracked.
    def _go_functions(
        self, root: Any, src: bytes, pkg_id: str, rel_file: str, cobra_pending: List[Tuple[str, str, str, str]]
    ) -> None:
        stack = [root]
        while stack:
            n = stack.pop()
            stack.extend(reversed(n.children))
            if n.type not in ("function_declaration", "method_declaration"):
                continue
            name_node = n.child_by_field_name("name")
            if name_node is None:
                continue
            name = self._txt(name_node, src)
            recv = ""
            if n.type == "method_declaration":
                rn = n.child_by_field_name("receiver")
                m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\)?\s*$", self._txt(rn, src)) if rn is not None else None
                recv = m.group(1) if m else ""
            has_add = b"AddCommand" in src[n.start_byte : n.end_byte]
            if not name[:1].isupper() and not has_add:
                continue
            fid = f"{pkg_id}#{recv + '.' if recv else ''}{name}"
            self.symbol_table[fid] = {
                "file": rel_file,
                "line": n.start_point[0] + 1,
                "type": "go-method" if recv else "go-func",
                "package": pkg_id,
            }
            self._add_edge(pkg_id, fid, "defines", rel_file)
            if has_add:
                self._collect_add_command(n, src, fid, rel_file, cobra_pending)

    def _collect_add_command(
        self, fn: Any, src: bytes, fid: str, rel_file: str, out: List[Tuple[str, str, str, str]]
    ) -> None:
        stack = [fn]
        while stack:
            n = stack.pop()
            stack.extend(n.children)
            if n.type != "call_expression":
                continue
            f = n.child_by_field_name("function")
            if f is None or f.type != "selector_expression":
                continue
            fld = f.child_by_field_name("field")
            if fld is None or self._txt(fld, src) != "AddCommand":
                continue
            args = n.child_by_field_name("arguments")
            for a in args.named_children if args is not None else []:
                if a.type != "call_expression":
                    continue
                cf = a.child_by_field_name("function")
                if cf is None:
                    continue
                if cf.type == "selector_expression":
                    q, c = cf.child_by_field_name("operand"), cf.child_by_field_name("field")
                    if q is not None and c is not None:
                        out.append((fid, self._txt(q, src), self._txt(c, src), rel_file))
                elif cf.type == "identifier":
                    out.append((fid, "", self._txt(cf, src), rel_file))

    def _link_cobra(self, pending: List[Tuple[str, str, str, str]]) -> None:
        by_name: Dict[str, List[str]] = {}
        for nid, node in self.symbol_table.items():
            if node.get("type") == "go-func":
                by_name.setdefault(nid.split("#", 1)[1], []).append(nid)
        for parent, qual, callee, rel_file in pending:
            cands = by_name.get(callee, [])
            if qual:
                pkgs = {nid: self.symbol_table[self.symbol_table[nid]["package"]] for nid in cands}
                cands = [
                    n for n in cands if pkgs[n].get("package") == qual or pkgs[n]["file"].rsplit("/", 1)[-1] == qual
                ]
            else:
                same = [n for n in cands if self.symbol_table[n]["package"] == self.symbol_table[parent]["package"]]
                cands = same or cands
            if len(cands) == 1:
                self._add_edge(parent, cands[0], "adds-command", rel_file)

    # --- Python: module-level graph (nodes = modules, edges = in-repo imports / inheritance) ----
    # Imports are matched against the repo's own module table. Absolute imports that carry a prefix
    # from outside the mapped root (e.g. `projects.vault_controller.lib.x` with root=vault_controller)
    # resolve by dropping leading components. Stdlib and third-party names never match, so no edge.

    def _py_module_name(self, path: Path) -> Tuple[str, bool]:
        parts = list(path.relative_to(self.root_dir).with_suffix("").parts)
        is_pkg = parts[-1] == "__init__"
        if is_pkg:
            parts = parts[:-1]
        return ".".join(parts), is_pkg

    def _py_resolve(self, dotted: str, table: Dict[str, str]) -> Optional[str]:
        parts = dotted.split(".")
        for i in range(len(parts)):
            rest = parts[i:]
            cand = ".".join(rest)
            if cand in table:
                return table[cand]
            if i == 0 and parts[0] in sys.stdlib_module_names:
                return None
        return None

    def _build_python(self, files: List[Path]) -> None:
        parser = self.parsers.get("python")
        py_files = [p for p in files if p.suffix == ".py"]
        if not parser or not py_files:
            return
        table: Dict[str, str] = {}
        units = []
        for path in py_files:
            try:
                src = path.read_bytes()
            except IOError:
                continue
            dotted, is_pkg = self._py_module_name(path)
            if not dotted:
                continue
            root = parser.parse(src).root_node
            nid = "py:" + dotted
            node = {
                "file": str(path.relative_to(self.root_dir)),
                "line": 1,
                "type": "py-module",
                "classes": [],
                "functions": [],
                "inherits": {},
            }
            for child in root.children:
                target = child
                if child.type == "decorated_definition":
                    target = child.child_by_field_name("definition") or child
                name_node = target.child_by_field_name("name")
                if name_node is None:
                    continue
                name = self._txt(name_node, src)
                if target.type == "class_definition":
                    node["classes"].append(name)
                    sup = target.child_by_field_name("superclasses")
                    if sup is not None:
                        node["inherits"][name] = [
                            self._txt(c, src) for c in sup.children if c.type in ("identifier", "attribute")
                        ]
                elif target.type == "function_definition":
                    node["functions"].append(name)
            self.symbol_table[nid] = node
            table[dotted] = nid
            units.append((nid, dotted, is_pkg, root, src))

        imp_q = self._query("python", "(import_statement) @i (import_from_statement) @f")
        for nid, dotted, is_pkg, root, src in units:
            rel = self.symbol_table[nid]["file"]
            pkg = dotted if is_pkg else dotted.rpartition(".")[0]
            local: Dict[str, str] = {}  # imported name -> module node id (for inheritance)
            for node, tag in imp_q.captures(root):
                if tag == "i":
                    for c in node.children:
                        if c.type in ("dotted_name", "aliased_import"):
                            dn = c if c.type == "dotted_name" else c.child_by_field_name("name")
                            alias = None if c.type == "dotted_name" else c.child_by_field_name("alias")
                            target = self._py_resolve(self._txt(dn, src), table)
                            if target:
                                self._add_edge(nid, target, "imports", rel)
                                if alias is not None:
                                    local[self._txt(alias, src)] = target
                    continue
                module, names, seen_import = "", [], False
                for c in node.children:
                    if c.type == "import":
                        seen_import = True
                    elif not seen_import and c.type == "dotted_name":
                        module = self._txt(c, src)
                    elif not seen_import and c.type == "relative_import":
                        dots, tail = 0, ""
                        for rc in c.children:
                            if rc.type == "import_prefix":
                                dots = len(self._txt(rc, src))
                            elif rc.type == "dotted_name":
                                tail = self._txt(rc, src)
                        base = pkg.split(".") if pkg else []
                        base = base[: len(base) - (dots - 1)] if dots > 1 else base
                        module = ".".join(base + ([tail] if tail else []))
                    elif seen_import and c.type in ("dotted_name", "aliased_import"):
                        nn = c if c.type == "dotted_name" else c.child_by_field_name("name")
                        al = None if c.type == "dotted_name" else c.child_by_field_name("alias")
                        names.append((self._txt(nn, src), self._txt(al, src) if al is not None else None))
                for nm, al in names:
                    target = self._py_resolve(f"{module}.{nm}" if module else nm, table)
                    if target is None:  # `from pkg.mod import Symbol`: the module itself is the dependency
                        target = self._py_resolve(module, table) if module else None
                    if target:
                        self._add_edge(nid, target, "imports", rel)
                        local[al or nm] = target
                if not names and module:  # wildcard import
                    target = self._py_resolve(module, table)
                    if target:
                        self._add_edge(nid, target, "imports", rel)
            for cname, bases in self.symbol_table[nid]["inherits"].items():
                for b in bases:
                    target = local.get(b.split(".")[0])
                    if target and target != nid:
                        self._add_edge(nid, target, "inherits", rel)

    # --- Java: class-keyed nodes, typed edges, receiver-resolved calls ----------
    # Tree-sitter is syntactic only. Calls resolve through declared field/param/local
    # types and static class names; anything else (JDK, logger, chained calls) emits no
    # edge, so every edge present is a verified syntactic fact, never a name-match guess.

    _CLASS_NODES = (
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
        "annotation_type_declaration",
    )
    # Reflection and dynamic-dispatch call sites a syntax graph cannot follow (textual count, reported as a gap).
    # `import static a.b.C.member;` or `import static a.b.C.*;` -> (class path, member or *)
    _STATIC_IMPORT = re.compile(r"\s*import\s+static\s+([\w.]+)\.(\w+|\*)\s*;")
    _DYNAMIC = re.compile(
        r"\bClass\s*\.\s*forName\s*\(|\.\s*(?:newInstance|getDeclaredMethod|getMethod|getDeclaredConstructor|invoke)\s*\("
    )
    _TYPE_NODES = ("type_identifier", "generic_type", "scoped_type_identifier")
    _STEREOTYPES = {"Service", "Component", "Controller", "RestController", "Repository", "Configuration"}
    _INJECT_ANNOTATIONS = {"Autowired", "Inject", "Resource"}
    _MAPPING_VERBS = {
        "GetMapping": "GET",
        "PostMapping": "POST",
        "PutMapping": "PUT",
        "DeleteMapping": "DELETE",
        "PatchMapping": "PATCH",
        "RequestMapping": "ANY",
    }

    @staticmethod
    def _txt(node: Any, src: bytes) -> str:
        return src[node.start_byte : node.end_byte].decode("utf-8", errors="ignore")

    def _parse_java(self, path: Path) -> Optional[Dict[str, Any]]:
        parser = self.parsers.get("java")
        if not parser:
            return None
        try:
            src = path.read_bytes()
        except IOError:
            self.skipped_files.append(str(path.relative_to(self.root_dir)))
            return None
        root = parser.parse(src).root_node
        pkg = ""
        imports = []
        static_imports: List[Tuple[str, str]] = []
        for c in root.children:
            if c.type == "package_declaration":
                pkg = self._txt(c, src).replace("package", "").replace(";", "").strip()
            elif c.type == "import_declaration":
                m = self._STATIC_IMPORT.match(self._txt(c, src))
                if m:
                    static_imports.append((m.group(1), m.group(2)))
                imp = self._txt(c, src).replace("import", "").replace("static", "").replace(";", "").strip()
                if imp:
                    imports.append(imp)
        return {
            "rel": str(path.relative_to(self.root_dir)),
            "src": src,
            "decls": [(cls.start_byte, qname) for cls, qname in self._iter_classes(root, src)],
            "tree": root if self._keep_trees else None,
            "package": pkg,
            "imports": imports,
            "static_imports": static_imports,
            "has_error": bool(root.has_error),
            "dynamic_sites": len(self._DYNAMIC.findall(src.decode("utf-8", errors="ignore"))),
        }

    # A tree costs a few hundred KB, so keeping all of them is fine for a service and not for a monolith.
    KEEP_TREES_MAX_FILES = int(os.environ.get("CODEMAP_KEEP_TREES_MAX", "2000"))

    def _java_tree(self, rel: str, src: bytes) -> Any:
        """The kept tree for a small repository; otherwise parse again and let the caller drop it."""
        return self._java_trees.get(rel) or self.parsers["java"].parse(src).root_node

    def _iter_classes(self, root: Any, src: bytes):
        """Pre-order DFS yielding (class_node, qualified_name) so outer class context flows down to inner classes."""
        stack: List[Tuple[Any, str]] = [(root, "")]
        while stack:
            node, parent_cls = stack.pop()
            cur_cls = parent_cls
            if node.type in self._CLASS_NODES:
                name_node = node.child_by_field_name("name")
                if name_node is not None:
                    simple = self._txt(name_node, src)
                    cur_cls = f"{parent_cls}.{simple}" if parent_cls else simple
                    yield node, cur_cls
            for child in reversed(node.children):
                stack.append((child, cur_cls))

    def _type_names(self, node: Any, src: bytes) -> List[str]:
        """Type identifiers under a type node in source order; first is the primary type."""
        names: List[str] = []
        stack = [node]
        while stack:
            n = stack.pop()
            if n.type == "type_identifier":
                names.append(self._txt(n, src))
            else:
                stack.extend(reversed(n.children))
        return names

    def _annotations(self, decl: Any, src: bytes) -> List[Tuple[str, Any]]:
        out: List[Tuple[str, Any]] = []
        for mods in (c for c in decl.children if c.type == "modifiers"):
            for c in mods.children:
                if c.type in ("marker_annotation", "annotation"):
                    name = c.child_by_field_name("name")
                    if name is not None:
                        out.append((self._txt(name, src).split(".")[-1], c))
        return out

    def _first_string(self, node: Any, src: bytes) -> Optional[str]:
        stack = [node]
        while stack:
            n = stack.pop()
            if n.type == "string_literal":
                return self._txt(n, src).strip('"')
            stack.extend(reversed(n.children))
        return None

    def _annotation_path(self, ann: Any, src: bytes) -> str:
        args = ann.child_by_field_name("arguments")
        if args is None:
            return ""
        for c in args.children:
            if c.type == "string_literal":
                return self._txt(c, src).strip('"')
            if c.type == "element_value_pair":
                key, val = c.child_by_field_name("key"), c.child_by_field_name("value")
                if key is not None and val is not None and self._txt(key, src) in ("value", "path"):
                    lit = self._first_string(val, src)
                    if lit is not None:
                        return lit
        return ""

    def _direct_types(self, header: Any) -> List[Any]:
        out: List[Any] = []
        for c in header.children:
            if c.type in self._TYPE_NODES:
                out.append(c)
            elif c.type == "type_list":
                out.extend(self._direct_types(c))
        return out

    def _bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n

    def _record_java_gaps(self, units: List[Dict[str, Any]]) -> None:
        """Count what a syntax graph cannot see, so answers can say where the map is blind."""
        self._bump("java_files", len(units))
        self._bump("java_parse_error_files", sum(1 for u in units if u.get("has_error")))
        self._bump("java_dynamic_call_sites", sum(u.get("dynamic_sites", 0) for u in units))
        self._bump("java_files_with_dynamic_sites", sum(1 for u in units if u.get("dynamic_sites")))

    @staticmethod
    def _source_root(rel: str, package: str) -> str:
        """Directory that holds the package tree: `android/guava/src/com/google/x/A.java` -> `android/guava/src`."""
        parent = rel.replace(os.sep, "/").rpartition("/")[0]
        tail = package.replace(".", "/")
        if tail and (parent == tail or parent.endswith("/" + tail)):
            return parent[: -len(tail)].rstrip("/")
        return parent

    def _java_ids(self, units: List[Dict[str, Any]]) -> Dict[Tuple[str, int], str]:
        """Node id per declaration: the plain name when unique, else package-qualified, else source-root-qualified.

        Two source trees can declare the same package (guava ships `guava/` and `android/guava/`), so a package alone
        does not always separate two classes."""
        decls = []
        for unit in units:
            for start, qname in unit["decls"]:
                fqn = f"{unit['package']}.{qname}" if unit["package"] else qname
                decls.append(((unit["rel"], start), unit, qname, fqn))
        names = collections.Counter(d[2] for d in decls)
        fqns = collections.Counter(d[3] for d in decls)
        ids: Dict[Tuple[str, int], str] = {}
        for key, unit, qname, fqn in decls:
            if names[qname] == 1:
                cid = qname
            elif fqns[fqn] == 1 and fqn != qname:
                cid = fqn
            else:
                cid = f"{self._source_root(unit['rel'], unit['package'])}::{fqn}"
            ids[key] = cid
            self._java_by_name.setdefault(qname, []).append(cid)
            self._java_by_fqn.setdefault(fqn, []).append(cid)
        self._bump("java_duplicate_names", sum(1 for n in names.values() if n > 1))
        return ids

    def _pick(self, cands: List[str], info: Dict[str, Any], ref: str) -> Optional[str]:
        """Choose among same-named candidates by source tree: longest shared path, then most similar depth."""
        if len(cands) == 1:
            return cands[0]
        mine = self._source_root(info["file"], info["package"]).split("/")

        def score(cid: str) -> Tuple[int, int]:
            other = self.java_classes[cid]
            theirs = self._source_root(other["file"], other["package"]).split("/")
            shared = 0
            for a, b in zip(mine, theirs):
                if a != b:
                    break
                shared += 1
            return shared, -abs(len(mine) - len(theirs))

        ranked = sorted(cands, key=score, reverse=True)
        if score(ranked[0]) != score(ranked[1]):
            return ranked[0]
        self._mark_ambiguous(info, ref)
        return None

    def _mark_ambiguous(self, info: Dict[str, Any], ref: str) -> None:
        self._java_ambiguous.add((info["file"], ref))
        node = self.symbol_table.get(info["name"])
        if node is not None:
            refs = node.setdefault("gaps", {}).setdefault("ambiguous_refs", [])
            if ref not in refs:
                refs.append(ref)

    def _resolve(self, info: Dict[str, Any], ref: Optional[str]) -> Optional[str]:
        """The class `ref` means inside `info`, in Java's lookup order; None for library or undecidable names."""
        if not ref:
            return None
        key = (info["name"], ref)
        if key not in self._java_resolved:
            self._java_resolved[key] = self._lookup(info, ref)
        return self._java_resolved[key]

    def _lookup(self, info: Dict[str, Any], ref: str) -> Optional[str]:
        # 1. A member of this class or an enclosing one, or another class in the same file.
        parts = info["qname"].split(".")
        scopes = [".".join(parts[:i] + [ref]) for i in range(len(parts), 0, -1)] + [ref]
        for qname in scopes:
            local = [c for c in self._java_by_name.get(qname, ()) if self.java_classes[c]["file"] == info["file"]]
            if local:
                return local[0]
        # 2. A single-type import decides the name, even when it points outside the project.
        static = {f"{cls}.{member}" for cls, member in info.get("static_imports", ())}
        for imp in info["imports"]:
            if imp.endswith("." + ref) and imp not in static:
                cands = self._java_by_fqn.get(imp)
                return self._pick(cands, info, ref) if cands else None
        # 3. The same package, then wildcard imports.
        same = self._java_by_fqn.get(f"{info['package']}.{ref}" if info["package"] else ref)
        if same:
            return self._pick(same, info, ref)
        wild = [c for imp in info["imports"] if imp.endswith(".*") for c in self._java_by_fqn.get(imp[:-1] + ref, ())]
        if wild:
            return self._pick(wild, info, ref)
        # 4. Otherwise only a name that is unique in the project (e.g. an inherited member type).
        named = self._java_by_name.get(ref, [])
        if len(named) > 1:
            self._mark_ambiguous(info, ref)
        return named[0] if len(named) == 1 else None

    def _type_edge(self, frm: str, info: Dict[str, Any], ref: str, typ: str) -> None:
        target = self._resolve(info, ref)
        if target:
            self._add_edge(frm, target, typ, info["file"])

    def _index_java_units(self, units: List[Dict[str, Any]]) -> None:
        ids = self._java_ids(units)
        for unit in units:
            src, rel = unit["src"], unit["rel"]
            for cls, qname in self._iter_classes(self._java_tree(rel, src), src):
                name = ids[(rel, cls.start_byte)]
                body = cls.child_by_field_name("body")
                if cls.type == "annotation_type_declaration":
                    self._bump("java_annotation_types")
                anns = self._annotations(cls, src)
                base = next((self._annotation_path(n, src) for a, n in anns if a == "RequestMapping"), "")
                info: Dict[str, Any] = {
                    "name": name,
                    "qname": qname,
                    "file": rel,
                    "start": cls.start_byte,
                    "src": src,
                    "package": unit.get("package", ""),
                    "imports": unit.get("imports", []),
                    "static_imports": unit.get("static_imports", []),
                    "annotations": [a for a, _ in anns],
                    "fields": {},
                    "field_injected": set(),
                    "methods": set(),
                    "supers": [],
                }
                self.java_classes[name] = info
                self.symbol_table[name] = {
                    "file": rel,
                    "line": cls.start_point[0] + 1,
                    "type": "class",
                    "package": unit.get("package", ""),
                    "imports": unit.get("imports", []),
                    "annotations": info["annotations"],
                }
                gaps: Dict[str, Any] = {}
                if unit.get("dynamic_sites"):
                    gaps["dynamic_sites"] = unit["dynamic_sites"]
                if unit.get("has_error"):
                    gaps["parse_error"] = True
                if gaps:
                    self.symbol_table[name]["gaps"] = gaps
                for header in cls.children:
                    if header.type in ("superclass", "super_interfaces", "extends_interfaces"):
                        for t in self._direct_types(header):
                            names = self._type_names(t, src)
                            if names:
                                info["supers"].append(names[0])
                if body is None:
                    continue
                for member in body.children:
                    if member.type == "method_declaration":
                        self._index_method(info, member, base)
                    elif member.type == "constructor_declaration":
                        self.symbol_table.setdefault(
                            f"{name}.<init>",
                            {"file": rel, "line": member.start_point[0] + 1, "type": "constructor"},
                        )
                    elif member.type == "field_declaration":
                        type_node = member.child_by_field_name("type")
                        names = self._type_names(type_node, src) if type_node is not None else []
                        injected = any(a in self._INJECT_ANNOTATIONS for a, _ in self._annotations(member, src))
                        for decl in (c for c in member.children if c.type == "variable_declarator"):
                            fname = decl.child_by_field_name("name")
                            if fname is not None and names:
                                info["fields"][self._txt(fname, src)] = names[0]
                                if injected:
                                    info["field_injected"].add(self._txt(fname, src))

    def _index_method(self, info: Dict[str, Any], member: Any, base: str) -> None:
        src = info["src"]
        name_node = member.child_by_field_name("name")
        if name_node is None:
            return
        mname = self._txt(name_node, src)
        mid = f"{info['name']}.{mname}"
        info["methods"].add(mname)
        if mid in self.symbol_table:
            self.symbol_table[mid]["overloads"] = self.symbol_table[mid].get("overloads", 1) + 1
            return
        anns = self._annotations(member, src)

        # Extract return type
        ret_node = member.child_by_field_name("type")
        ret_type = " ".join(self._txt(ret_node, src).split()) if ret_node is not None else "void"

        # Extract parameters: ["Long id", "DataDTO data", ...]
        params_node = member.child_by_field_name("parameters")
        params_list = []
        if params_node is not None:
            for p in params_node.children:
                if p.type in ("formal_parameter", "spread_parameter"):
                    ptype = p.child_by_field_name("type")
                    pname = p.child_by_field_name("name")
                    if ptype is not None:
                        t_str = " ".join(self._txt(ptype, src).split())
                        n_str = self._txt(pname, src).strip() if pname is not None else ""
                        params_list.append(f"{t_str} {n_str}".strip())

        node: Dict[str, Any] = {
            "file": info["file"],
            "line": member.start_point[0] + 1,
            "type": "method",
            "annotations": [a for a, _ in anns],
            "return_type": ret_type,
            "parameters": params_list,
        }
        for a, ann in anns:
            verb = self._MAPPING_VERBS.get(a)
            if verb:
                sub = self._annotation_path(ann, src)
                path = base.rstrip("/") + ("/" + sub.lstrip("/") if sub else "")
                node["route"] = f"{verb} {path or '/'}"
                break
        self.symbol_table[mid] = node

    def _add_edge(self, frm: str, to: str, typ: str, rel: str) -> None:
        key = (frm, to, typ)
        if key in self._edge_keys or to not in self.symbol_table:
            return
        if typ == "uses-type" and frm.rsplit(".", 1)[0] == to:
            return
        self._edge_keys.add(key)
        self.edges.append({"from": frm, "to": to, "type": typ, "file": rel})

    def _link_java_units(self, units: List[Dict[str, Any]]) -> None:
        by_file: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
        for info in self.java_classes.values():
            by_file[info["file"]].append(info)
        for infos in by_file.values():
            src = infos[0]["src"]
            tree = self._java_tree(infos[0]["file"], src)
            decls = {cls.start_byte: cls for cls, _ in self._iter_classes(tree, src)}
            for info in infos:
                info["node"] = decls[info["start"]]
                try:
                    self._link_class(info)
                except RecursionError:  # one pathological expression must not lose the whole repository
                    self.skipped_files.append(info["file"])
                del info["node"]
        self._bump("java_ambiguous_references", len(self._java_ambiguous))

    def _link_class(self, info: Dict[str, Any]) -> None:
        cls, src, name = info["node"], info["src"], info["name"]
        # Header: direct supertypes inherit; their type arguments are type uses.
        for header in cls.children:
            if header.type in ("superclass", "super_interfaces", "extends_interfaces"):
                for t in self._direct_types(header):
                    names = self._type_names(t, src)
                    if names:
                        self._type_edge(name, info, names[0], "inherits")
                    for extra in names[1:]:
                        self._type_edge(name, info, extra, "uses-type")
        for ann_name, _ in self._annotations(cls, src):
            self._type_edge(name, info, ann_name, "annotated-by")
        body = cls.child_by_field_name("body")
        if body is None:
            return
        stereotype = bool(self._STEREOTYPES & set(info["annotations"]))
        for member in body.children:
            if member.type == "field_declaration":
                type_node = member.child_by_field_name("type")
                names = self._type_names(type_node, src) if type_node is not None else []
                injected = any(a in self._INJECT_ANNOTATIONS for a, _ in self._annotations(member, src))
                for ann_name, _ in self._annotations(member, src):
                    self._type_edge(name, info, ann_name, "annotated-by")
                for i, tname in enumerate(names):
                    kind = "injects" if (i == 0 and injected) else "uses-type"
                    self._type_edge(name, info, tname, kind)
            elif member.type == "constructor_declaration":
                self._link_method(info, member, f"{name}.<init>", ctor_injects=stereotype)
            elif member.type == "method_declaration":
                name_node = member.child_by_field_name("name")
                if name_node is not None:
                    self._link_method(info, member, f"{name}.{self._txt(name_node, src)}")

    def _link_method(self, info: Dict[str, Any], member: Any, mid: str, ctor_injects: bool = False) -> None:
        src, rel, cname = info["src"], info["file"], info["name"]
        param_locals: Dict[str, str] = {}

        for ann_name, _ in self._annotations(member, src):
            self._type_edge(mid, info, ann_name, "annotated-by")
        ret = member.child_by_field_name("type")
        if ret is not None:
            for t in self._type_names(ret, src):
                self._type_edge(mid, info, t, "uses-type")

        params = member.child_by_field_name("parameters")
        for p in params.children if params is not None else []:
            if p.type not in ("formal_parameter", "spread_parameter"):
                continue
            for ann_name, _ in self._annotations(p, src):
                self._type_edge(mid, info, ann_name, "annotated-by")
            ptype, pname = p.child_by_field_name("type"), p.child_by_field_name("name")
            names = self._type_names(ptype, src) if ptype is not None else []
            if pname is not None and names:
                param_locals[self._txt(pname, src)] = names[0]
            for i, t in enumerate(names):
                if ctor_injects and i == 0:
                    self._type_edge(cname, info, t, "injects")
                else:
                    self._type_edge(mid, info, t, "uses-type")

        for c in member.children:
            if c.type == "throws":
                for t in self._type_names(c, src):
                    self._type_edge(mid, info, t, "throws")

        body = member.child_by_field_name("body")
        if body is None:
            return

        # Pre-order DFS with block-level lexical scoping: ancestor locals flow down to child blocks,
        # while declarations inside sibling blocks never leak or overwrite across blocks.
        def walk_scope(node: Any, scope_locals: Dict[str, str]) -> None:
            if node.type == "local_variable_declaration":
                ltype = node.child_by_field_name("type")
                names = self._type_names(ltype, src) if ltype is not None else []
                for decl in (c for c in node.children if c.type == "variable_declarator"):
                    dname, value = decl.child_by_field_name("name"), decl.child_by_field_name("value")
                    if dname is None:
                        continue
                    if (ltype is not None and self._txt(ltype, src) == "var") and value is not None:
                        if value.type == "object_creation_expression":
                            vt = value.child_by_field_name("type")
                            names = self._type_names(vt, src) if vt is not None else []
                    if names:
                        scope_locals[self._txt(dname, src)] = names[0]
                for t in names:
                    self._type_edge(mid, info, t, "uses-type")
            elif node.type == "object_creation_expression":
                ctype = node.child_by_field_name("type")
                for t in self._type_names(ctype, src) if ctype is not None else []:
                    self._type_edge(mid, info, t, "uses-type")
            elif node.type == "throw_statement":
                for c in node.children:
                    if c.type == "object_creation_expression":
                        ctype = c.child_by_field_name("type")
                        for t in self._type_names(ctype, src)[:1] if ctype is not None else []:
                            self._type_edge(mid, info, t, "throws")
            elif node.type == "method_invocation":
                self._link_call(info, node, mid, scope_locals)
            elif node.type == "method_reference":
                kids = node.children
                if len(kids) >= 3 and kids[0].type == "this":
                    target = self._find_method(cname, self._txt(kids[-1], src))
                    if target:
                        self._add_edge(mid, target, "calls", rel)

            for child in node.children:
                if child.type in ("block", "lambda_expression"):
                    walk_scope(child, dict(scope_locals))
                elif child.type not in self._CLASS_NODES:
                    walk_scope(child, scope_locals)

        walk_scope(body, dict(param_locals))

    def _receiver_class(self, obj: Any, info: Dict[str, Any], locals_: Dict[str, str]) -> Optional[str]:
        src = info["src"]
        if obj is None or obj.type == "this":
            return info["name"]
        if obj.type == "super":
            return self._resolve(info, info["supers"][0]) if info["supers"] else None
        if obj.type == "identifier":
            ident = self._txt(obj, src)
            if ident in locals_:
                return self._resolve(info, locals_[ident])
            if ident in info["fields"]:
                return self._resolve(info, info["fields"][ident])
            return self._resolve(info, ident)  # static call on a project class
        if obj.type == "field_access":
            inner, field = obj.child_by_field_name("object"), obj.child_by_field_name("field")
            if inner is not None and inner.type == "this" and field is not None:
                return self._resolve(info, info["fields"].get(self._txt(field, src)))
            return None
        if obj.type == "object_creation_expression":
            ctype = obj.child_by_field_name("type")
            names = self._type_names(ctype, src) if ctype is not None else []
            return self._resolve(info, names[0]) if names else None
        return None

    def _find_method(self, cls_name: Optional[str], mname: str, seen: Optional[Set[str]] = None) -> Optional[str]:
        seen = seen if seen is not None else set()
        if cls_name in seen or cls_name not in self.java_classes:
            return None
        seen.add(cls_name)
        info = self.java_classes[cls_name]
        if mname in info["methods"]:
            return f"{cls_name}.{mname}"
        for sup in info["supers"]:
            found = self._find_method(self._resolve(info, sup), mname, seen)
            if found:
                return found
        return None

    def _static_import_target(self, info: Dict[str, Any], mname: str) -> Optional[str]:
        """Resolve `mname()` through `import static ...Class.mname;` or a wildcard `Class.*` import.

        Only classes declared in the repository resolve."""
        for cls_path, member in info.get("static_imports", ()):
            if member not in (mname, "*"):
                continue
            cands = self._java_by_fqn.get(cls_path)
            found = self._find_method(self._pick(cands, info, cls_path), mname) if cands else None
            if found:
                return found
        return None

    def _link_call(self, info: Dict[str, Any], node: Any, mid: str, locals_: Dict[str, str]) -> None:
        src = info["src"]
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        obj = node.child_by_field_name("object")
        mname = self._txt(name_node, src)
        target_cls = self._receiver_class(obj, info, locals_)
        target = self._find_method(target_cls, mname) if target_cls else None
        if target is None and obj is None:
            # A receiver-less call that is not a method of this class or its supertypes may come from a static import.
            target = self._static_import_target(info, mname)
            if target:
                self._bump("java_static_import_calls")
        if target:
            self.stats["calls_resolved"] += 1
            self._add_edge(mid, target, "calls", info["file"])
        else:
            self.stats["calls_unresolved"] += 1

    def _parse_hcl(self, path: Path) -> Optional[Dict[str, Any]]:
        parser = self.parsers.get("hcl")
        if not parser:
            return None
        try:
            content = path.read_bytes()
        except IOError:
            return None
        return {
            "rel": str(path.relative_to(self.root_dir)),
            "src": content,
            "root": parser.parse(content).root_node,
        }

    def _index_hcl(self, unit: Dict[str, Any]) -> None:
        # HCL definitions are usually blocks (resource, variable, module, etc.)
        content = unit["src"]
        query = self._query("hcl", "(block (identifier) @type (string_lit) @name)")
        for node, tag in query.captures(unit["root"]):
            try:
                name = content[node.start_byte : node.end_byte].decode("utf-8").strip('"')
                self.symbol_table[name] = {
                    "file": unit["rel"],
                    "line": node.start_point[0] + 1,
                    "type": tag,
                }
            except UnicodeDecodeError:
                continue
        self._index_hcl_typed(unit)

    # --- Terraform: typed resource/module/provider/variable nodes -------------------------------
    # Literal attribute values only; interpolations (var.x, local.y) are left unresolved on purpose.
    _TF_ATTR = r'(?m)^[ \t]*{key}[ \t]*=[ \t]*"([^"$]*)"[ \t\r]*$'

    @staticmethod
    def _iter_hcl_blocks(root: Any):
        stack = [root]
        while stack:
            n = stack.pop()
            if n.type == "block":
                yield n
            stack.extend(reversed(n.children))

    def _tf_attr(self, text: str, key: str) -> Optional[str]:
        m = re.search(self._TF_ATTR.format(key=re.escape(key)), text)
        return m.group(1) if m else None

    def _index_hcl_typed(self, unit: Dict[str, Any]) -> None:
        content, rel = unit["src"], unit["rel"]
        for blk in self._iter_hcl_blocks(unit["root"]):
            try:
                text = content[blk.start_byte : blk.end_byte].decode("utf-8")
            except UnicodeDecodeError:
                continue
            kind = next((c for c in blk.children if c.type == "identifier"), None)
            if kind is None:
                continue
            kname = content[kind.start_byte : kind.end_byte].decode("utf-8")
            labels = [
                content[c.start_byte : c.end_byte].decode("utf-8").strip('"')
                for c in blk.children
                if c.type == "string_lit"
            ]
            line = blk.start_point[0] + 1
            if kname == "resource" and len(labels) == 2:
                rtype, rname = labels
                node: Dict[str, Any] = {
                    "file": rel,
                    "line": line,
                    "type": "tf_resource",
                    "tf_type": rtype,
                    "tf_name": rname,
                }
                meta = re.search(r"metadata[ \t]*\{(.*?)\n[ \t]*\}", text, re.DOTALL)
                scope = meta.group(1) if meta else text
                for key in ("name", "namespace", "chart", "repository", "version"):
                    val = self._tf_attr(scope if key in ("name", "namespace") and meta else text, key)
                    if val:
                        node[f"k8s_{key}" if rtype.startswith("kubernetes_") else key] = val
                self.symbol_table[f"resource:{rtype}/{rname}"] = node
            elif kname == "module" and labels:
                node = {"file": rel, "line": line, "type": "tf_module", "tf_name": labels[0]}
                for key in ("source", "version"):
                    val = self._tf_attr(text, key)
                    if val:
                        node[key] = val
                self.symbol_table[f"module:{labels[0]}"] = node
            elif kname == "provider" and labels:
                alias = self._tf_attr(text, "alias")
                pid = f"provider:{labels[0]}" + (f".{alias}" if alias else "")
                self.symbol_table[pid] = {"file": rel, "line": line, "type": "tf_provider", "alias": alias or ""}
            elif kname == "variable" and labels:
                node = {"file": rel, "line": line, "type": "tf_variable"}
                default = self._tf_attr(text, "default")
                if default is not None and not is_secret(labels[0], default):
                    node["default"] = default
                self.symbol_table[f"variable:{labels[0]}"] = node

    def _index_tf_modules_json(self, hcl_files: List[Path]) -> None:
        """Resolved module sources/versions from `terraform init` (.terraform/modules/modules.json), when present."""
        seen = set()
        for d in {p.parent for p in hcl_files} | {self.root_dir}:
            mj = d / ".terraform" / "modules" / "modules.json"
            if mj in seen or not readable(mj, self.root_dir):
                continue
            seen.add(mj)
            try:
                mods = json.loads(mj.read_text(encoding="utf-8")).get("Modules", [])
            except (OSError, ValueError):
                continue
            for m in mods:
                key = m.get("Key")
                if not key:
                    continue
                node = self.symbol_table.get(f"module:{key}")
                if node is None:
                    continue
                node["resolved_source"] = m.get("Source", "")
                if m.get("Version"):
                    node["resolved_version"] = m["Version"]

    def _index_tfvars(self, path: Path) -> None:
        """vars/*.tfvars bindings: one tf_var_binding node per key with a binds-variable edge; secrets redacted."""
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            return
        rel = str(path.relative_to(self.root_dir))
        for i, raw in enumerate(lines, 1):
            m = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*(.+?)\s*$", raw)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if is_secret(key, val):
                val = "[REDACTED]"
            nid = f"tfvar:{rel}:{key}"
            self.symbol_table[nid] = {"file": rel, "line": i, "type": "tf_var_binding", "value": val[:200]}
            self._add_edge(nid, f"variable:{key}", "binds-variable", rel)

    def _link_hcl(self, unit: Dict[str, Any]) -> None:
        content = unit["src"]
        query = self._query("hcl", "(variable_expr (identifier) @usage)")
        for node, tag in query.captures(unit["root"]):
            try:
                name = content[node.start_byte : node.end_byte].decode("utf-8")
                if name in self.symbol_table:
                    self.edges.append({"from": unit["rel"], "to": name, "type": "uses"})
            except UnicodeDecodeError:
                continue


def render_catalog(graph: Dict[str, Any]) -> Dict[str, str]:
    """Per-file structural catalog for Java classes: annotations, injections, routes, resolved calls.

    Built from the graph so code_map.md and relationship_graph.json cannot disagree.
    """
    nodes, edges = graph["nodes"], graph["edges"]
    by_from: Dict[str, List[Dict[str, str]]] = {}
    for e in edges:
        by_from.setdefault(e["from"], []).append(e)

    def targets(frm: str, typ: str) -> List[str]:
        return sorted({e["to"] for e in by_from.get(frm, []) if e["type"] == typ})

    per_file: Dict[str, List[str]] = {}
    for cname, node in nodes.items():
        if node.get("type") != "class":
            continue
        anns = " ".join("@" + a for a in node.get("annotations", []))
        lines = [f"{cname} {anns}".rstrip()]
        if node.get("package"):
            lines.append(f"  package: {node['package']}")
        if node.get("imports"):
            # Compact view of top imports
            lines.append("  imports: " + ", ".join(node["imports"]))
        if targets(cname, "inherits"):
            lines.append("  extends: " + ", ".join(targets(cname, "inherits")))
        if targets(cname, "injects"):
            lines.append("  injects: " + ", ".join(targets(cname, "injects")))
        methods = sorted(
            (k for k, v in nodes.items() if v.get("type") == "method" and k.startswith(cname + ".")),
            key=lambda k: nodes[k]["line"],
        )
        plain: List[str] = []
        for mid in methods:
            mnode = nodes[mid]
            mname = mid.split(".", 1)[1]
            calls, throws = targets(mid, "calls"), targets(mid, "throws")
            route = mnode.get("route")
            params = mnode.get("parameters", [])
            ret = mnode.get("return_type", "void")
            sig = f"{mname}({', '.join(params)}) -> {ret}"

            if not (route or calls or throws):
                plain.append(sig)
                continue
            line = f"  {route + ' ' if route else ''}{sig}"
            if calls:
                line += " [calls: " + ", ".join(calls) + "]"
            if throws:
                line += " | throws: " + ", ".join(throws)
            lines.append(line)
        if plain:
            lines.append("  methods: " + "; ".join(plain))
        per_file.setdefault(node["file"], []).extend(lines)
    return {f: "\n".join(ls) for f, ls in per_file.items()}


_COMMUNITY_MAP = {
    "class": 1,
    "method": 2,
    "constructor": 2,
    "go-package": 3,
    "py-module": 4,
    "type": 5,
    "name": 5,
}


def parse_git_log_cochanges(
    log_text: str,
    min_cochanges: int = 2,
    min_jaccard: float = 0.3,
    max_files_per_commit: int = 20,
    nodes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Parse git log --name-only --pretty=format:COMMIT:%H output into INFERRED co-changes-with edges."""
    commits: List[Set[str]] = []
    cur: Set[str] = set()
    for raw in log_text.splitlines():
        line = raw.strip()
        if line.startswith("COMMIT:"):
            if 1 < len(cur) <= max_files_per_commit:
                commits.append(cur)
            cur = set()
        elif line:
            cur.add(line)
    if 1 < len(cur) <= max_files_per_commit:
        commits.append(cur)

    file_counts: Dict[str, int] = {}
    pair_counts: Dict[Tuple[str, str], int] = {}
    for cset in commits:
        ordered = sorted(cset)
        for f in ordered:
            file_counts[f] = file_counts.get(f, 0) + 1
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                pair = (ordered[i], ordered[j])
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

    file_to_nid: Dict[str, str] = {}
    if nodes is not None:
        for nid, info in sorted(nodes.items(), key=lambda kv: (kv[1].get("line", 1), kv[0])):
            fpath = info.get("file", "")
            if fpath and fpath not in file_to_nid:
                file_to_nid[fpath] = nid

    def _resolve_node(fpath: str) -> str:
        if nodes is None:
            return fpath
        if fpath in file_to_nid:
            return file_to_nid[fpath]
        if fpath not in nodes:
            nodes[fpath] = {"file": fpath, "line": 1, "type": "file"}
        file_to_nid[fpath] = fpath
        return fpath

    edges: List[Dict[str, Any]] = []
    for (fa, fb), shared in sorted(pair_counts.items()):
        if shared < min_cochanges:
            continue
        union = file_counts[fa] + file_counts[fb] - shared
        jaccard = round(shared / union, 2) if union > 0 else 0.0
        if jaccard >= min_jaccard:
            src_id = _resolve_node(fa)
            dst_id = _resolve_node(fb)
            edges.append(
                {
                    "from": src_id,
                    "to": dst_id,
                    "type": "co-changes-with",
                    "file": fa,
                    "confidence": "INFERRED",
                    "confidence_score": jaccard,
                    "weight": float(shared),
                }
            )
    return edges


def mine_git_cochanges(
    repo_dir: str,
    max_commits: int = 200,
    min_cochanges: int = 2,
    min_jaccard: float = 0.3,
    nodes: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Run git log --name-only in repo_dir and return inferred co-change edges."""
    import subprocess

    res = subprocess.run(
        [*git_argv(repo_dir), "log", "--no-show-signature", f"-n{max_commits}", "--name-only",
         "--pretty=format:COMMIT:%H"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0 or not res.stdout:
        return []
    return parse_git_log_cochanges(res.stdout, min_cochanges=min_cochanges, min_jaccard=min_jaccard, nodes=nodes)


def find_cycles_postorder(nodes: Dict[str, Any], edges: List[Dict[str, Any]]) -> List[List[str]]:
    """Post-order DFS (Tarjan's SCC): child lowlinks flow up to parent after children finish."""
    adj: Dict[str, List[str]] = {n: [] for n in nodes}
    for e in edges:
        u, v = str(e.get("from", "")), str(e.get("to", ""))
        if u and v and u != v:
            adj.setdefault(u, []).append(v)
            adj.setdefault(v, [])

    index = 0
    indices: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    stack: List[str] = []
    on_stack: Set[str] = set()
    sccs: List[List[str]] = []

    def strongconnect(root: str) -> None:
        """Tarjan with an explicit stack: a long import chain must not overflow Python's recursion limit."""
        nonlocal index
        work = [(root, iter(sorted(adj.get(root, []))))]
        indices[root] = lowlink[root] = index
        index += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            u, children = work[-1]
            for v in children:
                if v not in indices:
                    indices[v] = lowlink[v] = index
                    index += 1
                    stack.append(v)
                    on_stack.add(v)
                    work.append((v, iter(sorted(adj.get(v, [])))))
                    break
                if v in on_stack:
                    lowlink[u] = min(lowlink[u], indices[v])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlink[parent] = min(lowlink[parent], lowlink[u])
                if lowlink[u] == indices[u]:
                    comp: List[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        comp.append(w)
                        if w == u:
                            break
                    if len(comp) > 1:
                        sccs.append(list(reversed(comp)))

    for n in sorted(adj):
        if n not in indices:
            strongconnect(n)
    return sccs


def detect_communities(nodes: Dict[str, Any], edges: List[Dict[str, Any]], max_iter: int = 15) -> Dict[str, int]:
    """Deterministic weighted label propagation clustering tightly coupled domain slices into subsystem IDs."""
    all_nodes = sorted(
        set(nodes.keys()) | {str(e.get("from", "")) for e in edges} | {str(e.get("to", "")) for e in edges} - {""}
    )
    labels: Dict[str, int] = {n: idx + 1 for idx, n in enumerate(all_nodes)}
    nbrs: Dict[str, Dict[str, float]] = {n: {} for n in all_nodes}
    for e in edges:
        u, v = str(e.get("from", "")), str(e.get("to", ""))
        if u and v and u != v:
            w = float(e.get("confidence_score", 1.0)) * float(e.get("weight", 1.0))
            nbrs[u][v] = nbrs[u].get(v, 0.0) + w
            nbrs[v][u] = nbrs[v].get(u, 0.0) + w

    for _ in range(max_iter):
        changed = False
        for u in all_nodes:
            if not nbrs[u]:
                continue
            scores: Dict[int, float] = {}
            for v, w in nbrs[u].items():
                lbl = labels[v]
                scores[lbl] = scores.get(lbl, 0.0) + w
            # Tie-break deterministically by smallest label integer
            best_lbl = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            if best_lbl != labels[u]:
                labels[u] = best_lbl
                changed = True
        if not changed:
            break
    return labels


def generate_graph_report(graph: Dict[str, Any]) -> str:
    """Emit a Graphify-style GRAPH_REPORT.md summarizing God nodes, communities, and Tarjan SCC cycles."""
    graph = clean_tree(graph)
    norm = from_graphify(graph)
    nodes, edges = norm.get("nodes", {}), norm.get("edges", [])
    degree: Dict[str, int] = {n: 0 for n in nodes}
    extracted_cnt, inferred_cnt = 0, 0
    edge_set: Set[Tuple[str, str]] = set()
    for e in edges:
        u, v = str(e.get("from", "")), str(e.get("to", ""))
        if u and v:
            edge_set.add((u, v))
        degree[u] = degree.get(u, 0) + 1
        degree[v] = degree.get(v, 0) + 1
        if e.get("confidence") == "INFERRED" or float(e.get("confidence_score", 1.0)) < 1.0:
            inferred_cnt += 1
        else:
            extracted_cnt += 1

    god_nodes = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    comms = detect_communities(nodes, edges)
    by_comm: Dict[int, List[str]] = {}
    for n, cid in comms.items():
        by_comm.setdefault(cid, []).append(n)
    cycles = find_cycles_postorder(nodes, edges)

    lines = [
        "# GRAPH_REPORT.md",
        "",
        "## 1. Graph Summary & Audit Trail",
        f"- **Nodes**: {len(nodes)}",
        f"- **Edges**: {len(edges)} (`EXTRACTED`: {extracted_cnt}, `INFERRED`: {inferred_cnt})",
        f"- **Subsystems (Communities)**: {len(by_comm)}",
        "",
        "## 2. Top Architectural Hubs (God Nodes)",
    ]
    for nid, deg in god_nodes:
        lines.append(f"- `{nid}` (degree: {deg}, file: `{nodes.get(nid, {}).get('file', '')}`)")
    lines.extend(["", "## 3. Subsystem Communities"])
    for cid, members in sorted(by_comm.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:10]:
        lines.append(
            f"- **Community {cid}** ({len(members)} nodes): {', '.join(f'`{m}`' for m in sorted(members)[:6])}"
        )
    lines.extend(["", "## 4. Circular Dependencies (Post-Order Tarjan SCC)"])
    if not cycles:
        lines.append("- None detected.")
    else:
        for cyc in cycles:
            is_simple_ring = all((cyc[i], cyc[(i + 1) % len(cyc)]) in edge_set for i in range(len(cyc)))
            if is_simple_ring:
                lines.append(f"- {' -> '.join(cyc)} -> {cyc[0]}")
            else:
                lines.append(f"- SCC ({len(cyc)} nodes): {', '.join(f'`{m}`' for m in cyc)}")
    return "\n".join(lines) + "\n"


def to_graphify(graph: Dict[str, Any], name: str = "code-map-ast-graph") -> Dict[str, Any]:
    """Convert a GraphBuilder relationship graph into standard Graphify node_link_data JSON."""
    raw_nodes = graph.get("nodes", {})
    raw_edges = graph.get("edges", [])

    degree: Dict[str, int] = {}
    for e in raw_edges:
        frm, to = str(e.get("from", "")), str(e.get("to", ""))
        degree[frm] = degree.get(frm, 0) + 1
        degree[to] = degree.get(to, 0) + 1

    topo_comms = detect_communities(raw_nodes, raw_edges)

    g_nodes: List[Dict[str, Any]] = []
    for nid, info in raw_nodes.items():
        ntype = info.get("type", "symbol")
        props = {k: v for k, v in info.items() if k not in ("file", "line", "type")}
        props["type"] = ntype
        props["line"] = info.get("line", 1)
        props["degree"] = degree.get(nid, 0)
        props["is_god_node"] = degree.get(nid, 0) >= 5
        g_nodes.append(
            {
                "id": nid,
                "label": f"{ntype}: {nid}",
                "file_type": ntype,
                "source_file": info.get("file", ""),
                "source_location": f"{info.get('file', '')}:{info.get('line', 1)}",
                "community": topo_comms.get(nid, _COMMUNITY_MAP.get(ntype, 6)),
                "_origin": "code_mapper_ast",
                "properties": props,
            }
        )

    g_links: List[Dict[str, Any]] = []
    for e in raw_edges:
        g_links.append(
            {
                "source": e["from"],
                "target": e["to"],
                "relation": e["type"],
                "file": e.get("file", ""),
                "_origin": "code_mapper_ast",
                "confidence": e.get("confidence", "EXTRACTED"),
                "confidence_score": float(e.get("confidence_score", 1.0)),
                "weight": float(e.get("weight", 1.0)),
            }
        )

    return {
        "directed": True,
        "multigraph": False,
        "graph": {
            "name": name,
            "source": "skill-code-map",
            "node_count": len(g_nodes),
            "edge_count": len(g_links),
            "stats": graph.get("stats", {}),
        },
        "nodes": g_nodes,
        "links": g_links,
        "hyperedges": [],
    }


def from_graphify(g_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Graphify node_link_data JSON into GraphBuilder/SemanticQuery {nodes: dict, edges: list}."""
    if isinstance(g_graph.get("nodes"), dict) and "edges" in g_graph:
        return g_graph
    nodes: Dict[str, Dict[str, Any]] = {}
    for n in g_graph.get("nodes", []):
        nid = n.get("id")
        if not nid:
            continue
        props = dict(n.get("properties") or {})
        sfile = n.get("source_file", "")
        if sfile.startswith("k8s://"):
            sfile = props.get("source_file", sfile)
        entry: Dict[str, Any] = {
            "file": sfile or props.get("file", ""),
            "line": props.get("line", 1),
            "type": props.get("type") or n.get("file_type", "symbol"),
        }
        for k, v in props.items():
            if k not in entry:
                entry[k] = v
        nodes[nid] = entry

    edges: List[Dict[str, Any]] = []
    for lnk in g_graph.get("links", g_graph.get("edges", [])):
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
                    "confidence": lnk.get("confidence", "EXTRACTED"),
                    "confidence_score": float(lnk.get("confidence_score", 1.0)),
                    "weight": float(lnk.get("weight", 1.0)),
                }
            )
    return {"nodes": nodes, "edges": edges, "stats": g_graph.get("graph", {}).get("stats", {})}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a semantic relationship graph.")
    parser.add_argument("dir", help="Directory to analyze")
    parser.add_argument("--output", default="relationship_graph.json", help="Output file")
    parser.add_argument("--format", choices=("codemap", "graphify"), default="codemap", help="Output schema format")
    parser.add_argument("--cochanges", action="store_true", help="Overlay git co-change coupling edges")
    parser.add_argument("--report", default=None, help="Optional path to write GRAPH_REPORT.md")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logger.error(f"Provided path is not a directory: {args.dir}")
        sys.exit(1)

    builder = GraphBuilder(args.dir)
    logger.info(f"Building graph for {args.dir}...")
    graph = builder.build_graph()
    if args.cochanges:
        graph["edges"].extend(mine_git_cochanges(args.dir, nodes=graph["nodes"]))
    out_data = to_graphify(graph) if args.format == "graphify" else graph

    try:
        write_atomic(args.output, json.JSONEncoder(indent=2).iterencode(out_data))
        if args.report:
            write_atomic(args.report, generate_graph_report(graph))
        logger.info(f"Graph built ({args.format}) with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.")
    except IOError as e:
        logger.error(f"Failed to write graph to {args.output}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
