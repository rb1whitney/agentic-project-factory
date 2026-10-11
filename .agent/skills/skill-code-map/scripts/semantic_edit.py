#!/usr/bin/env python3
"""
semantic_edit.py - Replace one named declaration in a source file, located by AST node, not by text.

  semantic_edit.py Foo.java method DataService.createData 'public DataDTO createData(...) { ... }'
  semantic_edit.py main.tf resource aws_vpc.main 'resource "aws_vpc" "main" { ... }' --dry-run

Safety contract: nothing is written unless exactly one declaration matches and the result still parses
cleanly. Ambiguous or missing symbols exit non-zero and leave the file untouched.

Types
  java: class | interface | enum | method | constructor | field   (name or Outer.Inner.member)
  hcl : block | <block type, e.g. resource, module, variable>      (name: last label, a.b labels, or type.a.b)
  yaml: key                                                         (dotted path, e.g. spec.replicas)
"""

import argparse
import difflib
import logging
import os
import sys
import tempfile
from typing import Callable, List, Optional, Tuple

from tree_sitter import Node, Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("semantic_edit")

EXTENSIONS = {"java": "java", "tf": "hcl", "hcl": "hcl", "yaml": "yaml", "yml": "yaml"}

JAVA_KINDS = {
    "class": "class_declaration",
    "interface": "interface_declaration",
    "enum": "enum_declaration",
    "method": "method_declaration",
    "constructor": "constructor_declaration",
    "field": "field_declaration",
}
JAVA_SCOPES = {"class_declaration", "interface_declaration", "enum_declaration"}


class EditError(Exception):
    pass


def _text(node: Optional[Node], src: bytes) -> str:
    return src[node.start_byte : node.end_byte].decode("utf-8", errors="replace") if node else ""


def _walk(node: Node):
    yield node
    for child in node.children:
        yield from _walk(child)


def _java_names(node: Node, src: bytes) -> List[str]:
    """Qualified names for a Java declaration: Outer.Inner.member (fields may declare several)."""
    if node.type == "field_declaration":
        simple = [_text(d.child_by_field_name("name"), src) for d in node.children if d.type == "variable_declarator"]
    else:
        simple = [_text(node.child_by_field_name("name"), src)]
    scopes: List[str] = []
    parent = node.parent
    while parent is not None:
        if parent.type in JAVA_SCOPES:
            scopes.append(_text(parent.child_by_field_name("name"), src))
        parent = parent.parent
    prefix = ".".join(reversed(scopes))
    # Answer to the bare name too; an ambiguous bare name is rejected by plan_edit, never guessed.
    return [n for name in simple if name for n in ((f"{prefix}.{name}", name) if prefix else (name,))]


def _hcl_names(node: Node, src: bytes) -> List[str]:
    kind = _text(next((c for c in node.children if c.type == "identifier"), None), src)
    labels = [
        _text(next((t for t in c.children if t.type == "template_literal"), None), src)
        for c in node.children
        if c.type == "string_lit"
    ]
    if not labels:
        return [kind]
    return [labels[-1], ".".join(labels), f"{kind}.{'.'.join(labels)}"]


def _yaml_names(node: Node, src: bytes) -> List[str]:
    keys: List[str] = []
    cur: Optional[Node] = node
    while cur is not None:
        if cur.type == "block_mapping_pair":
            keys.append(_text(cur.child_by_field_name("key"), src).strip())
        cur = cur.parent
    return [".".join(reversed(keys))]


def candidates(lang: str, symbol_type: str, root: Node, src: bytes) -> List[Tuple[Node, List[str]]]:
    """Every declaration of the requested type with the names it answers to."""
    if lang == "java":
        node_type = JAVA_KINDS.get(symbol_type)
        if node_type is None:
            raise EditError(f"java type must be one of {sorted(JAVA_KINDS)}, got '{symbol_type}'")
        names: Callable[[Node, bytes], List[str]] = _java_names

        def match(n: Node) -> bool:
            return n.type == node_type
    elif lang == "hcl":
        names = _hcl_names

        def match(n: Node) -> bool:
            if n.type != "block":
                return False
            kind = _text(next((c for c in n.children if c.type == "identifier"), None), src)
            return symbol_type in ("block", kind)
    elif lang == "yaml":
        if symbol_type != "key":
            raise EditError("yaml type must be 'key'")
        names = _yaml_names

        def match(n: Node) -> bool:
            return n.type == "block_mapping_pair"
    else:
        raise EditError(f"unsupported language: {lang}")
    return [(n, names(n, src)) for n in _walk(root) if match(n)]


def _parse(lang: str, src: bytes):
    parser = Parser()
    parser.set_language(get_language(lang))
    return parser.parse(src)


def plan_edit(path: str, symbol_type: str, symbol_name: str, new_content: str) -> Tuple[str, str]:
    """Return (old_source, new_source) or raise EditError. Performs no writes."""
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    lang = EXTENSIONS.get(ext)
    if lang is None:
        raise EditError(f"unsupported file extension: .{ext}")
    with open(path, "r", encoding="utf-8") as f:
        old = f.read()
    src = old.encode("utf-8")
    tree = _parse(lang, src)

    hits = [n for n, names in candidates(lang, symbol_type, tree.root_node, src) if symbol_name in names]
    if not hits:
        raise EditError(f"no {symbol_type} named '{symbol_name}' in {path}")
    if len(hits) > 1:
        where = ", ".join(f"line {n.start_point[0] + 1}" for n in hits)
        raise EditError(f"'{symbol_name}' is ambiguous ({len(hits)} matches: {where}); qualify the name")

    target = hits[0]
    new_src = src[: target.start_byte] + new_content.encode("utf-8") + src[target.end_byte :]
    if _parse(lang, new_src).root_node.has_error and not tree.root_node.has_error:
        raise EditError("replacement does not parse; file left unchanged")
    return old, new_src.decode("utf-8")


def apply_edit(path: str, new_source: str) -> None:
    """Atomic write: temp file in the same directory, then rename."""
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".semantic_edit.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(new_source)
        os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def semantic_replace(path: str, symbol_type: str, symbol_name: str, new_content: str, dry_run: bool = False) -> bool:
    try:
        old, new = plan_edit(path, symbol_type, symbol_name, new_content)
    except (EditError, OSError) as e:
        logger.error(str(e))
        return False
    if dry_run:
        sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "before", "after"))
        return True
    apply_edit(path, new)
    logger.info(f"Replaced {symbol_type} '{symbol_name}' in {path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Replace one named declaration by AST node.")
    parser.add_argument("file", help="File to edit")
    parser.add_argument("type", help="Declaration type (see module docstring)")
    parser.add_argument("name", help="Declaration name; qualify with Outer.member when ambiguous")
    parser.add_argument("content", help="Full replacement text for the declaration")
    parser.add_argument("--dry-run", action="store_true", help="Print a diff instead of writing")
    args = parser.parse_args()
    return 0 if semantic_replace(args.file, args.type, args.name, args.content, args.dry_run) else 1


if __name__ == "__main__":
    sys.exit(main())
