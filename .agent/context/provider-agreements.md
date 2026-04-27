# Provider Context Agreements (2026)

This repository opt-in to the following advanced context sharing standards for AI agents:

## GitHub / Copilot
- **Discovery**: Utilizes [`.agent/manifest.json`](file://./.agent/manifest.json) for capability mapping.
- **Protocol**: Mandates [**AGENT.md**](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/AGENT.md) for behavioral rules.

## Anthropic / Claude Code
- **Discovery**: Recognizes [**acs.yaml**](file://./.agent/acs.yaml) for tiered context loading.
- **Protocol**: Utilizes [`.agent/agents/`](file://./.agent/agents/) for expert system prompts.

## Google / Antigravity
- **Discovery**: Native integration via [`.agent/settings.json`](file://./.agent/settings.json).
- **Protocol**: Standardized [`SYSTEM.md`](file://./.agent/agents/*/SYSTEM.md) ingestion.

## Standard Optimization (2026)
1. **Thinking Blocks**: All models MUST use `<thinking>` for internal reasoning.
2. **Tiered Loading**: Ingest metadata (Tier-1) before full logic (Tier-2).
3. **Zero-Friction**: Root-level symlinks provided for legacy tool discovery.
