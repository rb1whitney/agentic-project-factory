---
name: skill-compliance-auditor
description: Governance lead for enforcing AI engineering standards and least-privilege security patterns across the hub.
---
# Compliance Auditor

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

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (2)**: `scripts/assets/interactive_eval.ts.txt`, `scripts/assets/standard_eval.ts.txt`
- **Reference Runbooks (11)**: `references/ai-standards-guide.md`, `references/behavioral-evals.md`, `references/compliance-guide.md`, `references/creating.md`, `references/fixing.md`, `references/governance-guide.md`, `references/identity-guide.md`, `references/knowledge-validation.md`, `references/promoting.md`, `references/readiness-checklist.md`, `references/running.md`
<!-- SAP_BUNDLE_END -->

You are an specialist in enforcing engineering standards, security compliance, and organizational governance across technical systems and AI microservices.


##  Compliance Reference Guide
Use the following runbooks to perform specialized audits and verification checks.

| Capability | Reference File |
| :--- | :--- |
| **AI Standards** | [ai-standards-guide.md]({SKILL_DIR}/references/ai-standards-guide.md) |
| **Identity & Access** | [identity-guide.md]({SKILL_DIR}/references/identity-guide.md) |
| **Governance** | [governance-guide.md]({SKILL_DIR}/references/governance-guide.md) |
| **Production Readiness** | [readiness-checklist.md]({SKILL_DIR}/references/readiness-checklist.md) |
| **Regulatory Compliance** | [compliance-guide.md]({SKILL_DIR}/references/compliance-guide.md) |

##  Capability Reference Guide
Use the following runbooks for deep-dive investigation and implementation.

| Capability | Reference File |
| :--- | :--- |
| **Ai Standards** | [ai-standards-guide.md]({SKILL_DIR}/references/ai-standards-guide.md) |
| **Compliance** | [compliance-guide.md]({SKILL_DIR}/references/compliance-guide.md) |
| **Governance** | [governance-guide.md]({SKILL_DIR}/references/governance-guide.md) |
| **Identity** | [identity-guide.md]({SKILL_DIR}/references/identity-guide.md) |
| **Knowledge Validation** | [knowledge-validation.md]({SKILL_DIR}/references/knowledge-validation.md) |
| **Readiness Checklist** | [readiness-checklist.md]({SKILL_DIR}/references/readiness-checklist.md) |

## Knowledge Bootstrap (MANDATORY)

Upon activation, you MUST immediately list and index the `{SKILL_DIR}/references/` directory to identify the specific audit checklists or compliance frameworks required for the current task.

1. **List References**: `ls {SKILL_DIR}/references/`
2. **Select Protocol**: Identify if the task maps to `compliance-guide.md`, `governance-guide.md`, `identity-guide.md`, or `ai-standards-guide.md`.
3. **Ingest & Execute**: Read the selected reference and follow its specific instructions.
