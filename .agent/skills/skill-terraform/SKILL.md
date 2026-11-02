---
name: skill-terraform
description: IaC specialist for developing reusable Terraform modules, providers, and state management strategies.
---
# Skill: Terraform & Declarative Infrastructure (`skill-terraform`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: iac-infra-provisioning] parent=skill-terraform required_inputs=['infrastructure_dir', 'specific_target']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
terraform -chdir={infrastructure_dir} fmt -check && terraform -chdir={infrastructure_dir} validate | bin/rtk
/usr/bin/python3 .agent/skills/skill-code-map/scripts/state_graph.py lint {infrastructure_dir} | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_terraform_workflow(infrastructure_dir, specific_target):
  1. PRE-CHECK: No terraform destroy without explicit user confirmation; State backend locked/verified
  2. result <- invoke(iac-infra-provisioning, {infrastructure_dir: "<infrastructure_dir>", specific_target: "<specific_target>"})
  3. POST-CHECK: Declarative IaC validated and drift checked before apply
  4. RETURN {Location, Problem, Fix, outputs: ['implementation_status', 'capability_report']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: iac-infra-provisioning`**
  - `trigger`: Infrastructure capability implementation and specific skill description validation for Terraform, Packer, Network, PKI, and On-Prem
  - `inputs`: required `['infrastructure_dir', 'specific_target']`, optional `['var_file']`
  - `outputs`: `['implementation_status', 'capability_report']`
  - `preconditions`: No terraform destroy without explicit user confirmation; State backend locked/verified
  - `postconditions`: Declarative IaC validated and drift checked before apply
  - `side_effects`: filesystem=local .terraform cache only, network=provider schema/state read
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute infrastructure capability implementation and specific skill description validation across `infrastructure_dir`, `specific_target`, and `var_file` for Terraform, Packer, Network, PKI, and On-Prem provisioning to produce `implementation_status` and `capability_report`.

### 1. Pre-Apply Validation & Blast Radius Gate
- Run `terraform fmt -check`, `terraform validate`, `state_graph.py`, and `tf_plan_analyzer.py` before proposing any state mutation.
- Use `skill-code-map` (`graph_builder.py` and `semantic_query.py`) to trace module variable usages and cross-stack dependencies before editing HCL.
  ```bash
  terraform -chdir=<infrastructure_dir> fmt -check && terraform -chdir=<infrastructure_dir> validate | bin/rtk
  python3 .agent/skills/skill-terraform/scripts/tf_plan_analyzer.py --help 2>/dev/null | bin/rtk
  /usr/bin/python3 .agent/skills/skill-code-map/scripts/state_graph.py env-diff dev prod --root <infrastructure_dir> | bin/rtk
  ```

### 2. IaC Safety & Sovereignty Rules
- **No Unconfirmed Destroy**: `terraform destroy` is strictly prohibited without explicit user confirmation.
- **Zero Hardcoded Secrets**: Source all sensitive inputs from Vault/OpenBao, KMS, or environment variables; redact `*.tfvars` secrets in all diffs.
- **Modular & Tested HCL**: Enforce pinned provider versions, remote state locking, and declarative validation blocks.

## Reference & Script Routing Index

| IaC Capability | Trigger / Scope | Reference Runbooks & Scripts (`.agent/skills/skill-terraform/`) |
| :--- | :--- | :--- |
| **Terraform Plan & State Analysis** | HCL module design, plan risk analysis, ALB TLS policy and WAF review | `references/security-guide.md`, `scripts/tf_plan_analyzer.py` |
| **Packer & Machine Image Builders** | Golden AMI, Azure Image Builder, Windows images, container registry push | `references/aws-ami-builder.md`, `references/azure-image-builder.md`, `references/windows-builder.md`, `references/push-to-registry.md` |
| **PKI & Certificate Lifecycle** | Public TLS validity limits (200/100/47 days), ACME, cert-manager, rotation automation | `references/pki-guide.md` |
| **On-Prem Provisioning** | On-prem VMs: Terraform creates, Ansible configures (Proxmox example) | `references/on-prem-provisioning.md` |
