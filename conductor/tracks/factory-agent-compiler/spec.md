# Specification: Ephemeral Projection Adapter Pattern & Factory Agent Compiler

## 1. Objective
Decouple agent source definitions from proprietary vendor parser requirements (Claude Code, Antigravity, Codex) to eliminate lethal tool metadata validation errors and schema drift.

## 2. Canonical Data Schema Specification
All agents must be authored as a single source of truth in `.agent/canonical-agents/<agent-name>.yaml`.

### Schema Anatomy
- **Metadata Block**: Universal agent name and human-readable description.
- **Adapter Block**: Mapped configuration keys segregated by target vendor engine (`claude`, `antigravity`).
- **Instruction Body**: Standard Markdown instruction set separated by standard YAML frontmatter boundaries (`---`).

## 3. Hydration Engine Specification (`scripts/hydrate.sh`)
The hydration engine acts as the synchronous compilation bridge. It projects canonical sources into target dotfiles at runtime.

### Execution Contract
- **Input**: Target engine identifier (`claude` | `antigravity`).
- **Action**: Read canonical YAML, parse metadata and target adapter keys via `yq`, project into target directories (`.claude/agents/` or `.agents/`), and append instruction markdown.
- **Failure State**: If a required vendor key is missing or malformed, exit non-zero (`exit 1`) immediately without fallback defaults.
