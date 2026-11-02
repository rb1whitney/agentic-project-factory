---
name: skill-conductor
description: CDD (Context-Driven Development) protocol manager enforcing the Spec-Plan-Implement-Verify lifecycle.
---
# Skill: Conductor CDD & Swarm Orchestration (`skill-conductor`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: conductor-swarm-orchestration] parent=skill-conductor required_inputs=['phase_name', 'implementation_scope']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
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
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Define conductor phase implementation (`phase_name`, `implementation_scope`, `template_name`) and TDD skill description workflow across Swarm orchestration, Domain-Driven Design (DDD), Architecture (C4/LADR), and Product Blueprints to produce `phase_implementation_path` and `conductor_tdd_status`.

### 1. Deterministic 5-Phase Track Lifecycle
All project and manufacturing tracks in `conductor/tracks/<track-id>/` follow the Spec-Plan-Implement-Verify lifecycle using mandatory templates in `conductor/templates/`:
- **Phase 1 (Scout — Strategic Recon)**: Map blast radius and author `STRATEGIC_RECON.md`.
- **Phase 2 & 3 (Architect — DDD & Executive Plan)**: Define bounded contexts, LADRs, and TDD micro-steps in `EXECUTIVE_PLAN.md`.
- **Phase 4 (Engineer — TDD Implementation)**: Write failing tests first, implement surgical edits, and verify green test suite.
- **Phase 5 (Auditor — Certification)**: Run 6-Pillar audit and emit `CERTIFICATION_REPORT.md` before human review / PR push.

### 2. Conductor Commands & Governance Rules
- `/conductor:setup`, `/conductor:newTrack`, `/conductor:implement`, `/conductor:status`, `/conductor:review`, `/conductor:revert`.
- Never initiate a new project or track without explicit user approval.
- Follow the IDE Hand-off Protocol on phase completion: stop and ask the user to tag the next specialist (`@swarm-architect`, `@swarm-engineer`, `@swarm-auditor`, `@swarm-supervisor`).

## Reference & Script Routing Index

| Orchestration Capability | Trigger / Scope | Reference Runbooks & Templates (`.agent/skills/skill-conductor/` & `conductor/`) |
| :--- | :--- | :--- |
| **Track Lifecycle & Templates** | Phase 1/3/5 track artifacts and architectural plan templates | `conductor/templates/STRATEGIC_RECON.md`, `conductor/templates/EXECUTIVE_PLAN.md`, `conductor/templates/CERTIFICATION_REPORT.md`, `scripts/templates/IMPLEMENTATION_PLAN.md`, `scripts/templates/LOGICAL_ARCHITECTURE.md`, `scripts/templates/PHYSICAL_ARCHITECTURE.md` |
| **Swarm Multi-Agent Lifecycle** | Scout/Architect/Engineer/Auditor/Supervisor hand-offs & track archival | `references/swarm.md`, `references/swarm-agents.md`, `references/swarm-management.md` |
| **Domain-Driven Design (DDD)** | 7-step Strategic-to-Tactical DDD bounded context & aggregate design | `references/ddd.md` |
| **Product Factory Blueprint** | 6-phase standalone product manufacturing & Zero-Zero decoupling | `references/product-blueprint.md` |
| **Architecture & LADR Generation** | Lightweight Architecture Decision Records (LADRs) & system design | `references/ladr-generator.md`, `references/ladr-template.md`, `scripts/templates/LADR.md` |
| **AWS Architecture Diagrams** | Draw.io / XML architecture diagram generation & layout standards | `references/aws-diagrams/drawing-guide.md`, `references/aws-diagrams/layout-guidelines.md`, `references/aws-diagrams/style-guide.md`, `references/aws-diagrams/cli-export.md` |
