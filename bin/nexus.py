#!/usr/bin/env python3
"""
SWARM NEXUS: Multi-Platform Symlink Engine (Simplified v2.0)
Codifies the relationship between core agents/skills and AI tool configurations.
"""

import argparse
import os
from pathlib import Path

# --- Configuration ---
AGENT_SOURCE = Path(".agent/agents")
SKILL_SOURCE = Path(".agent/skills")
POLICY_SOURCE = Path(".agent/policies")

LOCAL_AGENT_SPOKES = [
    ".claude/agents", ".gemini/agents", ".gemini/antigravity/agents",
    ".github/agents", ".agents/agents", ".antigravitycli/agents",
]

LOCAL_SKILL_SPOKES = [
    ".claude/skills", ".gemini/skills", ".gemini/antigravity/skills",
    ".github/skills", ".agents/skills", ".antigravitycli/skills",
]

LOCAL_POLICY_SPOKES = [
    ".claude/policies", ".gemini/policies", ".agents/policies", ".antigravitycli/policies",
]

GLOBAL_SPOKES = [
    Path.home() / ".agent", Path.home() / ".claude", Path.home() / ".gemini",
    Path.home() / ".gemini/antigravity", Path.home() / ".config/github-copilot",
    Path.home() / ".gemini/antigravity-cli", Path.home() / ".antigravitycli",
    Path.home() / ".config/opencode",
]

ROOT_LINKS = {
    "AGENTS.md": [".github/copilot-instructions.md"]
}

def create_symlink(source: Path, target: Path, verbose=False):
    """Creates a symlink with safety checks."""
    if not source.exists():
        return False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if str(target).startswith(str(Path.home())):
            rel_source = str(source.absolute())
        else:
            rel_source = os.path.relpath(source, target.parent)

        if target.is_symlink():
            if target.exists() and os.readlink(target) == rel_source:
                return True
            target.unlink()
        elif target.exists():
            if verbose:
                print(f"Skipping: {target} (exists and is NOT a symlink)")
            return False

        target.symlink_to(rel_source)
        if verbose:
            print(f"Linked: {target}")
        return True
    except Exception as e:
        print(f"Error linking {target}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Swarm Nexus: Sync Agents and Skills")
    parser.add_argument("--global-sync", action="store_true", help="Sync to $HOME directories")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.absolute()
    os.chdir(repo_root)

    counts = {"agents": 0, "skills": 0, "policies": 0}

    # 1. Sync Agents
    if AGENT_SOURCE.exists():
        for agent_file in AGENT_SOURCE.glob("*.md"):
            if agent_file.name == "AGENT.md": continue
            success = False
            for spoke in LOCAL_AGENT_SPOKES:
                target_name = agent_file.name
                if spoke == ".github/agents" and target_name.endswith(".md") and not target_name.endswith(".agent.md"):
                    target_name = target_name[:-3] + ".agent.md"
                if create_symlink(agent_file, Path(spoke) / target_name, args.verbose): success = True
            
            if args.global_sync:
                for base in GLOBAL_SPOKES:
                    if create_symlink(agent_file, base / "agents" / agent_file.name, args.verbose): success = True
            if success: counts["agents"] += 1

    # 2. Sync Skills
    if SKILL_SOURCE.exists():
        for skill_item in SKILL_SOURCE.iterdir():
            if skill_item.name.startswith("."): continue
            success = False
            if skill_item.is_dir() or skill_item.suffix == ".md":
                for spoke in LOCAL_SKILL_SPOKES:
                    if create_symlink(skill_item, Path(spoke) / skill_item.name, args.verbose): success = True
                if args.global_sync:
                    for base in GLOBAL_SPOKES:
                        if create_symlink(skill_item, base / "skills" / skill_item.name, args.verbose): success = True
            if success: counts["skills"] += 1

    # 3. Sync Policies
    if POLICY_SOURCE.exists():
        for policy_file in POLICY_SOURCE.iterdir():
            if policy_file.suffix in [".toml", ".yaml", ".md"]:
                success = False
                for spoke in LOCAL_POLICY_SPOKES:
                    if create_symlink(policy_file, Path(spoke) / policy_file.name, args.verbose): success = True
                if args.global_sync:
                    for base in GLOBAL_SPOKES:
                        if create_symlink(policy_file, base / "policies" / policy_file.name, args.verbose): success = True
                if success: counts["policies"] += 1

    # 4. Instruction Bridges
    for source_rel, targets in ROOT_LINKS.items():
        source = Path(source_rel)
        for target_rel in targets:
            create_symlink(source, Path(target_rel), args.verbose)

    print(f"Nexus Sync: {counts['agents']} agents, {counts['skills']} skills, {counts['policies']} policies")

if __name__ == "__main__":
    main()
