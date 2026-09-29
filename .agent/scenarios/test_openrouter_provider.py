#!/usr/bin/env python3
"""
Scenario Test: OpenRouter Provider Integration
Validates that scripts/hydrate.py properly translates tiers to OpenRouter models
and generates OpenAI-compatible endpoints without hardcoding secrets.
"""

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HYDRATE_SCRIPT = REPO_ROOT / "scripts" / "hydrate.py"
CODEX_DIR = REPO_ROOT / ".codex" / "agents"


class TestOpenRouterProvider(unittest.TestCase):
    def test_openrouter_codex_projection(self):
        res = subprocess.run(
            [sys.executable, str(HYDRATE_SCRIPT), "codex", "--provider=openrouter"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Hydration failed: {res.stderr}")

        scout_toml = CODEX_DIR / "swarm-scout.toml"
        self.assertTrue(scout_toml.exists(), "swarm-scout.toml should exist")
        content = scout_toml.read_text(encoding="utf-8")

        # Must declare OpenRouter model and model_provider
        self.assertIn('model = "anthropic/claude-3.5-sonnet"', content)
        self.assertIn('model_provider = "openrouter"', content)
        self.assertNotIn("api_base", content)

        # Must never contain raw API keys
        self.assertNotIn("sk-or-v1", content)
        self.assertNotIn("OPENROUTER_API_KEY=", content)

    def test_native_provider_fallback(self):
        res = subprocess.run(
            [sys.executable, str(HYDRATE_SCRIPT), "codex", "--provider=native"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, f"Hydration failed: {res.stderr}")

        scout_toml = CODEX_DIR / "swarm-scout.toml"
        content = scout_toml.read_text(encoding="utf-8")

        # Native provider defaults to native model and omits api_base
        self.assertIn('model = "gpt-5-turbo"', content)
        self.assertNotIn("api_base", content)


if __name__ == "__main__":
    unittest.main()
