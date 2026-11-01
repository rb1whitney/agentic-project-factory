---
name: skill-compliance-auditor
description: Governance lead for enforcing AI engineering standards and least-privilege security patterns across the hub.
---
# Skill: Compliance & Governance Auditor (`skill-compliance-auditor`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: ast-policy-compliance-audit] parent=skill-compliance-auditor required_inputs=['target_dir', 'pillar_scope']
/usr/bin/python3 .agent/skills/skill-code-map/scripts/well_architected_audit.py {target_dir} --pillar {pillar_scope} | bin/rtk
/usr/bin/python3 .agent/skills/skill-code-map/scripts/local_extract.py {target_dir} | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_compliance_auditor_workflow(target_dir, pillar_scope):
  1. PRE-CHECK: ast-grep binary installed; Read-only static analysis mode
  2. result <- invoke(ast-policy-compliance-audit, {target_dir: "<target_dir>", pillar_scope: "<pillar_scope>"})
  3. POST-CHECK: Zero secret leak or policy violation unflagged
  4. RETURN {Location, Problem, Fix, outputs: ['findings_json', 'compliance_status', 'remediation_diff']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: ast-policy-compliance-audit`**
  - `trigger`: Execute 6-Pillar Well-Architected AST rules, compliance security checks, and behavioral evaluations
  - `inputs`: required `['target_dir', 'pillar_scope']`, optional `['rule_pack']`
  - `outputs`: `['findings_json', 'compliance_status', 'remediation_diff']`
  - `preconditions`: ast-grep binary installed; Read-only static analysis mode
  - `postconditions`: Zero secret leak or policy violation unflagged
  - `side_effects`: filesystem=none, network=none
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute 6-Pillar Well-Architected AST rules, compliance security checks, and behavioral evaluations across `target_dir` and `pillar_scope` (`SEC`, `REL`, `OPS`, `PERF`, `COST`, `SUS`, or `ALL`) using `rule_pack` definitions to emit `findings_json`, `compliance_status`, and `remediation_diff`.

### 1. Static AST & Policy Audit Workflow
- Run `well_architected_audit.py` and `local_extract.py` in read-only static analysis mode before certifying any track or PR.
- Cross-check findings against the governance and readiness runbooks in `{SKILL_DIR}/references/`.
- Verify zero unflagged secret exposure, wildcard IAM permissions, or unsafe execution sinks (`shell=True`, `eval`, unpinned images).

### 2. Behavioral & Release Readiness Gate
- Validate agent and microservice behavioral evaluations using the evaluation templates in `{SKILL_DIR}/scripts/assets/` and `{SKILL_DIR}/references/behavioral-evals.md`.
- Block promotion when `compliance_status` reports `HIGH` or `CRITICAL` findings or when `readiness-checklist.md` gates fail.

## Reference & Script Routing Index

| Audit Capability | Trigger / Scope | Reference Runbooks & Assets (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **AI & Agent Standards** | Agentic safety, prompt/contract standards, knowledge validation | `references/ai-standards-guide.md`, `references/knowledge-validation.md` |
| **Behavioral Evaluations** | Creating, running, fixing, and promoting behavioral eval suites | `references/behavioral-evals.md`, `references/creating.md`, `references/running.md`, `references/fixing.md`, `references/promoting.md`, `scripts/assets/standard_eval.ts.txt`, `scripts/assets/interactive_eval.ts.txt` |
| **Identity & Least Privilege** | IAM boundaries, zero-trust credentials, RBAC/ABAC review | `references/identity-guide.md` |
| **Regulatory & Hub Governance** | Policy enforcement, branch/PR governance, audit trails | `references/compliance-guide.md`, `references/governance-guide.md` |
| **Production Readiness** | Pre-release certification gate (`CERTIFICATION_REPORT.md`) | `references/readiness-checklist.md` |
