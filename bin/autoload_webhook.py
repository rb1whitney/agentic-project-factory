#!/usr/bin/env python3
"""
autoload_webhook.py - Lifecycle hook / adapter webhook for Antigravity, Claude, and Codex.
Triggered on session start or pre-invocation to:
1. Ensure standard metadata index is compiled (.agent/metadata.json).
2. Ensure canonical multi-adapter agents in .agent/agents/*.yaml are hydrated to vendor formats
   (.claude/agents, .agents).
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)
    venv_py = repo_root / ".venv" / "bin" / "python"
    py_bin = str(venv_py) if venv_py.is_file() else sys.executable

    # 1. Compile metadata from standard sources
    subprocess.run(
        [py_bin, "bin/compile_metadata.py", "--repo-root", str(repo_root), "--output", ".agent/metadata.json"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # 2. Hydrate canonical agents for active engines
    for target in ["claude", "antigravity"]:
        subprocess.run(
            ["./scripts/hydrate.sh", target],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    # 3. Output valid empty protojson HookResult object for agy hook runner
    print(json.dumps({}))

if __name__ == "__main__":
    main()
