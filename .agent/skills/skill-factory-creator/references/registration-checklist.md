# Registration Checklist

Run top to bottom. Stop on first failure. Pipe through `bin/rtk`.

## Tier 1 skill

- [ ] USER approved creation; on feature branch (`git branch --show-current` != master/main)
- [ ] Duplicate scan: `grep -n '^name:' .agent/skills/*/SKILL.md`
- [ ] `.agent/skills/<name>/SKILL.md` with frontmatter `name` == directory
- [ ] SaP bundle present (3 blocks, guard header, `invoke(<id>`)
- [ ] Contract in `scripts/sap/compile_corpus.py` `CONTRACTS_CATALOG` with `source_parents: [<name>]`
- [ ] Skill bound in `AGENT_CONTRACTS[<agent>]["skills"]` for >=1 agent, and agent YAML updated by compiler
- [ ] Test asserts for skill and agent counts updated together (`tests/test_sap_pipeline.py`)
- [ ] `./scripts/hydrate.sh all`
- [ ] `python3 bin/compile_metadata.py --repo-root . --output .agent/metadata.json`
- [ ] `python3 bin/verify_runtime_discovery.py`
- [ ] `.venv/bin/python -m unittest tests/test_sap_pipeline.py` all green
- [ ] Update `AGENTS.md` Skills Index and `docs/SKILL_AS_PSEUDOCODE_ARCHITECTURE.md` section 4 ledger if the parent count changes

## Tier 2 contract

- [ ] Entry in `CONTRACTS_CATALOG`; id not equal to any skill directory
- [ ] Verifier tier `auto_promote`
- [ ] Schema valid; consumers' agents regenerated

## Tier 3 runbook

- [ ] File under `<parent>/references/`; listed in parent body index
- [ ] Loaded conditionally (symptom match), not required reading

## Tier 4 script

- [ ] File under `<parent>/scripts/`; one Action Template line; `--help` works
- [ ] No `shell=True`, `eval`, undeclared destructive flags

## Hand-off

Finish with: "Skill creation complete. Please tag **@swarm-auditor** to verify before commit." Do not commit or push without USER instruction; never merge.
