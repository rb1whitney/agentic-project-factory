---
name: skill-conductor
description: CDD (Context-Driven Development) protocol manager enforcing the Spec-Plan-Implement-Verify lifecycle.
---
# Gemini Conductor Skill

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: conductor-swarm-orchestration] parent=skill-conductor required_inputs=['phase_name', 'implementation_scope']
ls conductor/tracks/ conductor/templates/ .agent/skills/skill-conductor/references/ 2>/dev/null | bin/rtk
python3 bin/nexus.py status 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_conductor_workflow(phase_name, implementation_scope):
  1. PRE-CHECK: Active track registered in conductor/tracks/; Mandatory template selected from conductor/templates/
  2. result <- invoke(conductor-swarm-orchestration, {phase_name: "<phase_name>", implementation_scope: "<implementation_scope>"})
  3. POST-CHECK: Phase artifact verified before specialist hand-off
  4. RETURN {Location, Problem, Fix, outputs: ['phase_implementation_path', 'conductor_tdd_status']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: conductor-swarm-orchestration`**
  - `trigger`: Define conductor phase implementation and TDD skill description workflow across Swarm, DDD, Architecture, and Blueprints
  - `inputs`: required `['phase_name', 'implementation_scope']`, optional `['template_name']`
  - `outputs`: `['phase_implementation_path', 'conductor_tdd_status']`
  - `preconditions`: Active track registered in conductor/tracks/; Mandatory template selected from conductor/templates/
  - `postconditions`: Phase artifact verified before specialist hand-off
  - `side_effects`: filesystem=writes track markdown in conductor/tracks/, network=none

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (4)**: `scripts/templates/IMPLEMENTATION_PLAN.md`, `scripts/templates/LADR.md`, `scripts/templates/LOGICAL_ARCHITECTURE.md`, `scripts/templates/PHYSICAL_ARCHITECTURE.md`
- **Reference Runbooks (22)**: `references/architecture.md`, `references/aws-diagrams/aws4-shapes-resources.md`, `references/aws-diagrams/aws4-shapes-services.md`, `references/aws-diagrams/cli-export.md`, `references/aws-diagrams/diagram-templates-advanced.md`, `references/aws-diagrams/diagram-templates-basic.md`, `references/aws-diagrams/drawing-guide.md`, `references/aws-diagrams/general-icons.md`, `references/aws-diagrams/group-styles.md`, `references/aws-diagrams/layout-guidelines.md`, `references/aws-diagrams/post-processing.md`, `references/aws-diagrams/style-guide.md`, `references/aws-diagrams/xml-rules.md`, `references/aws-diagrams/xml-templates-examples.md`, `references/aws-diagrams/xml-templates-structure.md` (+7 more)
<!-- SAP_BUNDLE_END -->

Conductor is a **Context-Driven Development (CDD)** protocol. It turns an AI agent into a proactive project manager that follows a strict protocol to specify, plan, and implement software features and bug fixes.

## Commands

| Command | Description |
| :--- | :--- |
| `/conductor:setup` | Scaffolds the project and sets up the Conductor environment. |
| `/conductor:newTrack` | Starts a new feature or bug track. Generates `spec.md` and `plan.md`. |
| `/conductor:implement` | Executes the tasks defined in the current track's plan. |
| `/conductor:status` | Displays the current progress of the tracks file and active tracks. |
| `/conductor:revert` | Reverts a track, phase, or task by analyzing git history. |
| `/conductor:review` | Reviews completed work against guidelines and the plan. |

## Protocol Summary

### 1. Setup (`/conductor:setup`)
Initialize the `{PROJECT_DIR}/conductor/` directory with:
- `product.md`: Product vision, goals, and user personas.
- `tech-stack.md`: Technical choices, languages, frameworks, and constraints.
- `product-guidelines.md`: Brand voice, UI/UX standards, and communication style.
- `workflow.md`: The development lifecycle (rules for TDD, commits, etc.).
- `tracks.md`: The registry of all work units.

### 2. New Track (`/conductor:newTrack`)
For every new feature or fix:
1. **Spec**: Define *what* is being built and *why*.
2. **Plan**: Break down the work into **Phases** and **Tasks**. Each task must be actionable.
3. **Register**: Add the track to `{PROJECT_DIR}/conductor/tracks.md`.

### 3. Implementation (`/conductor:implement`)
A strict loop:
1. **Selection**: Pick the next task from the plan.
2. **Workflow**: Follow `workflow.md` (e.g., TDD: Write Test -> Fail -> Implement -> Pass).
3. **Commit**: Use meaningful commit messages and attach summaries via `git notes`.
4. **CP Verification**: At the end of every phase, run tests and perform manual verification.

### 4. Synchronization & Cleanup
1. **Sync**: Update project-level docs (`product.md`, `tech-stack.md`) based on the completed track.
2. **Cleanup**: Archive or delete the track artifacts once finalized.

## Guidelines for the Agent
- **Adhere to the Plan**: Do not deviate from the current `plan.md` without formal revision.
- **Context is King**: Always read and update the core context files in `{PROJECT_DIR}/conductor/` to maintain the project's single source of truth.
- **Verification First**: Never mark a task as complete without passing tests and verification.
