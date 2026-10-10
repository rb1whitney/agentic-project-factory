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
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "target", "build", "dist", "__pycache__", ".ast_cache", "skills"}


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


    def _iter_classes(self, root: Any):
        stack = [root]
        while stack:
            node = stack.pop()
            if node.type in self._CLASS_NODES:
                yield node
            stack.extend(reversed(node.children))

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
            for cls in self._iter_classes(unit["root"]):
                name_node = cls.child_by_field_name("name")
                body = cls.child_by_field_name("body")
                if name_node is None:
                    continue
                name = self._txt(name_node, src)
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
        if typ == "uses-type" and frm.split(".")[0] == to:
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
        locals_: Dict[str, str] = {}

        ret = member.child_by_field_name("type")
        if ret is not None:
            for t in self._type_names(ret, src):
                self._add_edge(mid, t, "uses-type", rel)

        params = member.child_by_field_name("parameters")
        for p in (params.children if params is not None else []):
            if p.type not in ("formal_parameter", "spread_parameter"):
                continue
            ptype, pname = p.child_by_field_name("type"), p.child_by_field_name("name")
            names = self._type_names(ptype, src) if ptype is not None else []
            if pname is not None and names:
                locals_[self._txt(pname, src)] = names[0]
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

        nodes: List[Any] = []
        stack = [body]
        while stack:
            n = stack.pop()
            nodes.append(n)
            stack.extend(reversed(n.children))

        # Locals first so invocation order in the body does not matter.
        for n in nodes:
            if n.type != "local_variable_declaration":
                continue
            ltype = n.child_by_field_name("type")
            names = self._type_names(ltype, src) if ltype is not None else []
            for decl in (c for c in n.children if c.type == "variable_declarator"):
                dname, value = decl.child_by_field_name("name"), decl.child_by_field_name("value")
                if dname is None:
                    continue
                if (ltype is not None and self._txt(ltype, src) == "var") and value is not None:
                    if value.type == "object_creation_expression":
                        vt = value.child_by_field_name("type")
                        names = self._type_names(vt, src) if vt is not None else []
                if names:
                    locals_[self._txt(dname, src)] = names[0]
            for t in names:
                self._add_edge(mid, t, "uses-type", rel)

        for n in nodes:
            if n.type == "object_creation_expression":
                ctype = n.child_by_field_name("type")
                for t in (self._type_names(ctype, src) if ctype is not None else []):
                    self._add_edge(mid, t, "uses-type", rel)
            elif n.type == "throw_statement":
                for c in n.children:
                    if c.type == "object_creation_expression":
                        ctype = c.child_by_field_name("type")
                        for t in (self._type_names(ctype, src)[:1] if ctype is not None else []):
                            self._add_edge(mid, t, "throws", rel)
            elif n.type == "method_invocation":
                self._link_call(info, n, mid, locals_)
            elif n.type == "method_reference":
                kids = n.children
                if len(kids) >= 3 and kids[0].type == "this":
                    target = self._find_method(cname, self._txt(kids[-1], src))
                    if target:
                        self._add_edge(mid, target, "calls", rel)

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
