#!/usr/bin/env python3
"""
Test Harness Adapter Invariants:
1. Orphan pruning: Hydration removes projected files when canonical YAML is removed.
2. Banner truth: Generated headers reference actual source YAML file path, even when name differs from filename stem.
3. Antigravity twin parity: .agents/<name>.json and .agents/agents/<name>.md maintain parity on
   commandExecutionPolicy and auto_approve.
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
AGENT_DIR = REPO_ROOT / ".agent" / "agents"
CLAUDE_DIR = REPO_ROOT / ".claude" / "agents"
AGENTS_DIR = REPO_ROOT / ".agents"
CODEX_DIR = REPO_ROOT / ".codex" / "agents"
HYDRATE_SCRIPT = REPO_ROOT / "scripts" / "hydrate.py"


class TestAdapterInvariants(unittest.TestCase):
    def test_banner_source_path_fidelity(self):
        """Banner must reference actual source file path (e.g. db-migration.yaml vs db-migration-agent)."""
        src_yaml = AGENT_DIR / "db-migration.yaml"
        self.assertTrue(src_yaml.exists(), "db-migration.yaml must exist")

        # Claude projection check
        claude_file = CLAUDE_DIR / "db-migration-agent.md"
        self.assertTrue(claude_file.exists(), f"{claude_file} must exist")
        content = claude_file.read_text(encoding="utf-8")
        self.assertIn(".agent/agents/db-migration.yaml", content)

        # Codex projection check
        codex_file = CODEX_DIR / "db-migration-agent.toml"
        self.assertTrue(codex_file.exists(), f"{codex_file} must exist")
        content = codex_file.read_text(encoding="utf-8")
        self.assertIn(".agent/agents/db-migration.yaml", content)

        # Antigravity MD projection check
        ag_md_file = AGENTS_DIR / "agents" / "db-migration-agent.md"
        self.assertTrue(ag_md_file.exists(), f"{ag_md_file} must exist")
        content = ag_md_file.read_text(encoding="utf-8")
        self.assertIn(".agent/agents/db-migration.yaml", content)

    def test_antigravity_twin_parity(self):
        """Antigravity JSON and MD twins must declare identical commandExecutionPolicy and auto_approve."""
        raw_json_files = list(AGENTS_DIR.glob("*.json"))
        # Exclude non-agent hub symlinks (manifest, hooks, settings, mcp_config)
        agent_names = {p.stem for p in (AGENTS_DIR / "agents").glob("*.md")}
        json_files = [p for p in raw_json_files if p.stem in agent_names]
        self.assertEqual(len(json_files), len(agent_names), "JSON and MD twin count mismatch")
        self.assertGreater(len(json_files), 0, "No Antigravity JSON agent specs found")

        for j_path in json_files:
            name = j_path.stem
            md_path = AGENTS_DIR / "agents" / f"{name}.md"
            self.assertTrue(md_path.exists(), f"Antigravity MD twin missing for {j_path.name}")

            # Parse JSON
            with open(j_path, "r", encoding="utf-8") as f:
                j_data = json.load(f)

            # Parse MD frontmatter
            md_text = md_path.read_text(encoding="utf-8")
            match = re.match(r"^---\n(.*?)\n---", md_text, re.DOTALL)
            self.assertIsNotNone(match, f"Frontmatter missing in {md_path}")
            frontmatter_raw = match.group(1)

            # Extract fields from frontmatter
            cmd_policy_match = re.search(r"^commandExecutionPolicy:\s*(\w+)", frontmatter_raw, re.MULTILINE)
            self.assertIsNotNone(cmd_policy_match, f"commandExecutionPolicy missing in {md_path}")
            md_cmd_policy = cmd_policy_match.group(1)

            j_cmd_policy = j_data.get("commandExecutionPolicy")
            self.assertEqual(j_cmd_policy, md_cmd_policy, f"commandExecutionPolicy mismatch for {name}")

            # Auto approve check
            j_auto = sorted(j_data.get("auto_approve", []))
            auto_matches = re.findall(r"^auto_approve:\s*\n((?:\s*-\s*[^\n]+\n)*)", frontmatter_raw, re.MULTILINE)
            md_auto = []
            if auto_matches:
                md_auto = re.findall(r"-\s*(\S+)", auto_matches[0])
            md_auto = sorted(md_auto)
            self.assertEqual(j_auto, md_auto, f"auto_approve mismatch for {name}: JSON={j_auto}, MD={md_auto}")

    def test_orphan_pruning_lifecycle(self):
        """When canonical agent is deleted/renamed, hydration must prune projected files from all harness dirs."""
        dummy_name = "test-dummy-ephemeral"
        dummy_yaml = AGENT_DIR / f"{dummy_name}.yaml"

        dummy_content = f"""name: {dummy_name}
description: Ephemeral test agent for pruning invariant
tier: small
capabilities:
  - read
  - search
system_prompt: |
  Ephemeral test prompt for orphan pruning test.
"""
        try:
            # 1. Write dummy canonical agent
            dummy_yaml.write_text(dummy_content, encoding="utf-8")

            # 2. Run hydrate
            res = subprocess.run([sys.executable, str(HYDRATE_SCRIPT), "all"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Hydrate failed on dummy creation: {res.stderr}")

            # 3. Verify files projected
            dummy_claude = CLAUDE_DIR / f"{dummy_name}.md"
            dummy_codex = CODEX_DIR / f"{dummy_name}.toml"
            dummy_ag_json = AGENTS_DIR / f"{dummy_name}.json"
            dummy_ag_md = AGENTS_DIR / "agents" / f"{dummy_name}.md"

            self.assertTrue(dummy_claude.exists(), f"Claude output not created: {dummy_claude}")
            self.assertTrue(dummy_codex.exists(), f"Codex output not created: {dummy_codex}")
            self.assertTrue(dummy_ag_json.exists(), f"AG JSON output not created: {dummy_ag_json}")
            self.assertTrue(dummy_ag_md.exists(), f"AG MD output not created: {dummy_ag_md}")

            # 4. Remove dummy canonical agent
            dummy_yaml.unlink()

            # 5. Run hydrate again
            res2 = subprocess.run([sys.executable, str(HYDRATE_SCRIPT), "all"], capture_output=True, text=True)
            self.assertEqual(res2.returncode, 0, f"Hydrate failed on pruning pass: {res2.stderr}")

            # 6. Verify projected files were pruned
            self.assertFalse(dummy_claude.exists(), f"Claude output was NOT pruned: {dummy_claude}")
            self.assertFalse(dummy_codex.exists(), f"Codex output was NOT pruned: {dummy_codex}")
            self.assertFalse(dummy_ag_json.exists(), f"AG JSON output was NOT pruned: {dummy_ag_json}")
            self.assertFalse(dummy_ag_md.exists(), f"AG MD output was NOT pruned: {dummy_ag_md}")

        finally:
            # Cleanup in case of test failure
            if dummy_yaml.exists():
                dummy_yaml.unlink()
            for path in [
                CLAUDE_DIR / f"{dummy_name}.md",
                CODEX_DIR / f"{dummy_name}.toml",
                AGENTS_DIR / f"{dummy_name}.json",
                AGENTS_DIR / "agents" / f"{dummy_name}.md",
            ]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
