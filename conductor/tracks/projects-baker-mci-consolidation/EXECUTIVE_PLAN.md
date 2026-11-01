# Executive Plan: Projects Consolidation (`baker` & `managed-cloud-infra`)

## 1. Strategic Objective
Consolidate 8 overlapping projects in `projects/` into **2 standalone Flagship Hubs** guided by Graphify AST/IaC/K8s topology mapping:
1. **[`projects/baker`](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/projects/baker/)**: Absorbs `project-baker` (Canary locale refactor + regional `X-Request-Id` tracing), `project-crumbs` (CloudEvents cross-cloud worker mesh + `X-Message-Origin` + stateful `message_id` deduplication ledger), and `project-muffin` (Hard-Block vs. Soft-Block OPA/Vault/IAM security policy engine).
2. **[`projects/managed-cloud-infra`](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/projects/managed-cloud-infra/)**: Absorbs `multi-cloud-container` (Karpenter/EKS Blueprints, GKE Hub Fleet Membership & ConfigSync, cross-cloud `boundary_rules.tf`, `envs/{dev,prod}.tfvars`, and `gitops-fleet/` 3-tier layout), `cluster-forge` (`--cluster-size`, `--apps`, `--disabled-apps` bootstrap flags and `docs/kyverno_modular_design.md`), and `multicloud-k8s-iac` (`modules/aws/bedrock-kb/`).

## 2. TDD Verification Gates
- **Gate 1 (`projects/baker`)**: `pytest projects/baker/tests/` verifies Scanner, Auditor, Generator, Refactor Safety Canary Gate, Crumbs Deduplication/CloudEvents Engine, and Muffin Policy Evaluator.
- **Gate 2 (`projects/managed-cloud-infra`)**: `pytest projects/managed-cloud-infra/tests/` verifies consolidated Terraform modules, `.tfvars` bindings, GitOps fleet manifests, Bedrock KB module, and `bin/bootstrap.sh` CLI flags.
- **Gate 3 (Graphify Re-Extraction)**: Re-run `.agent/skills/skill-graphify/scripts/graph_builder.py --format graphify` on both flagship hubs to confirm increased node/edge density and zero broken references.
