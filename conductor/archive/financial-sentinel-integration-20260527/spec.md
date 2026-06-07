# Mission Specification: Financial Sentinel Integration

## Objective
Port the governance, monitoring, and financial sovereignty standards from `projects/fin-sentinel` into the primary ecosystems of the factory: `cloud-boot-app` and `managed-cloud-infra`.

## Success Criteria
1.  **Observability**: Implementation of the four Golden Signals (Latency, Traffic, Errors, Saturation).
2.  **Governance**: Enforcement of regional financial sovereignty and data residency via OPA.
3.  **Modularity**: Integration of FinOps controls as reusable Terraform submodules.
4.  **Auditability**: Presence of local Conductors tracking the integration in each project.

## Requirements
- Use the Swarm skill (Scout, Architect, Engineer) to execute the lifecycle.
- TDD-first approach for all implementation steps.
- Maintain physical sovereignty (no parent-repo escapes).
