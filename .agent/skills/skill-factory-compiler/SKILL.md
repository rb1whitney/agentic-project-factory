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

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: factory-hydration-compiler] parent=skill-factory-compiler required_inputs=['harness_target', 'repo_root']
./scripts/hydrate.sh {harness_target} | bin/rtk
./scripts/hydrate.sh models | bin/rtk
python3 bin/compile_metadata.py --repo-root {repo_root} --output .agent/metadata.json | bin/rtk
python3 bin/verify_runtime_discovery.py | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_factory_compiler_workflow(harness_target, repo_root):
  1. PRE-CHECK: Canonical sources in .agent/agents/*.yaml and .agent/skills/*/SKILL.md; Physical Sovereignty enforced
  2. result <- invoke(factory-hydration-compiler, {harness_target: "<harness_target>", repo_root: "<repo_root>"})
  3. POST-CHECK: 1:1 reconciliation across Claude, Antigravity, and Codex projections
  4. RETURN {Location, Problem, Fix, outputs: ['metadata_path', 'discovery_status', 'reconciled_count']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: factory-hydration-compiler`**
  - `trigger`: Hydrate canonical multi-adapter YAML agents, sync Nexus spokes, verify model tiers, and certify runtime discovery
  - `inputs`: required `['harness_target', 'repo_root']`, optional `['write_models']`
  - `outputs`: `['metadata_path', 'discovery_status', 'reconciled_count']`
  - `preconditions`: Canonical sources in .agent/agents/*.yaml and .agent/skills/*/SKILL.md; Physical Sovereignty enforced
  - `postconditions`: 1:1 reconciliation across Claude, Antigravity, and Codex projections
  - `side_effects`: filesystem=writes .claude/, .agents/, .codex/, .agent/metadata.json, network=none

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (5)**: `scripts/__init__.py`, `scripts/logic.py`, `scripts/scanner.py`, `scripts/templates/AGENT.md`, `scripts/tool.json`
- **Reference Runbooks (5)**: `references/agentic-initializer.md`, `references/harness-models.md`, `references/nexus-sync.md`, `references/vercel-agents-md.md`, `references/webhook-autoload.md`
<!-- SAP_BUNDLE_END -->

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
