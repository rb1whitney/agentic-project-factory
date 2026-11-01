#!/usr/bin/env python3
"""code_mapper writes artifacts outside the target repo by default."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".agent" / "skills" / "skill-code-map" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import code_mapper as cm  # noqa: E402


class ExternalCacheTests(unittest.TestCase):
    def test_root_is_stable_and_per_repo(self) -> None:
        with (
            tempfile.TemporaryDirectory() as home,
            tempfile.TemporaryDirectory() as a,
            tempfile.TemporaryDirectory() as b,
        ):
            os.environ["XDG_CACHE_HOME"] = home
            try:
                ra, ra2, rb = cm.external_cache_root(a), cm.external_cache_root(a), cm.external_cache_root(b)
            finally:
                del os.environ["XDG_CACHE_HOME"]
            self.assertEqual(ra, ra2)
            self.assertNotEqual(ra, rb)
            self.assertTrue(str(ra).startswith(home))

    def test_unwritable_cache_falls_back_to_tmp(self) -> None:
        os.environ["XDG_CACHE_HOME"] = "/proc/nonexistent-cache"
        try:
            root = cm.external_cache_root(tempfile.gettempdir())
        finally:
            del os.environ["XDG_CACHE_HOME"]
        self.assertTrue(str(root).startswith("/tmp/skill-code-map-"))

    def test_cli_leaves_repo_clean(self) -> None:
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as repo:
            (Path(repo) / "a.py").write_text("def f():\n    return 1\n")
            env = dict(os.environ, XDG_CACHE_HOME=home)
            res = subprocess.run(
                [sys.executable, str(SCRIPTS / "code_mapper.py"), repo], env=env, capture_output=True, text=True
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(sorted(p.name for p in Path(repo).iterdir()), ["a.py"])
            self.assertTrue(any(Path(home).rglob("code_map.md")))
            self.assertTrue(any(Path(home).rglob("relationship_graph.json")))


if __name__ == "__main__":
    unittest.main()
