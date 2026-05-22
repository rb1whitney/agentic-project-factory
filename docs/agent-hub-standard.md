# Agent Hub Standard (2026)

This document outlines the standard for the `.agent/` hub as of April 2026. This architecture ensures high-precision orchestration across multiple AI providers (Google Antigravity, Claude Code, GitHub Copilot) while maintaining strict safety and governance.

## 1. The Unified Manifest (v1.8.0)

The `.agent/manifest.json` is the entry point for all agents. It defines the project's identity, capabilities, and provider permissions.

### Key Fields:
- **`schema_version`**: Must be `1.8.0` for 2026 compliance.
- **`standard`**: `ACS-2026` ensures tool-agnostic context ingestion.
- **`permissions`**: Defines the "Opt-In" vs "Native" tiers for specific engines.

## 2. ACS v1.2.0: Tiered Context Loading

To prevent context drift and token saturation, the hub implements a three-tier ingestion strategy defined in `.agent/acs.yaml`.

| Tier | Description | Mode |
| :--- | :--- | :--- |
| **Tier-1** | Discovery (Role/Skill names) | `names-only` |
| **Tier-2** | Logical (Full Prompts/Logic) | `on-demand` (Intent-matched) |
| **Tier-3** | Deep Context (Specs/Logs) | `reference-only` |

## 3. Physical Sovereignty

The **April 2026 Shift** established that the `.agent/` directory is the **Physical Truth** for the repository's intelligence.
- **Zero-Delete Sanctity**: Core expert files (`.agent/agents/`) and skills (`.agent/skills/`) are immutable by the agents themselves to prevent "Self-Sabotage" loops.
- **IDE Portability**: Root-level symlinks (like `.cursorrules`) point into the hub, ensuring that switching from Cursor to Antigravity or Claude Code preserves the same expert context.

## 4. The Lethal Trifecta (Safety Policies)

Located in `.agent/policies/`, these machine-readable files govern agent behavior:
1. **`safety.toml`**: Restricts network egress (**Network Governance**) and prohibits destructive OS commands (**Tool Egress**) without human approval.
2. **`privacy.toml`**: Redacts sensitive files (secrets, personal data, .env) from agent context (**Data Sovereignty**).
3. **`governance.toml`**: Manages resource usage and cross-agent communication protocols.

## 5. Model-Specific Optimizations (April 2026)

Configurations in `.agent/providers/` (or `settings.json`) are optimized for:
- **Google Antigravity**: Primary engine is Gemini 3.1 Pro with native **Thinking Blocks** enabled.
- **Anthropic / Claude**: Optimized for Claude 4.6 (Sonnet/Opus) using **Deterministic Event Channels**.
- **Edge/Local**: Use **Nano Banana Pro 2** for lightweight, offline task triage and local file parsing.

## 6. Lifecycle Hooks

Deterministic event hooks in `.agent/hooks/` allow for precise orchestration:
- **`session_start.json`**: Pre-loads personas and regenerates symbol maps.
- **`pre_tool_use.json`**: Intercepts tool calls for policy validation.
- **`post_task.json`**: Triggers documentation updates and test runs automatically.

---
*Last Updated: April 2026*
