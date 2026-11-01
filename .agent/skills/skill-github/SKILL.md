---
name: skill-github
description: Repository manager for GitHub Issue lifecycles, Pull Request operations, and automated code review coordination.
---
# Skill: GitHub Repository & PR Governance (`skill-github`)

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
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute specific skill description workflow on `current_branch` and `specific_scope` (with optional `workflow_run_id`) for current repository state across PR creation, CI replication, review suite, and docs to produce `current_status` and `specific_description`.

### 1. Branch & Pull Request Governance Gate
- **No Direct Commits to Master/Main**: Verify `git branch --show-current | bin/rtk` is a feature branch (`feat/*`, `fix/*`, `chore/*`) before staging or committing.
- **No Autonomous Merge**: Never execute `gh pr merge`; merging is strictly reserved for human operators.
- **5-Step PR Sequence**:
  1. Verify feature branch and clean working tree (`git status -s | bin/rtk`).
  2. Run unit test and lint gates before commit.
  3. Commit with a concise technical message.
  4. Push branch and create/update PR via `gh pr create` / `gh pr edit` with a structured changelog.
  5. Attach specialist/auditor review findings via `gh pr comment`.

### 2. CI Failure Triage & Local Replication
- Inspect failing GitHub Actions runs using `gh run list --limit 5 | bin/rtk` and `gh run view <workflow_run_id> --log-failed | bin/rtk`, or use `{SKILL_DIR}/scripts/ci.mjs` and `{SKILL_DIR}/references/ci-replicator.md` to reproduce failures locally before pushing fixes.

## Reference & Script Routing Index

| GitHub Capability | Trigger / Scope | Reference Runbooks & Scripts (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **Pull Request Creation & Lifecycle** | Feature-branch PR formatting, changelog generation, PR updates | `references/pr-creator.md`, `references/pr-creation-guide.md`, `references/pr-guide.md`, `references/changelog-guide.md` |
| **Automated Code & String Review** | Multi-dimension PR review suite, security/style checks, UI/copy string review | `references/review-suite.md`, `references/review-guide.md`, `references/string-review-guide.md` |
| **CI Failure Replication** | Inspecting GitHub Actions logs (`workflow_run_id`) and reproducing CI locally | `references/ci-replicator.md`, `scripts/ci.mjs` |
| **Issue Triage & Authoring** | Structured bug reports, feature requests, issue labeling | `references/issue-creation-guide.md`, `references/issue-guide.md` |
| **Technical Documentation** | Architecture docs, READMEs, markdownlint compliance | `references/docs.md`, `references/docs-writing-guide.md` |
