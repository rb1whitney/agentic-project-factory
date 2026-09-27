#!/usr/bin/env python3
"""
Scenario Test: Frontmatter Parser & Horizontal Rule (---) Body Edge Cases
Verifies that scripts/hydrate.py correctly isolates YAML headers from prompt bodies
containing markdown horizontal rules ('---') without corruption, truncation, or silent fallback.
"""

import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.hydrate import parse_agent_file, load_map


class TestParserEdgeCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_data = load_map()

    def test_horizontal_rules_inside_body_unboxed_header(self):
        """Test unboxed YAML header with multiple '---' horizontal rules in prompt body."""
        content = """version: 2.0
name: test-hr-agent
description: Test agent with horizontal rules in prompt body.
role: worker
tier: fast
capabilities: [read, search]
skills: [skill-conductor]
---
# Primary Section

Some introductory text.

---

## Secondary Section Separated By Horizontal Rule

Here is an example code block or text:
---
Key-Value: Not-A-Header
---

Final concluding notes.
"""
        with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as tf:
            tf.write(content)
            tf.flush()
            temp_path = tf.name

        try:
            parsed = parse_agent_file(temp_path, self.map_data)
            self.assertEqual(parsed["name"], "test-hr-agent")
            self.assertEqual(parsed["tier"], "fast")
            self.assertEqual(parsed["capabilities"], ["read", "search"])
            self.assertIn("## Secondary Section Separated By Horizontal Rule", parsed["body"])
            self.assertIn("Key-Value: Not-A-Header", parsed["body"])
            self.assertIn("Final concluding notes.", parsed["body"])
            # Ensure the body retained its internal '---' markers
            self.assertGreaterEqual(parsed["body"].count("---"), 2)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_horizontal_rules_inside_body_boxed_header(self):
        """Test boxed YAML header (starting with line 1 '---') with '---' in prompt body."""
        content = """---
version: 2.0
name: test-boxed-agent
description: Test agent with boxed frontmatter and internal horizontal rules.
role: worker
tier: deep
capabilities: [read, search, shell]
skills: [skill-conductor]
---
# Architectural Evaluation

Overview text.

---

### Matrix Section
| A | B |
|---|---|
| 1 | 2 |

---

End of report.
"""
        with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as tf:
            tf.write(content)
            tf.flush()
            temp_path = tf.name

        try:
            parsed = parse_agent_file(temp_path, self.map_data)
            self.assertEqual(parsed["name"], "test-boxed-agent")
            self.assertEqual(parsed["tier"], "deep")
            self.assertEqual(parsed["capabilities"], ["read", "search", "shell"])
            self.assertIn("### Matrix Section", parsed["body"])
            self.assertIn("| A | B |", parsed["body"])
            self.assertIn("End of report.", parsed["body"])
            self.assertGreaterEqual(parsed["body"].count("---"), 2)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_fail_loud_on_missing_capabilities(self):
        """Test that missing capabilities halts execution and does not fallback to guessing."""
        content = """version: 2.0
name: test-invalid-agent
description: Agent missing capabilities.
role: worker
tier: fast
skills: [skill-conductor]
---
# Prompt
Test prompt.
"""
        with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as tf:
            tf.write(content)
            tf.flush()
            temp_path = tf.name

        try:
            with self.assertRaises(SystemExit) as cm:
                parse_agent_file(temp_path, self.map_data)
            self.assertEqual(cm.exception.code, 1)
        finally:
            Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
