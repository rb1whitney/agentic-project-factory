# Ephemeral Projection Adapter Pattern & Factory Compiler Architecture

## 1. Executive Summary
Proprietary LLM harnesses (such as Claude Code, Antigravity `agy`, and OpenAI/Copilot) enforce divergent agent configurations, frontmatter formats, and tool name validations. Authoring vendor-specific files directly results in **configuration drift**, **metadata pollution**, and **fatal schema validation errors**.

The **Ephemeral Projection Adapter Pattern** enforces a strict separation:
1. **Canonical Authoring Hub**: Pure multi-adapter YAML specifications in `.agent/agents/*.yaml`.
2. **Synchronous Hydration Engine**: `scripts/hydrate.sh` compiles canonical specifications into ephemeral dotfiles on demand.
3. **Canonical Metadata Cache**: `bin/compile_metadata.py` scans only standard locations, emitting `.agent/metadata.json`.
4. **Lifecycle Autoload Webhook**: `bin/autoload_webhook.py` auto-hydrates agents and recompiles metadata upon session initialization.
5. **Automated Discovery Verification**: `bin/verify_runtime_discovery.py` confirms 100% schema integrity across all harnesses before execution.
6. **Factory Cleanup**: `bin/factory_clean.sh` wipes ephemeral projections and dead vendor folders cleanly.

---

## 2. Directory Architecture

```text
Programming-Work/
├── .agent/
│   ├── agents/                  # Canonical authoring hub (Multi-adapter YAML + Prompts)
│   │   ├── db-migration.yaml
│   │   ├── memory-agent.yaml
│   │   ├── specialist-aws.yaml
│   │   └── ...
│   ├── skills/                  # Centralized industrial skills repository
│   ├── policies/                # Factory RBAC and safety policies
│   ├── hooks/                   # System lifecycle hooks
│   └── metadata.json            # Compiled canonical catalog of agents and skills
├── .claude/                     # Ephemeral projection: Claude Code dot directory
│   ├── agents/                  # Markdown + Claude frontmatter
│   ├── settings.json            # Claude hooks configuration
│   └── skills/                  # Symlink to .agent/skills
├── .agents/                     # Ephemeral projection: Antigravity CLI (agy)
│   ├── *.json                   # Native Antigravity agent JSON specifications
│   ├── hooks.json               # Antigravity lifecycle hooks
│   └── skills/                  # Symlink to .agent/skills
├── .github/                     # Codex / Copilot instructions and workflows
│   ├── copilot-instructions.md  # Symlink to AGENTS.md
│   └── workflows/
├── scripts/
│   └── hydrate.sh               # Synchronous compiler bridge
└── bin/
    ├── compile_metadata.py      # Fast metadata compiler
    ├── autoload_webhook.py      # Pre-invocation auto-hydration webhook
    ├── factory_clean.sh         # Purge ephemeral files and dead directories
    ├── nexus.sh                 # Orchestrated runner (compiles -> hydrates -> syncs)
    ├── nexus.py                 # Multi-platform symlink synchronization (v3.0)
    └── verify_runtime_discovery.py # Discovery audit & schema validation test suite
```

---

## 3. Schema & Compilation Specification

### Canonical Source (.agent/agents/<agent>.yaml)
```yaml
version: 1.0
name: specialist-aws
description: "Domain Specialist Subagent. Use for: AWS Infrastructure, S3, IAM, VPC networking, CloudFormation."
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
# AWS Strategic Design Authority
Markdown instructions...
```

### Projected Claude File (.claude/agents/specialist-aws.md)
```markdown
---
name: specialist-aws
description: "Domain Specialist Subagent. Use for: AWS Infrastructure, S3, IAM, VPC networking, CloudFormation."
model: sonnet
permissionMode: plan-first
tools: [Read, Glob, Grep, Bash]
disallowedTools: [Task]
---
# AWS Strategic Design Authority
Markdown instructions...
```

### Projected Antigravity File (.agents/specialist-aws.json)
```json
{
  "name": "specialist-aws",
  "description": "Domain Specialist Subagent. Use for: AWS Infrastructure, S3, IAM, VPC networking, CloudFormation.",
  "model": "flash",
  "subagent": true,
  "commandExecutionPolicy": "sandbox",
  "tools": [
    "view_file",
    "grep_search",
    "run_command",
    "list_dir"
  ],
  "auto_approve": [
    "view_file",
    "grep_search"
  ]
}
```

---

## 4. Verification & Continuous Integration
Run the verification suite at any time:
```bash
python3 bin/verify_runtime_discovery.py
```
This validates that:
- Every `.claude/agents/*.md` file has valid YAML frontmatter containing required keys (`name`, `model`, `tools`).
- Every `.agents/*.json` agent file parses as valid JSON with required runtime keys (`name`, `model`, `tools`).
- Standard skill counts and canonical agent counts match the centralized catalog.
