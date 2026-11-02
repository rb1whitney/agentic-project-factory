# Taxonomy Decision (4 Tiers)

Source: `docs/SKILL_AS_PSEUDOCODE_ARCHITECTURE.md` section 3. Re-read the section if this file and the doc disagree; the doc wins.

## Decision procedure

```text
Q0  Already covered? grep names/triggers in .agent/skills/*/SKILL.md and .agent/contracts/*.yaml.
    Yes -> extend the existing artifact. Stop.
Q1  Owns a distinct external CLI/API surface AND (>=1 script OR >=3 runbooks)?
    Yes -> Tier 1: Core Parent Skill  .agent/skills/<skill-name>/SKILL.md
           - Tier 1A (Procedural Parent): Primary surface is executable scripts/CLIs (e.g., skill-code-map, skill-sre-investigation).
           - Tier 1B (Knowledge-Router Parent): Owns >=10 reference runbooks across sub-domains (e.g., skill-aws).
             SKILL.md is a 2-hop router (SKILL.md -> domain guide/index.md -> leaf.md); its kappa contract wraps ONLY real
             executable discovery/audit procedures, never reference lookup (SaP §3.2 & Appendix U).
Q2  Multi-step procedure with typed inputs/outputs, invoked as invoke(kappa, args)?
    Yes -> Tier 2: Child Contract     .agent/contracts/<id>.yaml  (inlined into a Tier-1 parent and agents)
Q3  Troubleshooting guide, service catalog, architecture reference table?
    Yes -> Tier 3: Reference Runbook  .agent/skills/<parent>/references/<topic>.md (reachable in <=2 hops from SKILL.md)
Q4  Otherwise -> Tier 4: Script subcommand  .agent/skills/<parent>/scripts/<tool> + one Action Template line
```

## Tier table

| Tier | Path | Bound to agents? | Appears in skill picker? |
| :--- | :--- | :--- | :--- |
| 1A Procedural Parent | `.agent/skills/<name>/SKILL.md` | Yes, >=1 | Yes |
| 1B Knowledge-Router Parent | `.agent/skills/<name>/SKILL.md` | Yes, >=1 | Yes |
| 2 Child Contract | `.agent/contracts/<id>.yaml` | Via parent skill and agent `contract:` | No (must not) |
| 3 Reference Runbook | `.agent/skills/<parent>/references/**/*.md` | Via parent (`<=2` hops) | No |
| 4 Script Subcommand | `.agent/skills/<parent>/scripts/*` | Via parent | No |

## Worked classifications

| Idea | Tier | Reason |
| :--- | :--- | :--- |
| Narrative/PowerPoint deck builder | 1 | Distinct toolchain (storyboard schema, renderer), >=3 runbooks, scripts |
| "How to triage CrashLoopBackOff" | 3 | Symptom-matched runbook under `skill-kubernetes/references/` |
| New z-score detector for metrics | 4 | One script; add Action Template line in `skill-sre-investigation` |
| Typed "audit IAM policy" procedure used by 3 agents | 2 | Shared multi-step I/O; inline into parent |
| 20-line "prose stub" skill with no assets | none | Reject; fold into a parent as Tier 3 or Tier 4 |

## Rejection signals

- Name is a sub-procedure of an existing parent (`skill-pr-creator` under `skill-github`).
- Trigger is a noun list spanning unrelated services.
- Would be a peer of its own parent in the picker.
- Needs `mkdir` of a new top-level folder only to hold prose.

## Cluster width check (before Tier 2)

List the parent skills the contract serves. For each, confirm the contract's trigger tokens and required inputs actually appear in that parent's text. A token present in 1 of N parents drops recall to ~1/N and fails coverage.
