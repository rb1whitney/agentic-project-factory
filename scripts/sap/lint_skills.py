#!/usr/bin/env python3
"""Uber-style Skill Code-Smell Linter for .agent/skills/*/SKILL.md.

Checks:
1. YAML frontmatter with `name` and `description`.
2. Body kept under 500 lines (progressive disclosure).
3. Concrete runnable command (`bash`/`sh` fenced block).
4. Numbered workflow steps (`1.`, `2.`, ...) with explicit verification/check.
5. Explicit `## Error Recovery` section with a Markdown table (no "try again" stubs).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

MAX_LINES = 500
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
_CODE_BLOCK_RE = re.compile(r"```(?:bash|sh)\n.+?```", re.S)
_NUMBERED_STEP_RE = re.compile(r"^\s*1\.\s+", re.M)
_VERIFY_RE = re.compile(r"(verify|check|assert|post-check|validate|confirm)", re.I)
_ERR_SECTION_RE = re.compile(r"^##\s+Error Recovery\b", re.M)
_TABLE_ROW_RE = re.compile(r"^\|.+\|.+\|$", re.M)
_TRY_AGAIN_RE = re.compile(r"^\|.*\btry again\b.*\|", re.I | re.M)


def lint_skill_text(text: str, name: str = "SKILL.md") -> List[str]:
    """Return list of lint failure messages for a SKILL.md string."""
    errors: List[str] = []
    lines = text.splitlines()
    if len(lines) > MAX_LINES:
        errors.append(f"{name}: {len(lines)} lines exceeds {MAX_LINES}-line limit")

    fm = _FRONTMATTER_RE.match(text)
    if not fm or "name:" not in fm.group(1) or "description:" not in fm.group(1):
        errors.append(f"{name}: missing YAML frontmatter with name and description")

    if not _CODE_BLOCK_RE.search(text):
        errors.append(f"{name}: missing concrete ```bash/```sh command block")

    if not _NUMBERED_STEP_RE.search(text):
        errors.append(f"{name}: missing numbered workflow steps")

    if not _VERIFY_RE.search(text):
        errors.append(f"{name}: missing explicit verification/check step")

    err_match = _ERR_SECTION_RE.search(text)
    if not err_match:
        errors.append(f"{name}: missing `## Error Recovery` section")
    else:
        tail = text[err_match.start() :]
        rows = _TABLE_ROW_RE.findall(tail)
        # Need header + separator + at least 1 concrete failure row
        if len(rows) < 3:
            errors.append(f"{name}: `## Error Recovery` must include a Markdown table with >=1 failure row")
        if _TRY_AGAIN_RE.search(tail):
            errors.append(f"{name}: `## Error Recovery` contains vague 'try again' fix")

    return errors


def lint_skills_dir(skills_dir: Path) -> Tuple[int, List[str]]:
    """Lint all skill-*/SKILL.md under skills_dir. Returns (checked_count, all_errors)."""
    all_errors: List[str] = []
    files = sorted(skills_dir.glob("skill-*/SKILL.md"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        all_errors.extend(lint_skill_text(text, str(path)))
    return len(files), all_errors


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint .agent/skills/skill-*/SKILL.md")
    parser.add_argument("--skills-dir", type=Path, default=Path(".agent/skills"))
    args = parser.parse_args(argv)
    count, errors = lint_skills_dir(args.skills_dir)
    if errors:
        for err in errors:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1
    print(f"[PASS] {count}/{count} skills passed Uber skill code-smell linter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
