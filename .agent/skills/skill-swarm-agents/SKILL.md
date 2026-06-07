---
name: skill-swarm-agents
description: Swarm coordinator for initiating the Scout/Architect/Engineer/Auditor agent stack for complex builds.
license: MIT
---
# Swarm Agents Skill

This skill enables a high-precision, multi-agent workflow for designing and building production-ready systems. It is based on the **Conductor (CDD)** workflow.

## Workflow Lifecycle

1. **Discovery**: Dispatch `@swarm-scout` to analyze requirements and repo structure. Output: `{PROJECT_DIR}/conductor/tracks/<track_id>/research/`
2. **Strategic Planning**: Dispatch `@swarm-architect` to define high-level campaigns in `{PROJECT_DIR}/conductor/tracks.md`.
3. **Tactical Planning & Decomposition**: Dispatch `@swarm-architect` to create granular, TDD-focused plans in `{PROJECT_DIR}/conductor/tracks/<track_id>/plan.md`.
4. **Execution (Parallel)**: Spawn multiple `@swarm-engineer` instances to build independent sub-tracks step-by-step using TDD.
5. **Audit**: Dispatch `@swarm-auditor` to verify implementation against the plan and scan for stubs.

## Execution Commands

### Discovery
```bash
/conductor:dispatch agent=swarm-scout instruction="Research [topic] and map blast radius. Output to {PROJECT_DIR}/conductor/tracks/[track_id]/research/"
```

### Planning
```bash
/conductor:dispatch agent=swarm-architect instruction="Decompose [feature] into parallel tracks and create plans in {PROJECT_DIR}/conductor/tracks/[track_id]/"
```

### Execution (Parallel)
Instance 1:
```bash
/conductor:dispatch agent=swarm-engineer instruction="Implement track [id_1] in {PROJECT_DIR}/conductor/tracks/[id_1]/plan.md"
```
Instance 2:
```bash
/conductor:dispatch agent=swarm-engineer instruction="Implement track [id_2] in {PROJECT_DIR}/conductor/tracks/[id_2]/plan.md"
```

### Audit
```bash
/conductor:dispatch agent=swarm-auditor instruction="Audit implementation of track [id_1]. Scan for AI shortcuts."
```

## Templates

Templates for physical/logical architecture and implementation plans are located in `{SKILL_DIR}/scripts/templates/`.

## Quality Gate

The workflow uses the `audit_stubs.sh` script to ensure no shortcuts (TODO, FIXME, NotImplementedException) are present in the final implementation.
