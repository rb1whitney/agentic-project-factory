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
## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
<!-- SAP_BUNDLE_END -->

(domain prose: protocol, rules, decision tables)
```

The bundle sits immediately after the H1 so it is read first. `scripts/sap/compile_corpus.py` regenerates this block; do not hand-edit between the markers once the contract exists in the compiler catalog.

## Checks the repo runs on a skill

| Check | Where | Requirement |
| :--- | :--- | :--- |
| RC bundle | `scripts/sap/refactor.py:verify_rc_bundle` | `## ...Action Templates` + code fence; `## ...Procedural Skeleton` + `invoke(id` ; `## ...Inlined Contracts` |
| Orphan | `tests/test_sap_pipeline.py` | skill named in >=1 agent `skills:` |
| Hierarchy | same | no contract id equals a skill directory name |
| Count | same | hardcoded totals (13 skills, 15 agents). Adding a Tier-1 skill requires updating these asserts in the same change |
| Contract schema | `.agent/adapters/schemas/contract.schema.json` | required: id, trigger, input_schema.required, output_schema, preconditions, postconditions, side_effects{filesystem,network}, source_parents, action_templates |
| Verifier | `scripts/sap/verifier.py` | coverage >=0.45, binding >=0.50, replacement >=0.80, risk <0.80 |

## Agent side

Agents live in `.agent/agents/<name>.yaml` (stem == `name`), with `skills:` list, `contract:` block, and `prompt: |` carrying the SaP agent bundle. Edit the canonical YAML, then `./scripts/hydrate.sh all`. Never edit `.claude/agents/*.md`.

## Content rules for the body

- Decision tables over narrative paragraphs.
- Persona sentences ("You are a senior ...") are noise; state the contract and rules instead.
- Concrete flags only; every command piped through `bin/rtk`.
- No emoji. Credentials only via `gopass` references, never values.
