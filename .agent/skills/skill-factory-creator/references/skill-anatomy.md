# Skill Anatomy

## Layout (Tier 1)

```text
.agent/skills/<skill-name>/
  SKILL.md              frontmatter + H1 + SAP bundle + domain body
  references/*.md       Tier 3 runbooks (conditionally loaded)
  scripts/*             Tier 4 deterministic CLIs (optional if >=3 runbooks)
  schemas/ examples/    optional, skill-specific
```

Naming: `skill-<domain>` kebab-case, directory name == frontmatter `name`. Reference implementation: `skill-github`, `skill-conductor`, `skill-presentation-architect`.

## SKILL.md

```markdown
---
name: skill-<domain>
description: One sentence: what it owns + when to use. Include trigger nouns the router will match.
---
# <Title>

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
## 2. Procedural Skeleton (Where Calls Fit)
## 3. Inlined Child Contracts (Abstract Guarantees)
<!-- SAP_BUNDLE_END -->

(domain prose: operating guardrails + ## Reference & Script Routing Index)
```

The bundle sits immediately after the H1 so it is read first. `./scripts/sap/compile_corpus.py` regenerates this block; do not hand-edit between the markers once the contract exists in the compiler catalog.
- For **Tier 1B (Knowledge-Router Parent)** skills (`>=10` reference runbooks, e.g., `skill-aws`), the `κ` contract wraps only real executable procedures (discovery, audit, validation), while the `## Reference & Script Routing Index` links to per-domain `guide.md` / `index.md` files so every `.md` under `references/` is reachable in `<=2` hops.

## Checks the repo runs on a skill

| Check | Where | Requirement |
| :--- | :--- | :--- |
| RC bundle | `scripts/sap/refactor.py:verify_rc_bundle` | `## ...Action Templates` + code fence; `## ...Procedural Skeleton` + `invoke(id` ; `## ...Inlined Contracts` |
| Orphan | `tests/test_sap_pipeline.py` | skill named in >=1 agent `skills:` |
| Hierarchy | same | no contract id equals a skill directory name |
| Count | same | hardcoded totals (15 skills, 15 agents). Adding a Tier-1 skill requires updating these asserts in the same change |
| Link & 2-Hop Reachability | same | every path in `SKILL.md` and `references/**/*.md` exists on disk; every `references/**/*.md` is reachable within `<=2` hops from `SKILL.md` |
| Reference Purity | same | no line-1 `SKILL.md` YAML frontmatter, no `Knowledge Bootstrap`, no `.agent/skills/skill-factory-creator`, and no non-`.md` files inside `references/` |
| Contract schema | `.agent/adapters/schemas/contract.schema.json` | required: id, trigger, input_schema.required, output_schema, preconditions, postconditions, side_effects{filesystem,network}, source_parents, action_templates |
| Verifier | `./scripts/sap/verifier.py` | coverage >=0.45, binding >=0.50, replacement >=0.80, risk <0.80; risk includes `oversight_loosening_flag` over `action_templates`, `probes`, `verify` |
| Contract probes | `contract.schema.json` | optional `probes` (read-only orientation) and `verify` (read-only post-check) command lists; placeholders must be declared inputs |
| Volatile facts | same | every `## Volatile facts` row: ISO as-of date within the age limit, source on the skill's allowlist in `.agent/sources.yaml`, search query (`test_10`) |
| No emoji, no phantom paths | same | no emoji in `references/` or `SKILL.md`; every named `scripts/`, `bin/`, `.agent/skills/` path exists (`test_12`) |

## Agent side

Agents live in `.agent/agents/<name>.yaml` (stem == `name`), with `skills:` list, `contract:` block, and `prompt: |` carrying the SaP agent bundle. Edit the canonical YAML, then `./scripts/hydrate.sh all`. Never edit `.claude/agents/*.md`.

## Content rules for the body

- Decision tables over narrative paragraphs.
- Persona sentences ("..") are noise; state the contract and rules instead.
- Concrete flags only; every command piped through `bin/rtk`.
- No emoji. Credentials only via `gopass` references, never values.
- References follow `references/reference-authoring.md`: a `Read when` line, then Signal -> Probe -> Decision tables, gotchas and volatile facts. Mutations are propose-only.
