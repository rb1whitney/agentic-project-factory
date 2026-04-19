# Track Specification: Skill Consolidation & Role Alignment

## Objective
Eliminate repository-wide "selector noise" and redundancy by transitioning from 93 atomic, service-specific skills to 32 high-level, role-based experts.

## Context
The repository had reached 93 specialized skills (many redundant or stuttering like `aws-amazon-location-service-amazon-location-service`). This created significant overhead for AI agents during skill selection. The goal is to harden a "Reference-Led Architecture" where one expert (Role) can perform many specialized tasks by researching local runbooks (References).

## Scope
- **AWS Experts**: Consolidate Sagemaker, Serverless, Foundation (EC2/RDS), and niche app services (Location, Amplify, DSQL).
- **Terraform Specialization**: Group 25+ providers into Admin, Module-Writer, Tester, and Provider-Dev roles.
- **Security & Compliance**: Consolidate audit, governance, and identity skills into a unified Compliance Auditor role.
- **Operational Alignment**: Create Platform-Admin (Onboarding/SDKs) and CI-Replicator roles.
- **Protocol Hardening**: Inline the Agentic Loop into the master instructions (AGENT.md).

## Success Criteria
- [x] Total skill count reduced from 93 to 32 (~65% reduction).
- [x] All skills follow the "Knowledge Bootstrap" reference-discovery pattern.
- [x] Folder paths match agent names in the global index at 100% accuracy.
- [x] Master instructions (AGENT.md) contains the core Agentic Loop Protocol.
- [x] INVENTORY.md synchronized and verified.
