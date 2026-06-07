---
name: skill-swarm-management
description: Swarm quality control lead for enforcing the Conductor CDD lifecycle and automated quality gates.
license: MIT
---
# Swarm Management Skill

This skill provides the operational framework for high-performance agent swarms. It ensures that all work is planned, verified, and documented.

## 1. Supervisor Orchestration Protocol (The State Machine)

When acting as the Supervisor, follow this mandatory protocol to manage the swarm's lifecycle. Do not perform technical work yourself; instead, dispatch the appropriate agent.

### Protocol Steps:
1. **STATE CHECK**: Inspect the `{PROJECT_DIR}/conductor/tracks/<track_id>/` directory.
2. **GAP ANALYSIS**: Determine the next required action based on existing artifacts:
   - **No Research Report?** (Look for files in `research/`): Dispatch `@swarm-scout`
   - **No Implementation Plan?** (Look for `plan.md`): Dispatch `@swarm-architect`
   - **No Master Roadmap?** (Look for `00_MASTER_ROADMAP.md` in `{PROJECT_DIR}/conductor/`): Dispatch `@swarm-architect`
   - **Plan Approved & Ready for Code?**: Dispatch `@swarm-engineer`
   - **Code Implementation Finished?**: Dispatch `@swarm-auditor`
3. **DISPATCH**: Use `invoke_agent` to call the required specialist with a comprehensive prompt.
4. **VERIFICATION**: After a subagent finishes, verify the expected artifact (file) was created or updated.

### Phase Gates:
- **Phase 1: Discovery (Scout)**: Analyze requirements and repo structure.
- **Phase 2: Planning (Architect)**: Define strategy and decompose into granular tasks.
- **Phase 3: Human Review Gate (STOP)**: Present the `plan.md` to the user. **Wait for "Approve" before proceeding.**
- **Phase 4: Construction (Engineer/Auditor)**: Sequential implementation and quality verification.

## 2. Conductor Protocol (CDD)

Conductor is the **Context-Driven Development** protocol used to manage complex tasks through a strict lifecycle:

### Commands
- `/conductor:setup` - Initialize the project context (`{PROJECT_DIR}/conductor/` directory).
- `/conductor:newTrack` - Decompose a request into a `spec.md` and `plan.md`.
- `/conductor:implement` - Execute tasks sequentially following the plan.
- `/conductor:status` - View progress across all active tracks.
- `/conductor:review` - Audit the implementation against the original plan.

## Lifecycle Gates
1. **Spec Phase**: Problem statement, architecture diagrams, and success criteria.
2. **Plan Phase**: Granular task breakdown with verification steps for each task.
3. **Execution Phase**: TDD (Test -> Fail -> Implement -> Pass).
4. **Audit Phase**: Multi-agent review (GitHub, Quality, Security).

## 3. Swarm Coordination Roles

The swarm operates using four specialized roles to ensure separation of concerns:

- **Supervisor**: Project manager. Owns the state machine, git commits, and phase transitions.
- **Architect**: Strategic planner. Maps the codebase and designs the technical solution.
- **Engineer**: Tactical executor. Writes code and unit tests.
- **Auditor**: Quality guardian. Verifies implementations and enforces standards.

## 4. Context & Reconnaissance

Before any change is proposed, the swarm must have high-precision context.

- **Index**: Use code-map utilities to maintain an up-to-date repository map.
- **Lens**: Narrow the context to the relevant modules before starting work.
- **Ground Truth**: Always prioritize local documentation and official SDK references over pre-training data.

## 5. Multi-Agent Review Suite

Every significant change must pass through the Review Suite before completion:

1. **Logic Audit**: Verify the PR fulfills the requirements and follows commit standards.
2. **Quality Audit**: Check for SOLID compliance, test coverage, and anti-shortcut detection (no TODOs).
3. **Security Audit**: Ensure no secrets are exposed and least-privilege principles are followed.

[!IMPORTANT]
- **No Emojis**: Communication must be professional and evidence-based.
- **Verification First**: Never mark a task as complete without passing automated tests.
