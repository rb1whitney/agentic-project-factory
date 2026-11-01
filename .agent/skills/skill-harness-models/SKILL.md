---
name: skill-harness-models
description: Model-name drift checker and updater for the Claude Code, Antigravity (agy) and Codex adapters. Compares the tier models in .agent/adapters/map.yaml with what each installed harness reports, and rewrites stale tier values from regex rules.
auto_triggers:
  - "update models"
  - "model drift"
  - "stale model"
  - "refresh tiers"
  - "model not found"
---

# Harness Model Updater

Tier names (`fast`, `deep`) in agent yamls resolve to concrete model ids through
`.agent/adapters/map.yaml` (`harnesses.<harness>.tiers`). Vendors rename and retire models;
this skill detects that and fixes `map.yaml`. Agent yamls never contain model names.

## Commands (single entry point, no standalone script)

```bash
./scripts/hydrate.sh models           # check only; exit 1 if any tier model is not available
./scripts/hydrate.sh models --write   # rewrite stale tiers using tier_rules, then re-run to confirm
./scripts/hydrate.sh all              # regenerate harness files after the map changes
```

## Sources of truth per harness

| Harness | Source | Needs |
|---|---|---|
| antigravity | `agy models` (id, display name per line) | signed-in agy |
| codex | `codex debug models` (JSON catalog, only `visibility: list`) | codex installed |
| claude | `GET /v1/models` (active models, `line` = sonnet/opus/...) | `ANTHROPIC_API_KEY` via gopass; otherwise reported UNVERIFIED |

An unreachable source prints `UNVERIFIED` and never fails the check.

## Rules (edit in map.yaml)

`tier_rules.<tier>` is a regex over the harness's ids. The highest dotted version among matches
wins (`gpt-5.10-luna` beats `gpt-5.6-luna`). Claude tiers are aliases (`sonnet`, `opus`) checked
against active `line` values and are never auto-rewritten.

## Workflow

1. Run `./scripts/hydrate.sh models`. Read each `NOT AVAILABLE` line and the rule's pick.
2. If a pick is wrong (family renamed, tier mapping changed), edit `tier_rules` first, not the tier value.
3. Run with `--write`; review `git diff .agent/adapters/map.yaml`.
4. Run `./scripts/hydrate.sh all` and `python3 bin/verify_runtime_discovery.py`.
5. Feature branch, commit, PR. Never merge.

## Guardrails

- Read-only commands only; never send prompts to a model to discover names.
- Never print or store `ANTHROPIC_API_KEY`; source it from gopass for the one command.
- Docs pages can lag the installed build. The installed CLI output wins.
