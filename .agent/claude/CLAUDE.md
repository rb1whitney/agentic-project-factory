# Project Context: Agentic-Project-Factory

## Purpose
Unified AI Agent and Skills hub following the Unified Agentic Standard (UAS).

## Essential Commands
- **Sync Skills**: `python3 bin/nexus.py sync`
- **Rebuild Map**: `python3 tools/ast-bridge/code_mapper.py .`
- **Safety Audit**: `bash .agent/hooks/audit_stubs.sh`
- **Scaffold Project**: `bash bin/setup.sh`

## Coding Conventions
- **Dialect**: Always use `caveman-prose` (No articles, no pleasantries).
- **Style**: Direct, technical, and concise.
- **Edits**: Use `strict-patch` (surgical line-number replacements).
- **Patterns**: Domain-Driven Design (7-phase Strategic-to-Tactical workflow).
- **Infrastructure**: Terraform for IaC; shell scripts for lifecycle hooks.

## Testing & Quality
- **Success Criteria**: Define tests in `tests/` before implementation (TDD).
- **Validation**: Run `bin/audit_stubs.sh` post-implementation.
- **Verification**: Use `.agent/scenarios/` for runtime benchmarks.

## Project Structure
- `.agent/`: UNIFIED HUB (agents, skills, policies, hooks).
- `conductor/`: Project lifecycle orchestrator (product, tech-stack, tracks).
- `bin/`: CLI binaries and core synchronization scripts.
- `docs/`: Repository architecture and standards.
