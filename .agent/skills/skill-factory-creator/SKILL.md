---
name: skill-factory-creator
description: Create, classify, and audit skills in this agentic factory so they follow the Skill-as-Pseudocode (SaP) format and the 4-tier taxonomy. Use when asked to add a skill, agent capability, contract, reference runbook, or script subcommand, or to check whether a proposed skill belongs in .agent/skills, .agent/contracts, references/, or scripts/.
---
# Skill Factory Creator

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: skill-authoring-taxonomy-gate] parent=skill-factory-creator required_inputs=['capability_name', 'capability_summary']
ls .agent/skills/ .agent/contracts/ | bin/rtk
grep -n '^name:' .agent/skills/*/SKILL.md | bin/rtk
grep -n 'skills:' -A6 .agent/agents/swarm-architect.yaml | bin/rtk
./scripts/hydrate.sh all | bin/rtk
python3 bin/compile_metadata.py --repo-root . --output .agent/metadata.json | bin/rtk
python3 bin/verify_runtime_discovery.py | bin/rtk
.venv/bin/python -m unittest tests/test_sap_pipeline.py | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_factory_creator_workflow(capability_name, capability_summary):
  1. PRE-CHECK: Duplicate scan done; USER approval; feature branch
  2. result <- invoke(skill-authoring-taxonomy-gate, {capability_name: "<capability_name>", capability_summary: "<capability_summary>"})
  3. POST-CHECK: Artifact at correct tier path; contract not surfaced under .agent/skills/; no orphan skill
  4. RETURN {Location, Problem, Fix, outputs: ['tier', 'artifact_path', 'registration_status']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: skill-authoring-taxonomy-gate`**
  - `trigger`: Skill factory creator operating contract hard rules from docs skill_as_pseudocode_architecture output format and reference index
  - `inputs`: required `['capability_name', 'capability_summary']`, optional `['parent_skill', 'script_paths']`
  - `outputs`: `['tier', 'artifact_path', 'registration_status']`
  - `preconditions`: Duplicate scan done; USER approval; feature branch
  - `postconditions`: Artifact at correct tier path; contract not surfaced under .agent/skills/; no orphan skill
  - `side_effects`: filesystem=writes under .agent/skills/ or .agent/contracts/, network=none
<!-- SAP_BUNDLE_END -->

## Operating Contract

This skill is a procedure, not a generator. It makes the author decide the tier, write the three SaP blocks in the right order, and register the result. It never replaces existing skills silently.

```text
CAPABILITY IDEA
  -> DUPLICATE SCAN (names, triggers, absorbed sub-skills)
  -> NARRATIVE BRIEF (Big Idea = trigger + stakes; consumer persona)   references/narrative-for-skills.md
  -> TIER DECISION (4-tier rule)                                      references/taxonomy-decision.md
  -> AUTHOR (Tier-specific template)                                  references/sap-authoring.md
  -> REGISTER (agents, compiler catalog, metadata, tests)             references/registration-checklist.md
  -> VERIFY (hydrate, metadata, discovery, tests)
  -> [STOP: USER review before commit]
```

## Hard Rules (from docs/SKILL_AS_PSEUDOCODE_ARCHITECTURE.md)

1. Never ship a contract alone. Contract-only scored 13/134 vs raw prose 16/134 (paper-reported, ALFWorld). Pair concrete Action Templates first, skeleton second, contracts third.
2. Never surface a child contract as a top-level folder in `.agent/skills/`. Flat pool cost 27% in the paper; `tests/test_sap_pipeline.py` enforces zero overlap.
3. Never create a skill with zero scripts and fewer than 3 runbooks (zero-asset prose stub; 23 of 55 legacy skills were this). Absorb it as a reference runbook or Action Template line instead.
4. Never leave a skill unbound: every top-level skill must appear in at least one `.agent/agents/*.yaml` `skills:` list (orphan test).
5. Contract trigger and I/O = shared procedural intersection of parents, not the union of nouns. Over-wide clustering fails the coverage check (`< 0.45`).
6. Every command in Block 1 pipes through `bin/rtk`; AST scripts use `/usr/bin/python3`.
7. `invoke(...)` is notation. Keep the SaP guard header verbatim.
8. Destructive sinks (`rm -rf`, `terraform destroy`, `git push origin main|master`, `gh pr merge`, `shell=True`, `eval`) hard-reject unless declared in `side_effects` with a `confirm` precondition.
9. Source of truth is `.agent/`. Never author into `.claude/`, `.agents/`, `.codex/` (ephemeral projections).
10. No new project or track without USER approval. No commit to master. Never merge.
11. Never write approval-skipping flags or "without asking" phrasing into a command, contract or doc. `verifier.py` flags them in `action_templates`, `probes` and `verify`.
12. A new reference must pass the with/without eval (`scripts/sap/eval_skill_value.py`, tasks in `tests/evals/skill_value.yaml`). Delete a guide that shows no delta over the model alone.
13. Descriptive filenames: `<topic>-<role>.md`, no `skill-` prefix, no bare `guide.md` or `creating.md`. Never name a script or template that does not exist (`test_12`).
14. Every volatile fact (version, limit, default, price) goes in a `## Volatile facts` row with as-of date, allowlisted source in `.agent/sources.yaml`, and a search query (`test_10`).

## Output Format

Chat to USER: caveman-prose, `Location | Problem | Fix`, no emoji. Skill files: full technical prose where the skill needs it, no filler.

## Reference Index

| Need | File |
| :--- | :--- |
| Directory layout, frontmatter, bundle anatomy | `references/skill-anatomy.md` |
| Which tier does this belong to | `references/taxonomy-decision.md` |
| Write the three blocks and the contract YAML | `references/sap-authoring.md` |
| Fowler/Moghe narrative method applied to skill design | `references/narrative-for-skills.md` |
| Bind agents, update catalog, run gates | `references/registration-checklist.md` |
| Write or audit a Tier 3 reference (template, naming, eval, sources) | `references/reference-authoring.md` |
