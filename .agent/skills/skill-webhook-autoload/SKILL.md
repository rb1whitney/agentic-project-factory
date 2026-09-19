---
name: skill-webhook-autoload
description: Adapter webhook lifecycle hook that automatically compiles metadata and hydrates canonical agents into active engine dotfiles on session startup.
auto_triggers:
  - "webhook"
  - "autoload"
  - "adapter webhook"
  - "lifecycle hook"
---

# Adapter Webhook Autoload Engine

## Overview
Automates the zero-touch autoloading of agents and skills for **Claude Code**, **Antigravity CLI (`agy`)**, and **Codex**.
When an agent or session initiates, the adapter webhook fires `bin/autoload_webhook.py` pre-invocation or on session start.

## Components
1. **Runner Script**: `bin/autoload_webhook.py`
   - Recompiles `.agent/metadata.json` from standard canonical sources.
   - Synchronously compiles `.agent/canonical-agents/*.yaml` into `.claude/agents/*.md` and `.agents/*.json`.
2. **Antigravity Hook**: `.agents/hooks.json` (`PreInvocation` event)
3. **Claude Hook**: `.claude/settings.json` (`SessionStart` event)
4. **Test Suite**: `tests/test_agent_webhook_autoload.py`

## Manual Verification
```bash
python3 tests/test_agent_webhook_autoload.py
```
