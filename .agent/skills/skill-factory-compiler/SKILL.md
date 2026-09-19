---
name: skill-factory-compiler
description: Factory agent compiler and hydration engine. Translates canonical multi-adapter agent schemas into runtime dotfiles (.claude/agents/, .agents/) and recompiles standard metadata without drift.
auto_triggers:
  - "hydrate"
  - "compile agents"
  - "compile metadata"
  - "verify discovery"
  - "agent projection"
---

# Factory Agent Compiler (Ephemeral Projection Pattern)

## Overview
The Factory Agent Compiler decouples agent definitions from vendor harness parsers (Claude Code, Antigravity `agy`, OpenAI/Copilot). Source definitions live exclusively in `.agent/canonical-agents/*.yaml` with separate adapter blocks and markdown instruction bodies.

## Canonical Schema Anatomy
Location: `.agent/canonical-agents/<agent-name>.yaml`

```yaml
version: 1.0
name: <agent-name>
description: "<agent-description>"
adapter:
  claude:
    model: sonnet
    permissionMode: plan-first
    tools: [Read, Glob, Grep, Bash]
    disallowedTools: [Task]
  antigravity:
    model: flash
    subagent: true
    commandExecutionPolicy: sandbox
    tools: [view_file, grep_search, run_command, list_dir]
    auto_approve: ["view_file", "grep_search"]
---
# Agent System Instructions
Markdown prompt content here.
```

## Standard Commands

### 1. Hydrate Projections (Synchronous Build)
Compile canonical agents into runtime dotfiles:
```bash
# Hydrate Claude Code markdown frontmatter
./scripts/hydrate.sh claude

# Hydrate Antigravity JSON agent specifications
./scripts/hydrate.sh antigravity
```

### 2. Recompile Standard Metadata
Index agents and skills strictly from standard canonical directories (`.agent/agents`, `.agent/skills`, `.agent/canonical-agents`):
```bash
python3 bin/compile_metadata.py --repo-root . --output .agent/metadata.json
```

### 3. Orchestrated Nexus Sync
Recompile metadata pre-flight and synchronize symlinks across all spokes:
```bash
bash bin/nexus.sh
```

### 4. Verify Runtime Discovery
Run pre-flight discovery audit to verify 100% schema validity and zero syntax drift:
```bash
python3 bin/verify_runtime_discovery.py
```

## Guardrails
- **Zero Harness Frontmatter in Source**: Never write vendor-specific frontmatter directly into `.agent/canonical-agents/`.
- **Fail Fast**: Hydration aborts immediately on missing required adapter fields. No fallback guessing permitted.
- **Single Source of Truth**: Always edit `.agent/canonical-agents/*.yaml` rather than ephemeral dotfiles.
