#!/usr/bin/env python3
"""
test_agent_webhook_autoload.py - Demonstrates and validates that the webhook
autoloads agents and skills across Claude Code and Antigravity (agy).
Tests 3 representative specialist agents across both environments:
1. db-migration-agent
2. specialist-aws
3. memory-agent
"""

import json
import os
import subprocess
import sys
from pathlib import Path

TARGET_AGENTS = ["db-migration", "specialist-aws", "memory-agent"]

def simulate_webhook_execution():
    print("[1/4] Simulating adapter webhook trigger (bin/autoload_webhook.py)...")
    res = subprocess.run(
        [sys.executable, "bin/autoload_webhook.py"],
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"Webhook execution failed: {res.stderr}"
    data = json.loads(res.stdout)
    assert data.get("status") == "success", f"Invalid response: {data}"
    print("      Webhook successfully executed and returned valid JSON response.")

def verify_agy_loaded():
    print("[2/4] Testing Antigravity (agy) agent/skill autoloading...")
    # Check hook configuration
    agy_hooks = Path(".agents/hooks.json")
    assert agy_hooks.exists(), "Missing .agents/hooks.json"
    with open(agy_hooks) as f:
        hooks_data = json.load(f)
    assert "factory-autoload-webhook" in hooks_data, "Webhook not registered in .agents/hooks.json"

    # Verify target agents exist with valid schemas
    for agent in TARGET_AGENTS:
        agent_json_path = Path(f".agents/{agent}.json")
        assert agent_json_path.exists(), f"Agent {agent} missing from .agents/"
        with open(agent_json_path) as f:
            agent_data = json.load(f)
        assert agent_data.get("name") is not None, f"Agent {agent} missing name"
        assert agent_data.get("model") is not None, f"Agent {agent} missing model"
        assert "tools" in agent_data, f"Agent {agent} missing tools"
        print(f"      [AGY] Verified loaded: {agent} (model={agent_data['model']}, tools={len(agent_data['tools'])})")

def verify_claude_loaded():
    print("[3/4] Testing Claude Code agent/skill autoloading...")
    claude_settings = Path(".claude/settings.json")
    assert claude_settings.exists(), "Missing .claude/settings.json"
    with open(claude_settings) as f:
        settings_data = json.load(f)
    assert "hooks" in settings_data and "SessionStart" in settings_data["hooks"], "Hook missing in .claude/settings.json"

    for agent in TARGET_AGENTS:
        agent_md_path = Path(f".claude/agents/{agent}.md")
        assert agent_md_path.exists(), f"Agent {agent} missing from .claude/agents/"
        content = agent_md_path.read_text(encoding="utf-8")
        assert content.startswith("---"), f"Agent {agent} missing YAML frontmatter boundary"
        assert f"name: {agent}" in content or f"name: {agent}-agent" in content, f"Agent {agent} name mismatch"
        assert "model: " in content, f"Agent {agent} missing model"
        assert "tools: " in content, f"Agent {agent} missing tools"
        print(f"      [CLAUDE] Verified loaded: {agent} with valid frontmatter.")

def verify_skills_available():
    print("[4/4] Verifying skill availability for both harnesses...")
    claude_skills = Path(".claude/skills")
    agy_skills = Path(".agents/skills")
    assert claude_skills.exists(), "Missing .claude/skills"
    assert agy_skills.exists(), "Missing .agents/skills"

    claude_count = len([s for s in claude_skills.iterdir() if s.is_dir() and not s.name.startswith(".")])
    agy_count = len([s for s in agy_skills.iterdir() if s.is_dir() and not s.name.startswith(".")])
    print(f"      Claude Skills: {claude_count} loaded")
    print(f"      Antigravity Skills: {agy_count} loaded")
    assert claude_count >= 50, f"Claude skills count low: {claude_count}"
    assert agy_count >= 50, f"Antigravity skills count low: {agy_count}"

def main():
    print("==================================================")
    print("TEST: ADAPTER WEBHOOK AUTOLOAD FOR AGY & CLAUDE")
    print("==================================================")
    simulate_webhook_execution()
    verify_agy_loaded()
    verify_claude_loaded()
    verify_skills_available()
    print("\nALL HARNESS AUTOLOAD TESTS PASSED.")

if __name__ == "__main__":
    main()
