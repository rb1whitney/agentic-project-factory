#!/usr/bin/env python3
"""Log structured agent skill/tool papercuts (what tried, expected, actual, fix)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path


def append_papercut(
    log_path: Path,
    skill: str,
    tried: str,
    expected: str,
    actual: str,
    fix: str,
) -> dict:
    """Append a structured JSONL papercut entry and return it."""
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "skill": skill,
        "tried": tried,
        "expected": expected,
        "actual": actual,
        "suggested_fix": fix,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    os.chmod(log_path, 0o600)
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record structured skill papercut report")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--tried", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--actual", required=True)
    parser.add_argument("--fix", required=True)
    parser.add_argument("--log", type=Path, default=Path(".agent/papercuts.jsonl"))
    args = parser.parse_args(argv)
    entry = append_papercut(args.log, args.skill, args.tried, args.expected, args.actual, args.fix)
    print(json.dumps(entry))
    return 0


if __name__ == "__main__":
    sys.exit(main())
