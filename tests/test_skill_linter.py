#!/usr/bin/env python3
"""Unit tests for scripts/sap/lint_skills.py and bin/log_papercut.py."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "sap"))
sys.path.insert(0, str(ROOT / "bin"))

import lint_skills as ls  # noqa: E402
import log_papercut as lp  # noqa: E402

GOOD_SKILL = """---
name: skill-demo
description: Demo skill.
---
# Skill: Demo

```bash
echo "run"
```

1. Run command.
2. Verify output matches expected state.

## Error Recovery

| Failure / Symptom | Cause | Concrete Fix |
| :--- | :--- | :--- |
| `exit 1` | Missing env var | Export `TARGET_ENV` and re-run |
"""


class TestSkillLinterAndPapercut(unittest.TestCase):
    def test_good_skill_passes(self):
        self.assertEqual(ls.lint_skill_text(GOOD_SKILL), [])

    def test_rejects_missing_error_recovery_and_try_again(self):
        no_err = GOOD_SKILL.split("## Error Recovery")[0]
        errs = ls.lint_skill_text(no_err)
        self.assertTrue(any("Error Recovery" in e for e in errs))

        vague = GOOD_SKILL.replace("Export `TARGET_ENV` and re-run", "Try again")
        errs_vague = ls.lint_skill_text(vague)
        self.assertTrue(any("try again" in e.lower() for e in errs_vague))

    def test_papercut_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "papercuts.jsonl"
            lp.append_papercut(p, "skill-gcp", "cmd", "pass", "403", "set quota project")
            lines = p.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            row = json.loads(lines[0])
            self.assertEqual(row["skill"], "skill-gcp")
            self.assertEqual(row["suggested_fix"], "set quota project")


if __name__ == "__main__":
    unittest.main()
