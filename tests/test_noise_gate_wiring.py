"""The noise gate is wired for Claude and Antigravity from the canonical sources, and fails open."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".agent/skills/skill-code-map/scripts/noise_gate.py"


def test_claude_source_and_projection_carry_the_hook():
    for rel in (".agent/adapters/settings/claude.json", ".claude/settings.json"):
        entries = json.loads((ROOT / rel).read_text())["hooks"]["PreToolUse"]
        gate = [e for e in entries if e["matcher"] == "Grep|Bash"]
        assert gate and "noise_gate.py" in gate[0]["hooks"][0]["command"], rel
        assert gate[0]["hooks"][0]["command"].endswith("|| true")


def test_agy_hook_runs_from_dot_agents_and_falls_back_to_allow():
    hooks = json.loads((ROOT / ".agent/hooks/hooks.json").read_text())["hooks"]["PreToolUse"][0]
    cmd = hooks["hooks"][0]["command"]
    assert "run_command" in hooks["matcher"] and "grep_search" in hooks["matcher"]
    assert cmd.startswith("python3 ../.agent/skills/skill-code-map/scripts/noise_gate.py")  # cwd is <workspace>/.agents
    assert '"decision":"allow"' in cmd and "||" in cmd
    assert (ROOT / ".agents" / cmd.split()[1]).resolve() == GATE.resolve()


def test_gate_fails_open_on_garbage_input():
    run = subprocess.run([sys.executable, str(GATE)], input="not json", capture_output=True, text=True)
    assert run.returncode == 0 and "deny" not in run.stdout


def test_find_usages_footer_in_skill_copy_is_exact_for_go_packages(tmp_path):
    g = {"nodes": {"go:a": {"type": "go-package"}, "go:b": {"type": "go-package"}},
         "edges": [{"from": "go:b", "to": "go:a", "type": "imports"}]}  # fmt: skip
    f = tmp_path / "g.json"
    f.write_text(json.dumps(g))
    q = ROOT / ".agent/skills/skill-code-map/scripts/semantic_query.py"
    out = subprocess.run([sys.executable, str(q), "--graph", str(f), "find-usages", "go:a"], capture_output=True, text=True).stdout
    assert "complete for those files" in out and "git grep -lw" not in out
