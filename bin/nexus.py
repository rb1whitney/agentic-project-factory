#!/usr/bin/env python3
"""
SWARM NEXUS: Multi-Platform Symlink & Projection Engine (v3.1)
Synchronizes canonical skills (.agent/skills/*) and hydrated agents
(.claude/agents/*.md, .agents/agents/*.md, .agents/*.json) across:
- Project-local spokes: .claude/, .agents/, .github/, .codex/
- Global user spokes:   ~/.claude/{agents,skills}, ~/.gemini/config/{agents,skills}
"""

import argparse
import os
import shutil
from pathlib import Path

# --- Canonical Master Sources ---
AGENT_SOURCE = Path(".agent/agents")
SKILL_SOURCE = Path(".agent/skills")
POLICY_SOURCE = Path(".agent/policies")
HOOK_SOURCE = Path(".agent/hooks")

CLAUDE_HYDRATED_AGENTS = Path(".claude/agents")
AGY_HYDRATED_AGENTS_MD = Path(".agents/agents")
AGY_HYDRATED_AGENTS_JSON = Path(".agents")

# --- Active Local Spokes (Antigravity, Claude, GitHub/Codex) ---
LOCAL_AGENT_SPOKES = [
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
    "hooks/hooks.json": [
        ".agents/hooks.json",
    ],
}


def create_symlink(source: Path, target: Path, use_absolute: bool = False, verbose: bool = False) -> bool:
    """Creates a relative (or absolute for $HOME) symlink with safety checks."""
    if not source.exists():
        return False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        link_dest = str(source.resolve()) if use_absolute else os.path.relpath(source, target.parent)

        if target.is_symlink():
            if target.exists() and os.readlink(target) == link_dest:
                return True
            target.unlink()
        elif target.exists():
            if verbose:
                print(f"Skipping: {target} (exists and is NOT a symlink)")
            return False

        target.symlink_to(link_dest)
        if verbose:
            print(f"Linked: {target} -> {link_dest}")
        return True
    except Exception as e:
        print(f"Error linking {target}: {e}")
        return False


def cleanup_broken_links(directories: list[Path], verbose: bool = False) -> int:
    """Scans target directories for broken symlinks and removes them."""
    cleaned_count = 0
    for d in directories:
        if not d.exists():
            continue
        if d.is_symlink() and not d.exists():
            d.unlink()
            cleaned_count += 1
            continue
        if d.is_dir():
            for item in list(d.iterdir()):
                if item.is_symlink() and not item.exists():
                    if verbose:
                        print(f"Removing broken symlink: {item}")
                    item.unlink()
                    cleaned_count += 1
    if cleaned_count > 0 and verbose:
        print(f"Nexus Clean: Removed {cleaned_count} broken symlinks")
    return cleaned_count


def sync_global_harnesses(repo_root: Path, valid_skills: list[Path], verbose: bool = False) -> dict:
    """Synchronizes hydrated agents and canonical skills into ~/.claude and ~/.gemini/config."""
    home = Path.home()
    global_claude_agents = home / ".claude" / "agents"
    global_claude_skills = home / ".claude" / "skills"
    global_agy_agents = home / ".gemini" / "config" / "agents"
    global_agy_skills = home / ".gemini" / "config" / "skills"

    cleanup_broken_links(
        [global_claude_agents, global_claude_skills, global_agy_agents, global_agy_skills],
        verbose=verbose,
    )

    valid_skill_names = {s.name for s in valid_skills}
    expected_agent_mds = {p.name for p in (repo_root / CLAUDE_HYDRATED_AGENTS).glob("*.md")}

    # Prune stale repo-linked skills in global skill dirs
    for g_skill_dir in (global_claude_skills, global_agy_skills):
        if g_skill_dir.is_dir():
            for item in list(g_skill_dir.iterdir()):
                if item.is_symlink():
                    target_str = os.readlink(item)
                    if str(repo_root) in target_str and item.name not in valid_skill_names:
                        if verbose:
                            print(f"Pruning stale global skill symlink: {item}")
                        item.unlink()

    # Prune stale repo-linked agents in global agent dirs
    for g_agent_dir in (global_claude_agents, global_agy_agents):
        if g_agent_dir.is_dir():
            for item in list(g_agent_dir.iterdir()):
                if item.is_symlink():
                    target_str = os.readlink(item)
                    if str(repo_root) in target_str and item.name not in expected_agent_mds:
                        if verbose:
                            print(f"Pruning stale global agent symlink: {item}")
                        item.unlink()

    g_counts = {"global_skills": 0, "global_agents": 0}

    # Link valid skills into ~/.claude/skills and ~/.gemini/config/skills
    for skill_dir in valid_skills:
        ok_c = create_symlink(skill_dir, global_claude_skills / skill_dir.name, use_absolute=True, verbose=verbose)
        ok_a = create_symlink(skill_dir, global_agy_skills / skill_dir.name, use_absolute=True, verbose=verbose)
        if ok_c or ok_a:
            g_counts["global_skills"] += 1

    # Link hydrated Claude agents (.claude/agents/*.md) -> ~/.claude/agents/*.md
    for md_file in sorted((repo_root / CLAUDE_HYDRATED_AGENTS).glob("*.md")):
        if create_symlink(md_file, global_claude_agents / md_file.name, use_absolute=True, verbose=verbose):
            g_counts["global_agents"] += 1

    # Link hydrated Antigravity agents (.agents/agents/*.md) -> ~/.gemini/config/agents/*.md
    for md_file in sorted((repo_root / AGY_HYDRATED_AGENTS_MD).glob("*.md")):
        create_symlink(md_file, global_agy_agents / md_file.name, use_absolute=True, verbose=verbose)

    # Ensure autoload_webhook.py is reachable for global agy hooks
    agy_cli_bin = home / ".gemini/antigravity-cli/bin"
    if agy_cli_bin.is_dir():
        create_symlink(
            repo_root / "bin/autoload_webhook.py",
            agy_cli_bin / "autoload_webhook.py",
            use_absolute=True,
            verbose=verbose,
        )

    return g_counts


def main():
    parser = argparse.ArgumentParser(description="Swarm Nexus: Sync Active Harnesses (Claude, AGY, Codex)")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument(
        "--global-sync",
        action="store_true",
        default=True,
        help="Synchronize ~/.claude and ~/.gemini/config global spokes (default: True)",
    )
    parser.add_argument("actions", nargs="*", help="Optional actions (e.g. status)")
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.absolute()
    os.chdir(repo_root)

    # Clean stray non-skill artifacts in .agent/skills/ (e.g. sed temp files or empty dirs without SKILL.md)
    if SKILL_SOURCE.exists():
        for item in list(SKILL_SOURCE.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_file() and item.name.startswith("sed"):
                item.unlink()
            elif item.is_dir() and not (item / "SKILL.md").exists():
                shutil.rmtree(item)

    local_dirs = [Path(p) for p in LOCAL_AGENT_SPOKES + LOCAL_SKILL_SPOKES + LOCAL_POLICY_SPOKES + LOCAL_HOOK_SPOKES]
    local_dirs.extend([Path(".claude"), Path(".agents"), Path(".github")])
    cleanup_broken_links(local_dirs, verbose=args.verbose)

    counts = {"skills": 0, "agents": 0, "policies": 0, "hooks": 0}

    # 1. Sync Skills to active local spokes (only directories containing SKILL.md)
    valid_skills = []
    if SKILL_SOURCE.exists():
        valid_skills = sorted(
            [
                d
                for d in SKILL_SOURCE.iterdir()
                if d.is_dir() and not d.name.startswith(".") and (d / "SKILL.md").is_file()
            ]
        )
        valid_names = {d.name for d in valid_skills}
        for spoke in LOCAL_SKILL_SPOKES:
            spoke_path = Path(spoke)
            if spoke_path.is_dir():
                for existing in list(spoke_path.iterdir()):
                    if existing.is_symlink() and existing.name not in valid_names:
                        existing.unlink()
        for skill_item in valid_skills:
            success = False
            for spoke in LOCAL_SKILL_SPOKES:
                if create_symlink(skill_item, Path(spoke) / skill_item.name, verbose=args.verbose):
                    success = True
            if success:
                counts["skills"] += 1

    # 2. Sync Hydrated Agents to .github/agents
    if CLAUDE_HYDRATED_AGENTS.is_dir():
        for md_agent in sorted(CLAUDE_HYDRATED_AGENTS.glob("*.md")):
            for spoke in LOCAL_AGENT_SPOKES:
                if create_symlink(md_agent, Path(spoke) / md_agent.name, verbose=args.verbose):
                    counts["agents"] += 1

    # 3. Sync Policies
    if POLICY_SOURCE.exists():
        for policy_file in sorted(POLICY_SOURCE.iterdir()):
            if policy_file.suffix in [".toml", ".yaml", ".md"]:
                success = False
                for spoke in LOCAL_POLICY_SPOKES:
                    if create_symlink(policy_file, Path(spoke) / policy_file.name, verbose=args.verbose):
                        success = True
                if success:
                    counts["policies"] += 1

    # 4. Sync Hooks
    if HOOK_SOURCE.exists():
        for hook_item in sorted(HOOK_SOURCE.iterdir()):
            if hook_item.name.startswith("."):
                continue
            success = False
            for spoke in LOCAL_HOOK_SPOKES:
                if create_symlink(hook_item, Path(spoke) / hook_item.name, verbose=args.verbose):
                    success = True
            if success:
                counts["hooks"] += 1

    # 5. Instruction Bridges (AGENTS.md -> .github/copilot-instructions.md)
    for source_rel, targets in ROOT_LINKS.items():
        source = Path(source_rel)
        for target_rel in targets:
            create_symlink(source, Path(target_rel), verbose=args.verbose)

    # 6. Configurations
    for config_file_name, targets in CONFIG_LINKS.items():
        config_file = Path(".agent") / config_file_name
        if config_file.exists():
            for target in targets:
                create_symlink(config_file, Path(target), verbose=args.verbose)

    # 7. Global Harness Sync (~/.claude & ~/.gemini/config)
    g_counts = {"global_skills": 0, "global_agents": 0}
    if args.global_sync:
        g_counts = sync_global_harnesses(repo_root, valid_skills, verbose=args.verbose)

    print(
        f"Nexus Sync: {counts['skills']} local skills, {counts['agents']} local agent links, "
        f"{counts['policies']} policies, {counts['hooks']} hooks | "
        f"Global: {g_counts['global_skills']} skills, {g_counts['global_agents']} agents "
        f"active across [.claude, .agents, .github, ~/.claude, ~/.gemini/config]"
    )


if __name__ == "__main__":
    main()
