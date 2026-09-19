#!/usr/bin/env python3
"""
SWARM NEXUS: Multi-Platform Symlink Engine (Targeted v3.0)
Focused strictly on active harnesses: Antigravity (.agents), Claude (.claude), and GitHub/Codex (.github).
Decommissioned legacy .gemini, .copilot, .antigravitycli, and .opencode spokes.
"""

import argparse
import os
from pathlib import Path

# --- Canonical Master Sources ---
AGENT_SOURCE = Path(".agent/agents")
SKILL_SOURCE = Path(".agent/skills")
POLICY_SOURCE = Path(".agent/policies")
HOOK_SOURCE = Path(".agent/hooks")

# --- Active Local Spokes (Antigravity, Claude, GitHub/Codex) ---
LOCAL_AGENT_SPOKES = [
    ".claude/agents",
    ".github/agents",
]

LOCAL_SKILL_SPOKES = [
    ".claude/skills",
    ".agents/skills",
    ".github/skills",
]

LOCAL_POLICY_SPOKES = [
    ".claude/policies",
    ".agents/policies",
]

LOCAL_HOOK_SPOKES = [
    ".claude/hooks",
    ".agents/hooks",
    ".github/hooks",
]

ROOT_LINKS = {"AGENTS.md": [".github/copilot-instructions.md"]}

CONFIG_LINKS = {
    "manifest.json": [
        ".claude/manifest.json",
        ".agents/manifest.json",
    ],
    "mcp_config.json": [
        ".claude/mcp_config.json",
        ".agents/mcp_config.json",
    ],
    "settings.json": [
        ".claude/settings.json",
        ".agents/settings.json",
    ],
    "hooks/hooks.json": [
        ".agents/hooks.json",
    ],
}


def create_symlink(source: Path, target: Path, verbose=False):
    """Creates a symlink with safety checks."""
    if not source.exists():
        return False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
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


def cleanup_broken_links(verbose=False):
    """Scans spokes for broken symlinks and removes them."""
    spokes = LOCAL_AGENT_SPOKES + LOCAL_SKILL_SPOKES + LOCAL_POLICY_SPOKES + LOCAL_HOOK_SPOKES
    for targets in CONFIG_LINKS.values():
        spokes.extend(targets)
    for targets in ROOT_LINKS.values():
        spokes.extend(targets)

    parent_dirs = set(Path(s).parent for s in spokes)
    cleaned_count = 0

    for spoke in set(spokes):
        spoke_path = Path(spoke)
        if not spoke_path.exists():
            continue

        if spoke_path.is_dir():
            for item in spoke_path.glob("**/*"):
                if item.is_symlink() and not item.exists():
                    if verbose:
                        print(f"Removing broken symlink: {item}")
                    item.unlink()
                    cleaned_count += 1
        elif spoke_path.is_symlink() and not spoke_path.exists():
            if verbose:
                print(f"Removing broken symlink: {spoke_path}")
            spoke_path.unlink()
            cleaned_count += 1

    for parent_dir in parent_dirs:
        if parent_dir.exists() and parent_dir.is_dir():
            for item in parent_dir.iterdir():
                if item.is_symlink() and not item.exists():
                    if verbose:
                        print(f"Removing broken symlink: {item}")
                    item.unlink()
                    cleaned_count += 1

    if cleaned_count > 0 and verbose:
        print(f"Nexus Clean: Removed {cleaned_count} broken symlinks")


def main():
    parser = argparse.ArgumentParser(description="Swarm Nexus: Sync Active Harnesses (Claude, AGY, Codex)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("actions", nargs="*", help="Optional actions")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.absolute()
    os.chdir(repo_root)

    cleanup_broken_links(args.verbose)

    counts = {"skills": 0, "policies": 0, "hooks": 0}

    # 1. Sync Skills to active spokes
    if SKILL_SOURCE.exists():
        for skill_item in SKILL_SOURCE.iterdir():
            if skill_item.name.startswith("."):
                continue
            success = False
            if skill_item.is_dir() or skill_item.suffix == ".md":
                for spoke in LOCAL_SKILL_SPOKES:
                    if create_symlink(skill_item, Path(spoke) / skill_item.name, args.verbose):
                        success = True
            if success:
                counts["skills"] += 1

    # 2. Sync Policies
    if POLICY_SOURCE.exists():
        for policy_file in POLICY_SOURCE.iterdir():
            if policy_file.suffix in [".toml", ".yaml", ".md"]:
                success = False
                for spoke in LOCAL_POLICY_SPOKES:
                    if create_symlink(policy_file, Path(spoke) / policy_file.name, args.verbose):
                        success = True
                if success:
                    counts["policies"] += 1

    # 3. Sync Hooks
    if HOOK_SOURCE.exists():
        for hook_item in HOOK_SOURCE.iterdir():
            if hook_item.name.startswith("."):
                continue
            success = False
            for spoke in LOCAL_HOOK_SPOKES:
                if create_symlink(hook_item, Path(spoke) / hook_item.name, args.verbose):
                    success = True
            if success:
                counts["hooks"] += 1

    # 4. Instruction Bridges (AGENTS.md -> .github/copilot-instructions.md)
    for source_rel, targets in ROOT_LINKS.items():
        source = Path(source_rel)
        for target_rel in targets:
            create_symlink(source, Path(target_rel), args.verbose)

    # 5. Configurations
    for config_file_name, targets in CONFIG_LINKS.items():
        config_file = Path(".agent") / config_file_name
        if config_file.exists():
            for target in targets:
                create_symlink(config_file, Path(target), args.verbose)

    print(
        f"Nexus Sync: {counts['skills']} skills, {counts['policies']} policies, {counts['hooks']} hooks "
        f"active across [.claude, .agents, .github]"
    )


if __name__ == "__main__":
    main()
