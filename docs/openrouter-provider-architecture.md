# OpenRouter Provider Architecture & Multi-Harness Integration

## 1. Executive Summary
The **OpenRouter Provider Integration** enables the agentic factory to route subagent execution across arbitrary LLM models (e.g. Claude 3.5 Sonnet, Claude 3 Opus, DeepSeek Coder, Llama 3.3) via a single unified endpoint.

Crucially, this integration preserves **Canonical Source Purity**:
- Canonical agent definitions in `.agent/agents/*.yaml` declare abstract capability tiers (`fast`, `deep`), remaining 100% provider-agnostic.
- The provider mapping in `.agent/adapters/map.yaml` resolves abstract tiers to concrete OpenRouter model identifiers.
- The hydration compiler (`scripts/hydrate.py`) projects provider settings into harness-native formats on demand via `--provider=openrouter`.

---

## 2. Cross-Harness Runtime Specifications

Different agent coding harnesses handle custom model endpoints at distinct architectural layers:

| Harness | Injection Layer | Configuration Target | Specification & Requirements |
| :--- | :--- | :--- | :--- |
| **OpenAI Codex CLI** | Global Config Table | `~/.codex/config.toml` | Custom providers **must** reside in the user's global configuration. Requires `wire_api = "responses"`. Project TOML files specify `model_provider = "openrouter"`. |
| **Claude Code** | Environment Variables | Shell profile / Wrapper | Overrides default endpoint via `ANTHROPIC_BASE_URL="https://openrouter.ai/api"`. Requires `ANTHROPIC_API_KEY=""` to prevent silent fallback billing to Anthropic. |
| **Antigravity (AGY)** | Client Application | `~/.gemini/antigravity-cli/settings.json` | Model loop is hardwired to Gemini client settings (`flash` / `pro`). Out-of-band tools or MCP sidecars cannot hijack the primary reasoning loop. |

---

## 3. Configuration & Schemas

### A. Canonical Adapter Mapping (`.agent/adapters/map.yaml`)
```yaml
providers:
  native:
    description: "Direct vendor model routing"
  openrouter:
    description: "Unified inference gateway via OpenRouter"
    base_url: "https://openrouter.ai/api/v1"
    claude_base_url: "https://openrouter.ai/api"
    env_key: "OPENROUTER_API_KEY"
    wire_api: "responses"
    tiers:
      fast: "anthropic/claude-3.5-sonnet"
      deep: "anthropic/claude-3-opus"
      cost_optimized: "deepseek/deepseek-coder"
      fallback: "meta-llama/llama-3.3-70b-instruct"
```

### B. Codex CLI Configuration

#### 1. Global Declaration (`~/.codex/config.toml`)
```toml
model_provider = "openrouter"

[model_providers.openrouter]
name = "OpenRouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
wire_api = "responses"
```

#### 2. Ephemeral Agent Projection (`.codex/agents/<name>.toml`)
When compiled with `python3 scripts/hydrate.py codex --provider=openrouter`:
```toml
# GENERATED from .agent/agents/swarm-scout.yaml by harness adapter. Do not edit.
name = "swarm_scout"
description = "The Repository Investigator. Specialized in mapping Blast Radius, structural analysis, and deep repo research."
model = "anthropic/claude-3.5-sonnet"
model_provider = "openrouter"
sandbox_mode = "read-only"
developer_instructions = """
...
"""
```

### C. Claude Code Launch Wrapper
To launch Claude Code using OpenRouter without billing Anthropic directly:
```bash
#!/usr/bin/env bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api"
export ANTHROPIC_API_KEY=""
export OPENROUTER_API_KEY="$(gopass show tokens/openrouter || cat ~/.mcp-servers/credentials/openrouter)"
export ANTHROPIC_CUSTOM_HEADERS="HTTP-Referer=https://github.com/rb1whitney/agentic-project-factory,X-Title=Agentic-Project-Factory"

claude "$@"
```

---

## 4. Zero-Trust Security & Credential Isolation

Per Section 5 of `AGENTS.md`:
1. **Never write credentials into project files**: `OPENROUTER_API_KEY` is never written to `.agent/`, `.codex/`, or `.claude/` files.
2. **Environment variable resolution**: Generated configurations cite the key name (`env_key = "OPENROUTER_API_KEY"`), allowing the host runtime to resolve credentials securely from the environment or password store (`gopass` / `rbw`).

---

## 5. Verification & Testing

The OpenRouter integration is covered by automated regression scenarios:

```bash
# Run scenario test directly
python3 .agent/scenarios/test_openrouter_provider.py

# Run full discovery gate
python3 bin/verify_runtime_discovery.py
```

The tests assert:
- `model_provider = "openrouter"` is properly injected into `.codex/agents/*.toml` under `--provider=openrouter`.
- Model aliases correctly resolve (`fast` -> `anthropic/claude-3.5-sonnet`).
- Zero secret strings exist in generated projections.
- Default native hydration round-trips cleanly with zero configuration drift.
