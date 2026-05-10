#!/usr/bin/env python3
"""
🏛️ SWARM NEXUS: Multi-Platform Symlink Engine (Simplified v2.0)
Codifies the relationship between core agents/skills and AI tool configurations.
Mirrors the discovery and $HOME-sync logic of sync_skills.sh.
"""

import argparse
import os
from pathlib import Path

# --- Configuration ---
# Physical Source of Truth
AGENT_SOURCE = Path(".agent/agents")
SKILL_SOURCE = Path(".agent/skills")

# Local Project Spokes
LOCAL_AGENT_SPOKES = [
    ".cursor/rules",
    ".claude/agents",
    ".gemini/agents",
    ".gemini/antigravity/agents",
    ".github/agents",
]

LOCAL_SKILL_SPOKES = [
    ".claude/skills",
    ".gemini/skills",
    ".gemini/antigravity/skills",
    ".github/skills",
]

# Global/System Spokes (Mirroring sync_skills.sh)
GLOBAL_SPOKES = [
    Path.home() / ".agent",
    Path.home() / ".claude",
    Path.home() / ".gemini",
    Path.home() / ".gemini/antigravity",
    Path.home() / ".config/github-copilot",
]

# Special Instruction Bridges
ROOT_LINKS = {
    "AGENT.md": [
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md"
    ]
}

def create_symlink(source: Path, target: Path):
    """Creates a symlink with safety checks."""
    if not source.exists():
        return

    target.parent.mkdir(parents=True, exist_ok=True)

    # Use relative path for local links, absolute for global
    try:
        # If target is within the same root as source, use relative
        # This is a bit complex for global links, so we'll just check if target starts with $HOME
        if str(target).startswith(str(Path.home())):
            rel_source = str(source.absolute())
        else:
            rel_source = os.path.relpath(source, target.parent)
    except ValueError:
        rel_source = str(source.absolute())

    if target.is_symlink():
        if target.exists() and os.readlink(target) == rel_source:
            return # Already correct
        target.unlink()
    elif target.exists():
        # Do not overwrite real files
        print(f"⚠️ Target exists and is NOT a symlink: {target}")
        return

    try:
        target.symlink_to(rel_source)
        print(f"🔗 Linked: {target} -> {rel_source}")
    except Exception as e:
        print(f"❌ Error linking {target}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Swarm Nexus: Sync Agents and Skills")
    parser.add_argument("--global-sync", action="store_true", help="Sync to $HOME directories")
    args = parser.parse_args()

    # Move to repo root to ensure paths are consistent
    repo_root = Path(__file__).parent.parent.absolute()
    os.chdir(repo_root)

    print(f"🚀 Initializing Swarm Nexus at {repo_root}...")

    # 1. Discover and Sync Agents (*.md)
    if AGENT_SOURCE.exists():
        for agent_file in AGENT_SOURCE.glob("*.md"):
            if agent_file.name == "AGENT.md":
                continue

            # Link to Local Spokes
            for spoke in LOCAL_AGENT_SPOKES:
                create_symlink(agent_file, Path(spoke) / agent_file.name)

            # Link to Global Spokes
            if args.global_sync:
                for base in GLOBAL_SPOKES:
                    create_symlink(agent_file, base / "agents" / agent_file.name)

    # 2. Discover and Sync Skills (*.md)
    if SKILL_SOURCE.exists():
        for skill_file in SKILL_SOURCE.glob("*.md"):
            # Link to Local Spokes
            for spoke in LOCAL_SKILL_SPOKES:
                create_symlink(skill_file, Path(spoke) / skill_file.name)

            # Link to Global Spokes
            if args.global_sync:
                for base in GLOBAL_SPOKES:
                    create_symlink(skill_file, base / "skills" / skill_file.name)

    # 3. Instruction Bridges
    for source_rel, targets in ROOT_LINKS.items():
        source = Path(source_rel)
        for target_rel in targets:
            create_symlink(source, Path(target_rel))

    print("✅ Nexus synchronization complete.")

if __name__ == "__main__":
    main()
