import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from tree_sitter import Parser
from tree_sitter_languages import get_language

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


class GraphBuilder:
    def __init__(self, root_dir: str) -> None:
        self.root_dir: Path = Path(root_dir)
        self.symbol_table: Dict[str, Dict[str, Any]] = {}  # name -> {file, line, type}
        self.edges: List[Dict[str, str]] = []  # list of {from, to, type, file}
        self._queries: Dict[Tuple[str, str], Any] = {}
        self.java_classes: Dict[str, Dict[str, Any]] = {}  # simple class name -> parse info
        self._edge_keys: Set[Tuple[str, str, str]] = set()
        self.stats: Dict[str, int] = {"calls_resolved": 0, "calls_unresolved": 0}
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
        java_files = [p for p in files if p.suffix.lower() == ".java"]
        hcl_files = [p for p in files if p.suffix.lower() in (".tf", ".hcl")]

        files = [f for f in files if not SKIP_DIRS.intersection(f.relative_to(self.root_dir).parts[:-1])]
        self._build_go(files)
        self._build_python(files)

        # Pass 1: index all definitions (Java needs the full class set before linking).
        # Each file is parsed exactly once; the trees are reused by pass 2.
        java_units = [u for u in (self._parse_java(p) for p in java_files) if u]
        self._index_java_units(java_units)
        hcl_units = [u for u in (self._parse_hcl(p) for p in hcl_files) if u]
        for unit in hcl_units:
            self._index_hcl(unit)

        # Pass 2: link usages
        self._link_java_units(java_units)
        for unit in hcl_units:
            self._link_hcl(unit)

        # `throw new X()` is already a throws edge; drop the redundant uses-type twin.
        thrown = {(e["from"], e["to"]) for e in self.edges if e["type"] == "throws"}
        self.edges = [e for e in self.edges if not (e["type"] == "uses-type" and (e["from"], e["to"]) in thrown)]

        return {"nodes": self.symbol_table, "edges": self.edges, "stats": self.stats}

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

    _CLASS_NODES = ("class_declaration", "interface_declaration", "enum_declaration", "record_declaration")
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
            return None
        root = parser.parse(src).root_node
        pkg = ""
        imports = []
        for c in root.children:
            if c.type == "package_declaration":
                pkg = self._txt(c, src).replace("package", "").replace(";", "").strip()
            elif c.type == "import_declaration":
                imp = self._txt(c, src).replace("import", "").replace("static", "").replace(";", "").strip()
                if imp:
                    imports.append(imp)
        return {
            "rel": str(path.relative_to(self.root_dir)),
            "src": src,
            "root": root,
            "package": pkg,
            "imports": imports,
        }

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

    def _index_java_units(self, units: List[Dict[str, Any]]) -> None:
        for unit in units:
            src, rel = unit["src"], unit["rel"]
            for cls, name in self._iter_classes(unit["root"], src):
                body = cls.child_by_field_name("body")
                anns = self._annotations(cls, src)
                base = next((self._annotation_path(n, src) for a, n in anns if a == "RequestMapping"), "")
                info: Dict[str, Any] = {
                    "name": name,
                    "file": rel,
                    "node": cls,
                    "src": src,
                    "package": unit.get("package", ""),
                    "imports": unit.get("imports", []),
                    "annotations": [a for a, _ in anns],
                    "fields": {},
                    "field_injected": set(),
                    "methods": set(),
                    "supers": [],
                }
                if name in self.java_classes:
                    logger.debug(f"Duplicate simple class name {name}: {rel} shadows {self.java_classes[name]['file']}")
                self.java_classes[name] = info
                self.symbol_table[name] = {
                    "file": rel,
                    "line": cls.start_point[0] + 1,
                    "type": "class",
                    "package": unit.get("package", ""),
                    "imports": unit.get("imports", []),
                    "annotations": info["annotations"],
                }
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
        ret_type = self._txt(ret_node, src).strip() if ret_node is not None else "void"

        # Extract parameters: ["Long id", "DataDTO data", ...]
        params_node = member.child_by_field_name("parameters")
        params_list = []
        if params_node is not None:
            for p in params_node.children:
                if p.type in ("formal_parameter", "spread_parameter"):
                    ptype = p.child_by_field_name("type")
                    pname = p.child_by_field_name("name")
                    if ptype is not None:
                        t_str = self._txt(ptype, src).strip()
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
        for info in list(self.java_classes.values()):
            self._link_class(info)

    def _link_class(self, info: Dict[str, Any]) -> None:
        cls, src, rel, name = info["node"], info["src"], info["file"], info["name"]
        # Header: direct supertypes inherit; their type arguments are type uses.
        for header in cls.children:
            if header.type in ("superclass", "super_interfaces", "extends_interfaces"):
                for t in self._direct_types(header):
                    names = self._type_names(t, src)
                    if names:
                        self._add_edge(name, names[0], "inherits", rel)
                    for extra in names[1:]:
                        self._add_edge(name, extra, "uses-type", rel)
        body = cls.child_by_field_name("body")
        if body is None:
            return
        stereotype = bool(self._STEREOTYPES & set(info["annotations"]))
        for member in body.children:
            if member.type == "field_declaration":
                type_node = member.child_by_field_name("type")
                names = self._type_names(type_node, src) if type_node is not None else []
                injected = any(a in self._INJECT_ANNOTATIONS for a, _ in self._annotations(member, src))
                for i, tname in enumerate(names):
                    kind = "injects" if (i == 0 and injected) else "uses-type"
                    self._add_edge(name, tname, kind, rel)
            elif member.type == "constructor_declaration":
                self._link_method(info, member, f"{name}.<init>", ctor_injects=stereotype)
            elif member.type == "method_declaration":
                name_node = member.child_by_field_name("name")
                if name_node is not None:
                    self._link_method(info, member, f"{name}.{self._txt(name_node, src)}")

    def _link_method(self, info: Dict[str, Any], member: Any, mid: str, ctor_injects: bool = False) -> None:
        src, rel, cname = info["src"], info["file"], info["name"]
        param_locals: Dict[str, str] = {}

        ret = member.child_by_field_name("type")
        if ret is not None:
            for t in self._type_names(ret, src):
                self._add_edge(mid, t, "uses-type", rel)

        params = member.child_by_field_name("parameters")
        for p in params.children if params is not None else []:
            if p.type not in ("formal_parameter", "spread_parameter"):
                continue
            ptype, pname = p.child_by_field_name("type"), p.child_by_field_name("name")
            names = self._type_names(ptype, src) if ptype is not None else []
            if pname is not None and names:
                param_locals[self._txt(pname, src)] = names[0]
            for i, t in enumerate(names):
                if ctor_injects and i == 0:
                    self._add_edge(cname, t, "injects", rel)
                else:
                    self._add_edge(mid, t, "uses-type", rel)

        for c in member.children:
            if c.type == "throws":
                for t in self._type_names(c, src):
                    self._add_edge(mid, t, "throws", rel)

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
                    self._add_edge(mid, t, "uses-type", rel)
            elif node.type == "object_creation_expression":
                ctype = node.child_by_field_name("type")
                for t in self._type_names(ctype, src) if ctype is not None else []:
                    self._add_edge(mid, t, "uses-type", rel)
            elif node.type == "throw_statement":
                for c in node.children:
                    if c.type == "object_creation_expression":
                        ctype = c.child_by_field_name("type")
                        for t in self._type_names(ctype, src)[:1] if ctype is not None else []:
                            self._add_edge(mid, t, "throws", rel)
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
            return info["supers"][0] if info["supers"] else None
        if obj.type == "identifier":
            ident = self._txt(obj, src)
            if ident in locals_:
                return locals_[ident]
            if ident in info["fields"]:
                return info["fields"][ident]
            return ident if ident in self.java_classes else None  # static call on a project class
        if obj.type == "field_access":
            inner, field = obj.child_by_field_name("object"), obj.child_by_field_name("field")
            if inner is not None and inner.type == "this" and field is not None:
                return info["fields"].get(self._txt(field, src))
            return None
        if obj.type == "object_creation_expression":
            ctype = obj.child_by_field_name("type")
            names = self._type_names(ctype, src) if ctype is not None else []
            return names[0] if names else None
        return None

    def _find_method(self, cls_name: str, mname: str, seen: Optional[Set[str]] = None) -> Optional[str]:
        seen = seen if seen is not None else set()
        if cls_name in seen or cls_name not in self.java_classes:
            return None
        seen.add(cls_name)
        info = self.java_classes[cls_name]
        if mname in info["methods"]:
            return f"{cls_name}.{mname}"
        for sup in info["supers"]:
            found = self._find_method(sup, mname, seen)
            if found:
                return found
        return None

    def _link_call(self, info: Dict[str, Any], node: Any, mid: str, locals_: Dict[str, str]) -> None:
        src = info["src"]
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        target_cls = self._receiver_class(node.child_by_field_name("object"), info, locals_)
        target = self._find_method(target_cls, self._txt(name_node, src)) if target_cls else None
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
        ["git", "-C", str(repo_dir), "log", f"-n{max_commits}", "--name-only", "--pretty=format:COMMIT:%H"],
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

    def strongconnect(u: str) -> None:
        nonlocal index
        indices[u] = index
        lowlink[u] = index
        index += 1
        stack.append(u)
        on_stack.add(u)

        for v in sorted(adj.get(u, [])):
            if v not in indices:
                strongconnect(v)
                # Post-order aggregation: child v is finished, propagate lowlink[v] up to u
                lowlink[u] = min(lowlink[u], lowlink[v])
            elif v in on_stack:
                lowlink[u] = min(lowlink[u], indices[v])

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
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        if args.report:
            Path(args.report).write_text(generate_graph_report(graph), encoding="utf-8")
        logger.info(f"Graph built ({args.format}) with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges.")
    except IOError as e:
        logger.error(f"Failed to write graph to {args.output}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
