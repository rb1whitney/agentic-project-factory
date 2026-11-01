---
name: skill-factory-compiler
description: Factory agent compiler and hydration engine. Translates canonical multi-adapter agent schemas into runtime dotfiles (.claude/agents/, .agents/) and recompiles standard metadata without drift.
---
# Skill: Factory Agent Compiler & Hydration Engine (`skill-factory-compiler`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: factory-hydration-compiler] parent=skill-factory-compiler required_inputs=['harness_target', 'repo_root']
./scripts/hydrate.sh {harness_target} | bin/rtk
./scripts/hydrate.sh models | bin/rtk
python3 bin/compile_metadata.py --repo-root {repo_root} --output .agent/metadata.json | bin/rtk
python3 bin/verify_runtime_discovery.py | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_factory_compiler_workflow(harness_target, repo_root):
  1. PRE-CHECK: Canonical sources in .agent/agents/*.yaml and .agent/skills/*/SKILL.md; Physical Sovereignty enforced
  2. result <- invoke(factory-hydration-compiler, {harness_target: "<harness_target>", repo_root: "<repo_root>"})
  3. POST-CHECK: 1:1 reconciliation across Claude, Antigravity, and Codex projections
  4. RETURN {Location, Problem, Fix, outputs: ['metadata_path', 'discovery_status', 'reconciled_count']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: factory-hydration-compiler`**
  - `trigger`: Hydrate canonical multi-adapter YAML agents, sync Nexus spokes, verify model tiers, and certify runtime discovery
  - `inputs`: required `['harness_target', 'repo_root']`, optional `['write_models']`
  - `outputs`: `['metadata_path', 'discovery_status', 'reconciled_count']`
  - `preconditions`: Canonical sources in .agent/agents/*.yaml and .agent/skills/*/SKILL.md; Physical Sovereignty enforced
  - `postconditions`: 1:1 reconciliation across Claude, Antigravity, and Codex projections
  - `side_effects`: filesystem=writes .claude/, .agents/, .codex/, .agent/metadata.json, network=none
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Hydrate canonical multi-adapter YAML agents in `.agent/agents/*.yaml`, sync Nexus spokes via `bin/nexus.sh`, verify model tiers (`write_models`), and certify runtime discovery across `harness_target` and `repo_root` to produce `metadata_path`, `discovery_status`, and `reconciled_count`.

### 1. Canonical v2.2 Source Architecture
- **Agents**: `.agent/agents/<agent-name>.yaml` (`version: "2.2"`, `tier: fast|deep`, `skills: [...]`, `contract: {...}`, `prompt: |`). Validated against `.agent/adapters/schemas/agent.schema.json`.
- **Contracts**: `.agent/contracts/<contract-id>.yaml`. Validated against `.agent/adapters/schemas/contract.schema.json` and 4-check verifier (`{REPO_ROOT}/scripts/sap/verifier.py`).
- **Skills**: `.agent/skills/<skill-name>/SKILL.md`. Physical source of truth; projected to `.claude/skills/`, `.agents/skills/`, and `.codex/skills/` via `bin/nexus.py`.

### 2. Synchronous Hydration & Verification Pipeline
- Never author directly into `.claude/`, `.agents/`, or `.codex/` (ephemeral projections).
- Fail fast (`exit 1`) on missing adapter mappings in `.agent/adapters/map.yaml` or invalid model tiers (`agy plugin validate`).
  ```bash
  ./scripts/hydrate.sh all | bin/rtk
  ./scripts/hydrate.sh models | bin/rtk
  bash bin/nexus.sh | bin/rtk
  .venv/bin/python bin/verify_runtime_discovery.py | bin/rtk
  ```

## Reference & Script Routing Index

| Compiler Capability | Trigger / Scope | Reference Runbooks & Scripts (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **Hydration & Spoke Projection** | Compile `.agent/agents/*.yaml` into `.claude/agents/*.md`, `.agents/agents/*.md`, `.codex/agents/*.toml` | `references/nexus-sync.md`, `scripts/logic.py`, `scripts/scanner.py`, `scripts/templates/AGENT.md` |
| **Model Tier Drift & Validation** | Audit or update Claude (`sonnet`/`opus`), Antigravity (`flash`/`pro`), and Codex model tiers | `references/harness-models.md` |
| **PreInvocation Autoload Webhook** | Dynamic context and skill injection via `bin/autoload_webhook.py` | `references/webhook-autoload.md`, `scripts/tool.json` |
| **Agentic Initializer & AGENTS.md** | Bootstrapping canonical hub directories and `AGENTS.md` routing indexes | `references/agentic-initializer.md`, `references/vercel-agents-md.md` |
