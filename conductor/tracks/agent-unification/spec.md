# Mission: Agentic Standard Unification (.agent)

## Infrastructure Overview
**Mission Status**: [ACTIVE]
**Target**: Unified Repository Context Standard
**Standard**: Agentic Collaboration Standard (ACS) v1.0

## Manufacturing Goals
1. **Core Relocation**: Migrate `agents/` and `skills/` to `.agent/` hub.
2. **Symlink Purge**: Remove all legacy symbolic links (`agents`, `skills`) within vendor-specific hubs.
3. **Legacy Consolidation**: Decommission `.gemini`, `.claude`, and `.copilot` hubs in favor of the unified `.agent/` directory.
4. **Protocol Update**: Transition `AGENT.md` to be the single source of truth for all agents.

## Technical Impact
- **Sovereignty**: Physical separation of core factory logic from root clutter.
- **discoverability**: New-generation agents (Gemini 2.0+, Claude Code) prioritize `.agent/` discovery.
- **Maintenance**: Elimination of relative-path symlink drift.

## Phase Mapping
1. **[RESEARCH]**: Identification of all tool-specific configuration requirements. [COMPLETED]
2. **[PREPARATION]**: Initialization of `.agent/` structure and mission tracking. [CURRENT]
3. **[EXECUTION]**: `git mv` of core components and symlink removal.
4. **[VALIDATION]**: Verification of cross-tool context retrieval via `AGENT.md`.
