#!/usr/bin/env python3
"""
Scenario Test: Frontmatter Parser & Horizontal Rule (---) Body Edge Cases
Verifies that scripts/hydrate.py parses single-document agent YAML whose `prompt: |` block contains
markdown horizontal rules ('---') without corruption or truncation, and rejects the legacy
'---' + Markdown body format and schema violations (fail loud).
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.hydrate import load_map, parse_agent_file  # noqa: E402


class TestParserEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_data = load_map()

    def _parse(self, name, content):
        # File stem must equal `name` (schema rule), so write into a private temp dir.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / f"{name}.yaml"
            path.write_text(content, encoding="utf-8")
            return parse_agent_file(str(path), self.map_data)

    def test_horizontal_rules_inside_prompt(self):
        content = """version: '2.1'
name: test-hr-agent
description: Test agent with horizontal rules in prompt body.
tier: fast
capabilities: [read, search]
skills: [skill-conductor]
prompt: |
  # Primary Section

  Some introductory text.

  ---

  ## Secondary Section Separated By Horizontal Rule

  | A | B |
  |---|---|
  | 1 | 2 |

  ---
  Key-Value: Not-A-Header
  ---

  Final concluding notes.
"""
        parsed = self._parse("test-hr-agent", content)
        self.assertEqual(parsed["name"], "test-hr-agent")
        self.assertEqual(parsed["tier"], "fast")
        self.assertEqual(parsed["capabilities"], ["read", "search"])
        self.assertIn("## Secondary Section Separated By Horizontal Rule", parsed["body"])
        self.assertIn("Key-Value: Not-A-Header", parsed["body"])
        self.assertIn("Final concluding notes.", parsed["body"])
        self.assertGreaterEqual(parsed["body"].count("---"), 3)

    def test_legacy_multi_document_rejected(self):
        content = """version: '2.1'
name: test-legacy-agent
description: Legacy header plus markdown body.
tier: fast
capabilities: [read]
---
# Prompt
Body.
"""
        with self.assertRaises(SystemExit) as cm:
            self._parse("test-legacy-agent", content)
        self.assertEqual(cm.exception.code, 1)

    def test_fail_loud_on_missing_capabilities(self):
        content = """version: '2.1'
name: test-invalid-agent
description: Agent missing capabilities.
tier: fast
prompt: |
  Test prompt.
"""
        with self.assertRaises(SystemExit) as cm:
            self._parse("test-invalid-agent", content)
        self.assertEqual(cm.exception.code, 1)

    def test_stem_must_equal_name(self):
        content = """version: '2.1'
name: other-name
description: Stem mismatch.
tier: fast
capabilities: [read]
prompt: |
  x
"""
        with self.assertRaises(SystemExit) as cm:
            self._parse("test-stem-agent", content)
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
