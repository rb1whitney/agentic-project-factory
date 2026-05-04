# Workflow: nit-fabric Operational Mandate

## The 4-Stage Reconciliation Lifecycle

1. **Audit (Scan)**: 
    - Query live cloud APIs.
    - Identify Environmental Drift.
2. **Analysis (Visualize)**:
    - Synthesize the technical map.
    - Update `network_state.md`.
3. **Remediation (Remediate)**:
    - Generate AI-driven HCL patches for failed sessions.
4. **Verification (Test)**:
    - Execute the TDD simulation suite before any physical `apply`.

## Industrial Standards
- **ZERO-DELETE**: Destructive operations require 3-expert swarm sign-off.
- **LIVE-TRUTH**: No decisions shall be made based on cached state files.
- **TDD-FIRST**: New nit-fabric features must include a failure simulation in `test_failures.json`.