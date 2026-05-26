# Specification: Institutionalizing the 2026 Agentic Hub and Discovery Standards

## Overview
This track formalizes the industrial-grade agentic infrastructure for the repository. By April 2026, the proliferation of specialized AI agents (Google Antigravity, Claude Code, GitHub Copilot, Cursor) created significant configuration drift and context fragmentation. This mission establishes a centralized, high-precision **Agentic Hub** (`.agent/`) that serves as the single physical source of truth for all specialist personas, skills, and governance policies, while utilizing a "Hub and Spoke" symlink architecture to maintain 100% discoverability across legacy and modern toolchains.

## Functional Requirements
- **ACS v1.2.0 Implementation**: Configure the Agentic Collaboration Standard (ACS) to manage tiered context ingestion.
    - **Tier-1**: Names-only discovery for roles and skills.
    - **Tier-2**: On-demand, intent-matched ingestion for full logic and instructions.
- **Unified Manifest (v1.8.0)**: Centralize project identity and provider permissions in `.agent/manifest.json`.
- **The "Hub and Spoke" Discovery Architecture**:
    - Establish root-level and `.github/` symlinks that "poly-fill" legacy vendor paths.
    - Ensure `.cursorrules`, `CLAUDE.md`, and `.github/copilot-instructions.md` all redirect to the centralized hub.
    - Implement support for modern Cursor **`.mdc`** (Markdown Component) rules in `.cursor/rules/`.
- **2026 Model Suite Alignment**:
    - Explicitly configure support for **Gemini 3.1 Pro** and **Claude 4.6 (Sonnet)**.
    - Enforce the mandatory **"Thinking Block"** mandate for cognitive reflection.
- **Lethal Trifecta Safety Protocols**:
    - Implement **`safety.toml`** for network and tool egress governance.
    - Implement **`privacy.toml`** for data sovereignty and credential redaction.
    - Implement **`governance.toml`** for swarm-level resource management.
- **Deterministic Lifecycle Hooks**:
    - Configure `session_start.json` for automated AST symbol mapping.
    - Configure `pre_tool_use.json` for real-time policy enforcement and permission checks.

## Non-Functional Requirements
- **Physical Sovereignty**: The `.agent/` directory must remain a physical directory (not a symlink) to ensure the repository remains standalone and portable.
- **Zero Duplication**: Eliminate all redundant instruction files; any vendor-specific lookup must be handled via redirection to the Hub.
- **Deterministic Discovery**: The infrastructure must be "Zero-Config" for any ACS-compliant or legacy vendor tool.
- **Security**: Prohibit any "Self-Sabotage" loops where agents can mutate their own core personas or safety policies.

## Acceptance Criteria
- [x] The `.agent/` hub is the physical source of truth for all experts and skills.
- [x] All legacy vendor files (`.cursorrules`, `CLAUDE.md`, etc.) are symlinks pointing to the Hub.
- [x] `manifest.json` correctly specifies `schema_version: "1.8.0"` and the 2026 model suite.
- [x] `acs.yaml` is configured with `mode: "on-demand"` for Tier-2 ingestion to prevent context drift.
- [x] The `docs/agent-infrastructure-discovery.md` is verified against real-world 2026 tool specs.
- [x] The "Lethal Trifecta" policies are active and verified by the `preToolUse` hook.

## Out of Scope
- Architectural refactoring of the underlying application logic.
- Deprecating support for legacy IDEs (this standard focuses on interoperability).
- Management of secrets outside the established `gopass` / `rbw` / `~/.mcp-servers/` standards.
