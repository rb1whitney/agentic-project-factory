#!/usr/bin/env python3
"""
🏛️ SWARM NEXUS: Multi-Platform Symlink Engine
Codifies the relationship between core agents/skills and AI tool configurations.
Ensures parity across Gemini, Claude, Cursor, and Copilot.
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("nexus")

# --- Configuration: The Factory Manifest ---
# Maps Tool Directories to their required Source Folders
# This manifest manages the FACTORY FLOOR tools. Standalone products
# (in projects/) manage their own internal parity.
NEXUS_MANIFEST: Dict[str, list[str]] = {
    # Expert Factory Agents (Directory-based adapters for Claude/Gemini/Copilot)
    "agents/aws-expert": [".claude/agents/aws-expert", ".copilot/agents/aws-expert", ".gemini/agents/aws-expert"],
    "agents/k8s-expert": [".claude/agents/k8s-expert", ".copilot/agents/k8s-expert", ".gemini/agents/k8s-expert"],
    "agents/swarm-architect": [
        ".claude/agents/swarm-architect",
        ".copilot/agents/swarm-architect",
        ".gemini/agents/swarm-architect",
    ],
    "agents/swarm-engineer": [
        ".claude/agents/swarm-engineer",
        ".copilot/agents/swarm-engineer",
        ".gemini/agents/swarm-engineer",
    ],
}

# Standalone Links (Single Files)
# This includes general IDE files and the NEW FLATTENED Cursor Rule standard.
STANDALONE_LINKS: Dict[str, str] = {
    "CLAUDE.md": "AGENT.md",
    "GEMINI.md": "AGENT.md",
    ".github/copilot-instructions.md": "AGENT.md",
    # Flattened Cursor Rule standard
    ".cursor/rules/aws-expert.md": "agents/aws-expert/SYSTEM.md",
    ".cursor/rules/gcp-expert.md": "agents/gcp-expert/SYSTEM.md",
    ".cursor/rules/github-specialist.md": "agents/github-specialist/SYSTEM.md",
    ".cursor/rules/k8s-expert.md": "agents/k8s-expert/SYSTEM.md",
    ".cursor/rules/security-reviewer.md": "agents/security-reviewer/SYSTEM.md",
    ".cursor/rules/sre-expert.md": "agents/sre-expert/SYSTEM.md",
    ".cursor/rules/swarm-architect.md": "agents/swarm-architect/SYSTEM.md",
    ".cursor/rules/swarm-auditor.md": "agents/swarm-auditor/SYSTEM.md",
    ".cursor/rules/swarm-engineer.md": "agents/swarm-engineer/SYSTEM.md",
    ".cursor/rules/swarm-msbuild.md": "agents/swarm-msbuild/SYSTEM.md",
    ".cursor/rules/swarm-supervisor.md": "agents/swarm-supervisor/SYSTEM.md",
    ".cursor/rules/terraform-expert.md": "agents/terraform-expert/SYSTEM.md",
}


class Nexus:
    def __init__(self, root_dir: Path, dry_run: bool = False, migrate: bool = False) -> None:
        self.root: Path = root_dir
        self.dry_run: bool = dry_run
        self.migrate: bool = migrate
        self.stats: Dict[str, int] = {"installed": 0, "verified": 0, "broken": 0, "unmanaged": 0}

    def log(self, msg: str, level: int = logging.INFO) -> None:
        prefix = "[DRY-RUN] " if self.dry_run else ""
        logger.log(level, f"{prefix}{msg}")

    def status(self) -> None:
        """MAINTENANCE: Check the health of theFactory and its products."""
        self.log("[FACTORY FLOOR] Status: OPERATIONAL | Conductor: v2.0")
        self.log("[GOVERNANCE] Blueprint: [product_blueprint.md](file://../skills/product_blueprint.md)")
        self.log("[GOVERNANCE] Protocols: [AGENT.md](file://../AGENT.md) (TDD-FIRST IS THE LAW)")

    def install(self) -> None:
        self.log("🚀 Initializing Swarm Nexus...")

        # 1. Process Directory Manifest
        for target_rel, source_list in NEXUS_MANIFEST.items():
            target_dir = self.root / target_rel
            for source_rel in source_list:
                source_dir = self.root / source_rel

                if not source_dir.exists():
                    self.log(f"⚠️ Source missing: {source_rel}", logging.WARNING)
                    continue

                target_dir.mkdir(parents=True, exist_ok=True)

                # Link every child in source to target
                for item in source_dir.iterdir():
                    dest = target_dir / item.name
                    self._create_symlink(item, dest)

        # 2. Process Standalone Links
        for target_rel, source_rel in STANDALONE_LINKS.items():
            source = self.root / source_rel
            dest = self.root / target_rel

            if not source.exists():
                self.log(f"⚠️ Source file missing: {source_rel}", logging.WARNING)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            self._create_symlink(source, dest)

        self.log(f"✅ Nexus synchronized. Stats: {self.stats['installed']} installed.")

    def _create_symlink(self, source: Path, dest: Path) -> None:
        # Calculate relative path from dest to source
        try:
            rel_source = os.path.relpath(source, dest.parent)
        except ValueError:
            rel_source = str(source.absolute())

        if dest.is_symlink():
            if dest.exists() and os.readlink(dest) == rel_source:
                return  # Already correct
            if not self.dry_run:
                dest.unlink()

        if dest.exists() and not dest.is_symlink():
            if self.migrate:
                self.log(f"♻️ Migrating unmanaged configuration: {dest.relative_to(self.root)}")
                if not self.dry_run:
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
            else:
                self.log(f"❌ Target exists and is NOT a symlink: {dest.relative_to(self.root)}", logging.ERROR)
                self.stats["unmanaged"] += 1
                return

        if not self.dry_run:
            dest.symlink_to(rel_source)
            self.stats["installed"] += 1
        else:
            self.log(f"🔗 Would link {dest.relative_to(self.root)} -> {rel_source}")

    def verify(self) -> None:
        self.log("🔍 Verifying Nexus Integrity...")
        for target_rel in NEXUS_MANIFEST.keys():
            target_dir = self.root / target_rel
            if not target_dir.exists():
                continue

            for item in target_dir.iterdir():
                if not item.is_symlink():
                    self.log(f"🚨 UNMANAGED FILE: {item.relative_to(self.root)}", logging.ERROR)
                    self.stats["unmanaged"] += 1
                elif not item.exists():
                    self.log(f"💔 BROKEN LINK: {item.relative_to(self.root)}", logging.ERROR)
                    self.stats["broken"] += 1
                else:
                    self.stats["verified"] += 1

        self.log(
            f"Audit Results: {self.stats['verified']} verified, {self.stats['broken']} broken, "
            f"{self.stats['unmanaged']} unmanaged."
        )
        if self.stats["unmanaged"] > 0:
            sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Swarm Nexus Manager")
    parser.add_argument("action", choices=["install", "verify", "health"], help="Action to perform")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without executing")
    parser.add_argument("--migrate", action="store_true", help="Convert unmanaged files to symlinks")
    args = parser.parse_args()

    # Move to repo root
    repo_root = Path(__file__).parent.parent.absolute()
    nexus = Nexus(repo_root, dry_run=args.dry_run, migrate=args.migrate)

    if args.action == "install":
        nexus.install()
    elif args.action in ["verify", "health"]:
        if args.action == "health":
            nexus.status()
        nexus.verify()


if __name__ == "__main__":
    main()
