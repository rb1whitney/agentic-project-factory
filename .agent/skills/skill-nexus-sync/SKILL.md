---
name: skill-nexus-sync
description: Synchronizes expert agent and skill definitions across all AI platforms (Cursor, Claude, Gemini, Copilot).
auto_triggers:
  - "sync skills"
  - "sync agents"
  - "run nexus"
---

# Nexus Sync

This skill orchestrates the synchronization of the agentic hub across all integrated IDEs and AI tools.

## Usage

When you need to ensure that your agent definitions and skills are up-to-date across all platforms, trigger this skill by saying:
- "sync skills"
- "sync agents"

## Workflow

1. **Local Sync**: Run the Nexus engine to update project-local symlinks in `.cursor/rules`, `.claude/agents`, etc.
   ```bash
   python3 bin/nexus.py
   ```

2. **Global Sync (Optional)**: If you need to update your global user configurations in $HOME, run with the `--global-sync` flag.
   ```bash
   python3 bin/nexus.py --global-sync
   ```

3. **Validation**: Verify that the symlinks are correctly established.
   ```bash
   # Check Cursor rules
   ls -la .cursor/rules/
   ```

## Operating Principles
- **Physical Sovereignty**: Always treat `.agent/agents/` and `.agent/skills/` as the physical source of truth.
- **Parity**: Ensure all platforms receive the same definitions to prevent behavioral drift.
