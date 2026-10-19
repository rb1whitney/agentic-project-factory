#!/usr/bin/env python3
"""Deprecated alias for code_mapper.py.

The old analyzer walked .git and node_modules with rglob("*") and had no cache. code_mapper.py supersedes it
(cached, skip-aware, crash-tolerant), so this entry point only forwards. `--output` is ignored: artifacts go to
the code_mapper artifact directory (see SKILL.md)."""

import sys

import code_mapper


def main() -> None:
    print("repo_analyzer.py is deprecated; forwarding to code_mapper.py", file=sys.stderr)
    argv = [a for i, a in enumerate(sys.argv[1:]) if a != "--output" and sys.argv[i] != "--output"]
    sys.argv = ["code_mapper.py", *argv]
    code_mapper.main()


if __name__ == "__main__":
    main()
