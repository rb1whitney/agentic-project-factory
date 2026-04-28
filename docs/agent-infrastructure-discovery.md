# Agentic Infrastructure & Discovery Standard (2026)

This document formalizes the architecture, discovery logic, and precedence hierarchy for the agentic infrastructure established in April 2026.

## 1. Architectural Design: The Hub and Spoke Model

To resolve the conflict between **Logical Centralization** (one place for logic) and **Universal Discoverability** (multiple IDEs), this repository utilizes a "Hub and Spoke" pattern.

### Decision: The `.agent/` Hub
- **Rationale**: Centralizing all agent personas, skills, hooks, and policies into a single hidden directory prevents configuration drift across different AI providers.
- **Implementation**: The `.agent/` directory is the **Physical Source of Truth**. It must never be a symlink to an external location (Physical Sovereignty).

### Decision: The Spoke Symlinks
- **Rationale**: Legacy and modern IDEs (Cursor, Claude Code, Copilot) are hardcoded to look for specific vendor-locked filenames.
- **Implementation**: Root-level and `.github/` symlinks act as discovery "bridges" that redirect vendor-specific lookups to the unified hub.

| Entry Point | Target (Source of Truth) | Supported Tool | Status (2026) |
| :--- | :--- | :--- | :--- |
| `.agent/` | (Physical Directory) | Antigravity, ACS-Compliant Tools | **Standard** |
| `.cursor/rules/*.mdc` | `.agent/agents/` (Symlink) | Cursor (Modern) | **Primary** |
| `.cursor/index.mdc` | `AGENT.md` (Symlink) | Cursor (Modern) | **Primary** |
| `.cursorrules` | `AGENT.md` (Symlink) | Cursor (Legacy) | *Deprecated* |
| `CLAUDE.md` | `AGENT.md` (Symlink) | Claude Code | **Primary** |
| `./.claude/` | `.agent/` (Symlink) | Claude Code | **Primary** |
| `.github/copilot-instructions.md` | `AGENT.md` (Symlink) | GitHub Copilot | **Primary** |
| `.github/agents/*.agent.md` | `.agent/agents/` (Symlink) | Copilot Workspace | **Primary** |
| `.github/instructions/` | (Path-specific rules) | GitHub Copilot | **Advanced** |

---

## 2. Setting Precedence Hierarchy

The infrastructure supports a tiered configuration model. Verified 2026 discovery logic follows this path (Project > User > Org):

### Tier 1: Organizational (Global Guardrails)
- **Locations**: `/etc/agent/`, `/etc/gemini/`, `/etc/claude/`
- **Scope**: Mandatory safety policies (Lethal Trifecta), enterprise egress rules, and resource quotas.
- **Precedence**: Overridden by User/Project unless "Locked" by administrative policy.

### Tier 2: User (Global Personalization)
- **Locations**: 
  - **General**: `~/.agent/` (Universal personas and global skills)
  - **Claude**: `~/.claude/` (Global `settings.json`, session history)
  - **Claude Memory**: `~/.claude/projects/{project}/MEMORY.md` (Auto-memory logs)
  - **Copilot**: `~/.config/github-copilot/` (User-level instructions)
- **Scope**: Personal workflows, global specialized experts, and local credentials (`gopass`, `rbw`).
- **Precedence**: Overrides Org, overridden by Project.

### Tier 3: Project (Repository Sovereignty)
- **Locations**: `.agent/` (in workspace root)
- **Scope**: 
  - **ACS**: `manifest.json`, `acs.yaml` (Tiered ingestion logic).
  - **Cursor**: `.cursor/rules/` (Using `.mdc` Markdown Component spec).
  - **Claude**: `CLAUDE.md` and `./.claude/` (Project-specific rules/commands).
  - **Copilot**: `.github/copilot-instructions.md` and `.github/agents/`.
- **Precedence**: **Highest**. Local project instructions always have the final mandate on implementation style and constraints.

---

## 3. Tool Support Matrix (April 2026)

| Tool | Native Support | ACS v1.2.0 Fallback | Rule Format |
| :--- | :--- | :--- | :--- |
| **Google Antigravity** | `.agent/` | Native | ACS JSON/YAML |
| **Claude Code (v4.6+)** | `CLAUDE.md` | Yes | Markdown / `@path` |
| **GitHub Copilot** | `.github/` | Yes | Markdown / Agents |
| **Cursor** | `.cursor/rules/`| No | `.mdc` (Frontmatter) |


---

## 4. Current State (Audit April 28, 2026)

- [x] **Centralized Hub**: All logic migrated to `.agent/`.
- [x] **Symlink Poly-fills**: Established for Cursor, Claude, and Copilot.
- [x] **Tiered Context**: `acs.yaml` configured for on-demand loading.
- [x] **Model Definition**: `manifest.json` updated to specify 2026 Model Suite (Gemini 3.1 Pro, Claude 4.6).
- [x] **Physical Sovereignty**: Verified that `.agent/` is a physical directory, not a link.

---
*Last Updated: 2026-04-28*
