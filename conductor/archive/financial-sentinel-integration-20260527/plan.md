# Implementation Plan: Cross-Project FinOps Hardening

## Phase 1: Strategic Discovery
- **Action**: Scout `fin-sentinel` for core logic and porting targets.
- **Action**: Analyze target projects for structural compatibility and observability gaps.

## Phase 2: Tactical Planning
- **Action**: Create local Conductors and mission tracks in target projects.
- **Action**: Design project-specific TDD implementation plans.

## Phase 3: Execution
- **Task A: cloud-boot-app**
    - Implement CloudWatch Metric Filters.
    - Create OPA Gatekeeper policies for `us-east-1` residency.
- **Task B: managed-cloud-infra**
    - Create modular `monitoring-sre` and `finops-governance` submodules.
    - Integrate submodules into the root orchestrator with conditional toggles.

## Phase 4: Verification
- **Action**: Run `opa test` and `terraform validate`.
- **Action**: Confirm end-to-end wire-up of alerting systems.
