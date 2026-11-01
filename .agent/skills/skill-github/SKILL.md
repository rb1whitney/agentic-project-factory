---
name: skill-github
description: Repository manager for GitHub Issue lifecycles, Pull Request operations, and automated code review coordination.
---
# GitHub Specialist

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: github-pr-ci-governance] parent=skill-github required_inputs=['current_branch', 'specific_scope']
ls .agent/skills/skill-github/references/ .agent/skills/skill-github/scripts/ 2>/dev/null | bin/rtk
git branch --show-current | bin/rtk
git status -s | bin/rtk
gh pr list --state open | bin/rtk
gh run list --limit 5 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_github_workflow(current_branch, specific_scope):
  1. PRE-CHECK: Active branch MUST NOT be master or main; Never execute gh pr merge (reserved for human operator)
  2. result <- invoke(github-pr-ci-governance, {current_branch: "<current_branch>", specific_scope: "<specific_scope>"})
  3. POST-CHECK: Feature branch verified, tests passing, PR changelog formatted
  4. RETURN {Location, Problem, Fix, outputs: ['current_status', 'specific_description']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: github-pr-ci-governance`**
  - `trigger`: Execute specific skill description workflow on current repository state for PR creation, CI replication, review suite, and docs
  - `inputs`: required `['current_branch', 'specific_scope']`, optional `['workflow_run_id']`
  - `outputs`: `['current_status', 'specific_description']`
  - `preconditions`: Active branch MUST NOT be master or main; Never execute gh pr merge (reserved for human operator)
  - `postconditions`: Feature branch verified, tests passing, PR changelog formatted
  - `side_effects`: filesystem=git working tree, network=GitHub API via gh CLI

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (1)**: `scripts/ci.mjs`
- **Reference Runbooks (12)**: `references/changelog-guide.md`, `references/ci-replicator.md`, `references/docs-writing-guide.md`, `references/docs.md`, `references/issue-creation-guide.md`, `references/issue-guide.md`, `references/pr-creation-guide.md`, `references/pr-creator.md`, `references/pr-guide.md`, `references/review-guide.md`, `references/review-suite.md`, `references/string-review-guide.md`
<!-- SAP_BUNDLE_END -->

You are an expert in managing the collaboration lifecycle on GitHub. You specialize in triaging issues, crafting high-quality Pull Requests, and conducting rigorous automated reviews.

##  Capability Reference Guide
Use the following runbooks for deep-dive investigation and implementation.

| Capability | Reference File |
| :--- | :--- |
| **Issue Creation** | [issue-creation-guide.md]({SKILL_DIR}/references/issue-creation-guide.md) |
| **Issue** | [issue-guide.md]({SKILL_DIR}/references/issue-guide.md) |
| **Pr Creation** | [pr-creation-guide.md]({SKILL_DIR}/references/pr-creation-guide.md) |
| **Pr** | [pr-guide.md]({SKILL_DIR}/references/pr-guide.md) |
| **Review** | [review-guide.md]({SKILL_DIR}/references/review-guide.md) |
| **String Review** | [string-review-guide.md]({SKILL_DIR}/references/string-review-guide.md) |

## Knowledge Bootstrap (MANDATORY)

Upon activation, you MUST immediately list and index the `{SKILL_DIR}/references/` directory to identify the specific issue or PR protocols required for the current task.

1. **List References**: `ls {SKILL_DIR}/references/`
2. **Select Protocol**: Identify if the task maps to `issue-guide.md`, `pr-guide.md`, or `review-guide.md`.
3. **Ingest & Execute**: Read the selected reference and follow its specific instructions.
