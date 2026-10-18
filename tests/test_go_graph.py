#!/usr/bin/env python3
"""Characterization tests for Go package-graph support in skill-code-map/scripts/graph_builder.py."""

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import graph_builder as gb  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


class GoGraphTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write(self.root, "go.mod", "module example.com/app\n\ngo 1.22\n")
        write(
            self.root,
            "cmd/app/main.go",
            (
                'package main\n\nimport (\n\t"fmt"\n\t"example.com/app/pkg/core"\n)\n\n'
                "func main() { fmt.Println(core.Run()) }\n"
            ),
        )
        write(
            self.root,
            "pkg/core/core.go",
            (
                'package core\n\nimport "example.com/app/pkg/util"\n\n'
                "type Runner interface{ Run() }\ntype impl struct{}\n\n"
                "func Run() int { return util.One() }\n"
            ),
        )
        write(self.root, "pkg/core/core_test.go", 'package core\n\nimport "example.com/app/cmd/app"\n')
        write(self.root, "pkg/util/util.go", "package util\n\nfunc One() int { return 1 }\n")
        write(self.root, "staging/src/example.org/lib/go.mod", "module example.org/lib\n")
        write(self.root, "staging/src/example.org/lib/lib.go", "package lib\n")
        write(self.root, "pkg/util/uses_lib.go", 'package util\n\nimport _ "example.org/lib"\n')
        write(self.root, "vendor/github.com/x/y/y.go", "package y\n")
        files = [p for p in self.root.rglob("*") if p.is_file()]
        self.graph = gb.GraphBuilder(str(self.root)).build_graph(files=files)

    def tearDown(self):
        self._tmp.cleanup()

    def test_package_nodes_keyed_by_dir(self):
        nodes = self.graph["nodes"]
        self.assertEqual(nodes["go:pkg/core"]["type"], "go-package")
        self.assertEqual(nodes["go:pkg/core"]["import_path"], "example.com/app/pkg/core")
        self.assertEqual(nodes["go:cmd/app"]["package"], "main")

    def test_in_repo_import_edges_only(self):
        edges = {(e["from"], e["to"]) for e in self.graph["edges"] if e["type"] == "imports"}
        self.assertIn(("go:cmd/app", "go:pkg/core"), edges)
        self.assertIn(("go:pkg/core", "go:pkg/util"), edges)
        self.assertFalse(any("fmt" in t for _, t in edges))

    def test_nested_module_resolves(self):
        edges = {(e["from"], e["to"]) for e in self.graph["edges"] if e["type"] == "imports"}
        self.assertIn(("go:pkg/util", "go:staging/src/example.org/lib"), edges)

    def test_test_files_and_vendor_excluded(self):
        edges = {(e["from"], e["to"]) for e in self.graph["edges"] if e["type"] == "imports"}
        self.assertNotIn(("go:pkg/core", "go:cmd/app"), edges)
        self.assertNotIn("go:vendor/github.com/x/y", self.graph["nodes"])

    def test_types_recorded(self):
        node = self.graph["nodes"]["go:pkg/core"]
        self.assertEqual(node["interfaces"], ["Runner"])
        self.assertEqual(node["structs"], ["impl"])


if __name__ == "__main__":
    unittest.main()
