#!/usr/bin/env python3
"""
🏛️ SWARM NEXUS: Multi-Platform Symlink Engine
Codifies the relationship between core agents/skills and AI tool configurations.
Ensures parity across Gemini, Claude, Cursor, and Copilot.
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

# --- Configuration: The Factory Manifest ---
# Maps Tool Directories to their required Source Folders
# This manifest manages the FACTORY FLOOR tools. Standalone products
# (in projects/) manage their own internal parity.
NEXUS_MANIFEST = {
    # Expert Factory Agents (Factory Floor)
    "agents/aws-expert": [".claude/agents/aws-expert", ".copilot/agents/aws-expert", ".gemini/agents/aws-expert", ".cursor/agents/aws-expert"],
    "agents/k8s-expert": [".claude/agents/k8s-expert", ".copilot/agents/k8s-expert", ".gemini/agents/k8s-expert", ".cursor/agents/k8s-expert"],
    "agents/swarm-architect": [".claude/agents/swarm-architect", ".copilot/agents/swarm-architect", ".gemini/agents/swarm-architect", ".cursor/agents/swarm-architect"],
    "agents/swarm-engineer": [".claude/agents/swarm-engineer", ".copilot/agents/swarm-engineer", ".gemini/agents/swarm-engineer", ".cursor/agents/swarm-engineer"],
}

# Standalone Links (Single Files)
STANDALONE_LINKS = {
    "CLAUDE.md": "AGENT.md",
    "GEMINI.md": "AGENT.md",
    ".github/copilot-instructions.md": "AGENT.md",
}

class Nexus:
    def __init__(self, root_dir: Path, dry_run: bool = False, migrate: bool = False):
        self.root = root_dir
        self.dry_run = dry_run
        self.migrate = migrate
        self.stats = {"installed": 0, "verified": 0, "broken": 0, "unmanaged": 0}

    def log(self, msg: str):
        prefix = "[DRY-RUN] " if self.dry_run else ""
        print(f"{prefix}{msg}")

    def status(self):
        """MAINTENANCE: Check the health of the Elite Factory and its products."""
        print(f"[FACTORY FLOOR] Status: OPERATIONAL | Conductor: v2.0")
        print(f"[GOVERNANCE] Blueprint: [product_blueprint.md](file://../skills/product_blueprint.md)")
        print(f"[GOVERNANCE] Protocols: [AGENT.md](file://../AGENT.md) (TDD-FIRST IS THE LAW)")

    def install(self):
        self.log("🚀 Initializing Swarm Nexus...")
        
        # 1. Process Directory Manifest
        for target_rel, source_rel in NEXUS_MANIFEST.items():
            target_dir = self.root / target_rel
            source_dir = self.root / source_rel
            
            if not source_dir.exists():
                self.log(f"⚠️ Source missing: {source_rel}")
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
                self.log(f"⚠️ Source file missing: {source_rel}")
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            self._create_symlink(source, dest)

        self.log(f"✅ Nexus synchronized. Stats: {self.stats['installed']} installed.")

    def _create_symlink(self, source: Path, dest: Path):
        # Calculate relative path from dest to source
        try:
            rel_source = os.path.relpath(source, dest.parent)
        except ValueError:
            rel_source = str(source.absolute())

        if dest.is_symlink():
            if dest.exists() and os.readlink(dest) == rel_source:
                return # Already correct
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
                self.log(f"❌ Target exists and is NOT a symlink: {dest.relative_to(self.root)}")
                self.stats["unmanaged"] += 1
                return

        if not self.dry_run:
            dest.symlink_to(rel_source)
            self.stats["installed"] += 1
        else:
            self.log(f"🔗 Would link {dest.relative_to(self.root)} -> {rel_source}")

    def verify(self):
        self.log("🔍 Verifying Nexus Integrity...")
        for target_rel in NEXUS_MANIFEST.keys():
            target_dir = self.root / target_rel
            if not target_dir.exists():
                continue
            
            for item in target_dir.iterdir():
                if not item.is_symlink():
                    self.log(f"🚨 UNMANAGED FILE: {item.relative_to(self.root)}")
                    self.stats["unmanaged"] += 1
                elif not item.exists():
                    self.log(f"💔 BROKEN LINK: {item.relative_to(self.root)}")
                    self.stats["broken"] += 1
                else:
                    self.stats["verified"] += 1

        print(f"\nAudit Results: {self.stats['verified']} verified, {self.stats['broken']} broken, {self.stats['unmanaged']} unmanaged.")
        if self.stats["broken"] > 0 or self.stats["unmanaged"] > 0:
            sys.exit(1)

if __name__ == "__main__":
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
        nexus.verify()
