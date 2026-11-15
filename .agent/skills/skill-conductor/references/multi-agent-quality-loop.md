# Multi-Agent Quality Loop (Domain-Driven)

**Read when**: more than one agent works on the same change and the result must be trustworthy. Scope: how roles, bounded contexts, independent review, and human gates keep multi-agent work correct. Lifecycle and templates are in `swarm-agent-roles-and-lifecycle.md`; this file covers the quality techniques.

## Core rule

The implementer's own gate is never the only gate. Linters, tests, and score tools are necessary; an independent reviewer who never saw the implementation is what finds what they miss.

## Techniques

1. **Bounded contexts per engineer.** The Architect splits the plan along domain boundaries (one aggregate or module per engineer). Each engineer gets a narrow slice, only the skills that slice needs, and no ability to delegate or rewrite the plan. Overlapping slices get separate worktrees.
2. **Roles in separate contexts.** Scout (read-only recon), Architect (plan, no implementation), Engineer (write and test), Auditor (review in a clean context). Permissions are explicit per role; nothing relies on a harness default.
3. **Independent hostile review.** After implementation, run the Auditor and a domain reviewer (for example `security-reviewer`) in parallel. Instruct them to attack, not to confirm. They return a written report, not a chat summary.
4. **Findings carry IDs.** Group by class (`SEC-`, `CFG-`, `AUTH-`, `INJ-`, `CRYPTO-`). Every fix cites the ID it closes, so nothing is silently dropped and the review is traceable.
5. **Human decision gates.** The reviewers convert findings that involve a trade-off into a short list of explicit questions (for example: change a CLI input method, harden example manifests, delete dead modules). The human answers; only then does remediation start. Agents decide mechanics, the human decides trade-offs.
6. **Evidence after every change.** Re-run the same deterministic gates (lint, tests, structural audit, policy lint) and report the numbers. A claim without output is not done.
7. **Deterministic tools take mechanical judgments.** Use linters, AST audits, and policy linters for anything a program can decide. Keep model reasoning for design and review.
8. **Artifacts land in the track.** Recon, plan, and certification reports are written to `conductor/tracks/<track-id>/` using the templates in `conductor/templates/`, not to a harness-private folder, so the review outlives the session.

## Worked example (vault_controller hardening session)

| Stage | What happened |
| :--- | :--- |
| Implement | Engineer applied a plan. `ruff` clean, structural audit 98.2/100 (all pillars passing), 55 tests passing. |
| Hostile review | `security-reviewer` and `swarm-auditor` ran in parallel. 22 security findings plus code-smell findings, written to a report with IDs. |
| Decision gate | Three trade-off questions put to the human. Answers: yes, yes, yes. |
| Remediate | Fixes mapped to finding IDs (secret input handling, token revocation, validation bypasses, crypto and backup hardening, dead-module removal, example manifest posture). |
| Verify | `ruff` clean, policy lint cleared the targeted finding classes, 60 tests passing. |

Observation: the structural audit score read 98.2/100 with the security pillar at 100 both before and after the hostile review, yet the reviewers found 22 security findings. The score did not discriminate. Treat a high automated score as a floor, never as certification.

## Anti-patterns

- Same agent implements and certifies.
- Reviewer shares the implementer's context or conversation.
- Findings reported as prose with no IDs, or fixed without referencing them.
- Trade-off decisions taken by an agent without asking.
- Report stored only in a harness-private directory.
- A passing score or green test run presented as sufficient evidence.
