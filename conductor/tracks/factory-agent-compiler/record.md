# Mission Record: Factory Agent Compiler

## Timeline
- **2026-09-19**: Track initialized.
- **2026-09-19**: Implemented Ephemeral Projection Adapter Pattern.
- **2026-09-19**: Created canonical agent repository in `.agent/canonical-agents/` with initial `db-migration.yaml`.
- **2026-09-19**: Created synchronous hydration engine `scripts/hydrate.sh` with strict fail-fast validation.
- **2026-09-19**: Verified compilation:
  - Claude target -> `.claude/agents/db-migration.md`
  - Antigravity target -> `.agents/db-migration.json`
- **2026-09-19**: Verified negative testing (fail-fast on missing keys).

- **2026-09-19**: Created `bin/compile_metadata.py` to recompile metadata indexes from standard source locations only (.agent/agents, .agent/skills, .agent/canonical-agents), bypassing non-canonical placement.
- **2026-09-19**: Created `bin/nexus.sh` orchestrator integrating metadata recompilation ahead of nexus sync.

- **2026-09-19**: Migrated all factory agents to canonical schema in `.agent/canonical-agents/*.yaml` (16 canonical agents) with dual Claude and Antigravity adapter blocks.
- **2026-09-19**: Hydrated all 16 canonical agents to `.claude/agents/*.md` and `.agents/*.json`.
- **2026-09-19**: Recompiled `.agent/metadata.json` across all standard agents, canonical agents, and 50 standard skills.

- **2026-09-19**: Created `bin/verify_runtime_discovery.py` to audit and demonstrate that projected agents and skills load correctly for Claude Code and Antigravity (agy). Verified 16/16 agents and 50/50 skills pass validation.

- **2026-09-19**: Updated `AGENTS.md` with Section 0.2 defining the Ephemeral Projection & Compiler Protocol.
- **2026-09-19**: Created dedicated skill in `.agent/skills/skill-factory-compiler/SKILL.md`.
- **2026-09-19**: Implemented adapter webhook autoload engine:
  - Runner: `bin/autoload_webhook.py`
  - Antigravity hook: `.agents/hooks.json` (`PreInvocation`)
  - Claude hook: `.claude/settings.json` (`SessionStart`)
  - Autoload skill: `.agent/skills/skill-webhook-autoload/SKILL.md`
  - Test suite: `tests/test_agent_webhook_autoload.py` demonstrating zero-touch autoload of `db-migration`, `specialist-aws`, and `memory-agent` across Claude and Antigravity.

- **2026-09-19**: Folded `.agent/canonical-agents/` into `.agent/agents/` as the single canonical source of truth.
  - Eliminated duplicate `.agent/canonical-agents/` directory.
  - Updated `scripts/hydrate.sh`, `bin/compile_metadata.py`, `bin/nexus.sh`, and `bin/autoload_webhook.py` to read directly from `.agent/agents/*.yaml`.
  - Re-verified runtime discovery and webhook tests (16/16 agents, 52 skills passed).

- **2026-09-19**: Decommissioned dead vendor spokes (`.gemini/`, `.antigravitycli/`, `.copilot/`, `.opencode/`).
- **2026-09-19**: Created `bin/factory_clean.sh` to purge ephemeral projections while leaving `.agent/` master untouched.
- **2026-09-19**: Hydrated repository documentation in `docs/`:
  - Updated `docs/ephemeral-projection-compiler.md` with unified `.agent/agents/*.yaml` architecture.
- **2026-09-19**: Authored `CLAUDE_INFO.md` at repository root defining compiler architecture, operational workflows, and instructions to make Codex/Copilot fully functional.

## Active Decisions
- [x] **Canonical Source Purity**: Raw harness-specific frontmatter banned from `.agent/agents/`.
- [x] **Single Canonical Directory**: Folded `.agent/canonical-agents` into `.agent/agents/` to eliminate duplicate definitions and code debt.
- [x] **Exact Property Mapping**: `yq` merges canonical metadata and target adapter blocks cleanly.
- [x] **Pre-Flight Integrity**: Zero guessing or default fallbacks; missing required keys abort execution.
- [x] **Standard Location Extraction**: Metadata recompilation reads strictly from canonical source hubs (`.agent/`), ignoring scattered vendor drop-in points.
- [x] **Full Factory Parity**: All 16 primary agents mapped and compiled.
- [x] **Automated Harness Audit**: `bin/verify_runtime_discovery.py` certifies zero drift across both harness dotfile projections.
- [x] **Standard Protocol Codification**: Section 0.2 integrated into `AGENTS.md` and indexed in `.agent/skills/`.
- [x] **Zero-Touch Adapter Webhooks**: Integrated `PreInvocation` and `SessionStart` hooks to auto-hydrate and compile metadata.
- [x] **Sprawl Eradication**: Legacy dead directories deleted; ephemeral directories isolated to `.claude/`, `.agents/`, `.github/`.
- [x] **Documentation Hydration**: Purged all stale CLI and path references from `docs/`.
- [x] **Codex Bridge**: Codified Codex `.github/` instruction and skill bridge in `CLAUDE_INFO.md`.

## Current State
- `canonical-agents`: `.agent/agents/*.yaml` [16 CANONICAL SCHEMAS]
- `hydrate script`: `scripts/hydrate.sh` [EXECUTABLE & VERIFIED ACROSS ALL 16 AGENTS]
- `metadata compiler`: `bin/compile_metadata.py` [ACTIVE -> `.agent/metadata.json`]
- `clean engine`: `bin/factory_clean.sh` [EXECUTABLE & VERIFIED]
- `targeted nexus`: `bin/nexus.py` (v3.0) & `bin/nexus.sh` [FOCUSED ON .agents, .claude, .github]
- `autoload webhook`: `bin/autoload_webhook.py` [ACTIVE -> `.agents/hooks.json` & `.claude/settings.json`]
- `verification tests`: `tests/test_agent_webhook_autoload.py` [PASSED]
- `documentation`: `docs/ephemeral-projection-compiler.md` & `CLAUDE_INFO.md` [HYDRATED & PRISTINE]
- `conductor track`: `conductor/tracks/factory-agent-compiler/` [COMPLETE]
- Status: [COMPLETE] | [CERTIFIED]
