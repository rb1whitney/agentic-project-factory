# Project Analysis: managed-cloud-infra

## 1. File & Directory Map
```
projects/managed-cloud-infra/
├── .claude/                   # Legacy vendor directory (Decommissioned)
├── .copilot/                  # Legacy vendor directory (Decommissioned)
├── .cursorrules               # Legacy IDE rules
├── .gemini/                   # Legacy vendor directory (Decommissioned)
├── .github/
├── 2hour-kubernetes/          # Sub-project/Template (Real logic buried here)
│   ├── argocd/
│   ├── compositions/          # AWS/GCP entry points
│   ├── helm/
│   ├── modules/               # Networking, Compute, IAM, FinOps
│   └── tests/                 # Rego policies
├── AGENT.md                   # Legacy manifest (Outdated)
├── agents/                    # Broken symlink (../agents)
├── runbooks/                  # SRE runbooks (Static docs)
├── skills/                    # Broken symlink (../skills)
└── terraform/
    └── sre-monitoring.tf      # Placeholder (No real resources)
```

## 2. Terraform Inspection
- **Root `terraform/`**: Contains only `sre-monitoring.tf`. This file is a placeholder with a single `output` and no `resource` blocks. It is non-functional.
- **`2hour-kubernetes/compositions/`**: Contains functional Terraform for AWS and GCP.
- **`2hour-kubernetes/modules/`**: Contains well-defined modules for VPC, EKS/GKE, and IAM.
- **Issue**: The functional Terraform is nested and disconnected from the project root. There is no clear `main.tf` or `provider.tf` at the project root to orchestrate the infrastructure.

## 3. Usability Gaps
- **Entry Point**: No clear entry point for `terraform apply`. The root `terraform/` directory is empty of logic.
- **Broken Dependencies**: `agents/` and `skills/` are symlinks pointing to non-existent parent directories (`../agents`, `../skills`). This breaks local agentic reasoning.
- **Missing Plan**: No `plan.md` or `task.md` to track progress or state.
- **Nested Logic**: Real infrastructure code is hidden in `2hour-kubernetes/`, making it non-obvious how to deploy.

## 4. Standard Compliance Audit
- **`manifest.json`**: **MISSING**. Required for Unified Agentic Standard.
- **`acs.yaml`**: **MISSING**. Required for tiered context loading.
- **`.agent/` Directory**: **MISSING**. Project uses legacy root-level `agents/` and `skills/` folders.
- **Legacy Directories**: **PRESENT** (`.gemini/`, `.claude/`, `.copilot/`). These violate the Unified Agentic Standard which mandates decommissioning in favor of `.agent/`.
- **Decoupling**: **FAILED**. Project uses symlink escapes (`../../`) in modules and broken symlinks for agents/skills.
- **`AGENT.md`**: **OUTDATED**. References decommissioned `.gemini/` nexus and legacy protocols.

## 5. Findings Summary
Location | Problem | Fix
--- | --- | ---
`projects/managed-cloud-infra/` | Missing `.agent/` directory | Create `.agent/` hub; move agents/skills there.
`projects/managed-cloud-infra/agents` | Broken symlink escape | Replace with physical resident experts.
`projects/managed-cloud-infra/skills` | Broken symlink escape | Replace with physical resident skills.
`projects/managed-cloud-infra/` | Missing `manifest.json` / `acs.yaml` | Initialize standard metadata files.
`projects/managed-cloud-infra/terraform/` | Placeholder logic only | Promote `2hour-kubernetes` logic or create root orchestrator.
`projects/managed-cloud-infra/AGENT.md` | Legacy/Conflicting protocols | Update to ACS-2026 Unified Standard.
`projects/managed-cloud-infra/` | Missing `plan.md` | Initialize project tracking.
