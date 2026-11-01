"""Characterization tests for the model-discovery helpers in scripts/hydrate.py."""

import importlib.util
import json
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "hydrate", Path(__file__).resolve().parent.parent / "scripts" / "hydrate.py"
)
hydrate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hydrate)

MAP = """harnesses:
  claude:
    tiers:
      fast: sonnet
  antigravity:
    tiers:
      fast: flash   # keep me
      deep: pro
    tier_rules:
      fast: '^x$'
  codex:
    tiers:
      fast: gpt-6-luna
providers:
  native:
    tiers:
      fast: untouched
"""


class ModelDiscoveryTests(unittest.TestCase):
    def test_parse_agy_models_skips_status_line(self):
        out = "Fetching available models...\ngemini-3.8-flash-high\tGemini 3.8 Flash (High)\n"
        self.assertEqual(hydrate.parse_agy_models(out), ["gemini-3.8-flash-high"])

    def test_parse_codex_models_keeps_only_listed(self):
        out = json.dumps(
            {
                "models": [
                    {"slug": "a", "visibility": "list"},
                    {"slug": "b", "visibility": "hide"},
                ]
            }
        )
        self.assertEqual(hydrate.parse_codex_models(out), ["a"])

    def test_parse_claude_lines_active_only(self):
        payload = {
            "data": [
                {"line": "opus", "lifecycle": "active"},
                {"line": "haiku", "lifecycle": "retired"},
                {"line": None, "lifecycle": "active"},
            ]
        }
        self.assertEqual(hydrate.parse_claude_lines(payload), {"opus"})

    def test_pick_best_prefers_highest_version(self):
        ids = ["gpt-5.5-luna", "gpt-5.6-luna", "gpt-5.10-luna", "gpt-5.6-sol"]
        self.assertEqual(hydrate.pick_best(ids, r"^gpt-[0-9.]+-luna$"), "gpt-5.10-luna")

    def test_pick_best_no_match(self):
        self.assertIsNone(hydrate.pick_best(["a"], r"^b$"))

    def test_rewrite_tier_scoped_and_preserves_comment(self):
        out = hydrate.rewrite_tier(MAP, "antigravity", "fast", "gemini-3.8-flash-medium")
        self.assertIn("      fast: gemini-3.8-flash-medium   # keep me", out)
        self.assertIn("      fast: sonnet", out)
        self.assertIn("      fast: untouched", out)
        self.assertIn("      deep: pro", out)

    def test_rewrite_tier_unknown_raises(self):
        with self.assertRaises(KeyError):
            hydrate.rewrite_tier(MAP, "codex", "deep", "x")


if __name__ == "__main__":
    unittest.main()
