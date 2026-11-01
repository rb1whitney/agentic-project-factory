---
name: skill-aws
description: Comprehensive AWS Cloud expert focusing on Well-Architected Framework audits and dynamic CLI resource discovery.
---
# Skill: AWS Cloud Architecture & Operations (`skill-aws`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: aws-cloud-architecture-audit] parent=skill-aws required_inputs=['skill_dir', 'aws_service']
ls {skill_dir}/references/ 2>/dev/null | bin/rtk
aws sts get-caller-identity | bin/rtk
aws {aws_service} help 2>/dev/null | head -n 30 | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_aws_workflow(skill_dir, aws_service):
  1. PRE-CHECK: AWS credentials sourced via environment or gopass; Read-only describe/list calls first
  2. result <- invoke(aws-cloud-architecture-audit, {skill_dir: "<skill_dir>", aws_service: "<aws_service>"})
  3. POST-CHECK: Blast radius and cost delta documented before state mutation
  4. RETURN {Location, Problem, Fix, outputs: ['reference_file', 'aws_management_plan']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: aws-cloud-architecture-audit`**
  - `trigger`: AWS capability reference guide and skill_dir references management for foundation, serverless, sagemaker, migration, and finops
  - `inputs`: required `['skill_dir', 'aws_service']`, optional `['aws_region']`
  - `outputs`: `['reference_file', 'aws_management_plan']`
  - `preconditions`: AWS credentials sourced via environment or gopass; Read-only describe/list calls first
  - `postconditions`: Blast radius and cost delta documented before state mutation
  - `side_effects`: filesystem=none, network=read-only AWS API describe/list
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute AWS capability reference guide lookups and `skill_dir` `references` management across foundation (`iam`, `vpc`, `ec2`, `rds`, `s3`), serverless (`lambda`, `api-gateway`, `amplify`, `dsql`), `sagemaker` (`hyperpod`, `finetuning`), `migration`, and `finops` domains before proposing any `aws_management_plan` for target `aws_service` or `aws_region`.

### 1. Discovery & Verification Gate
- Run read-only discovery via `{SKILL_DIR}/scripts/aws_discovery.sh` or `aws sts get-caller-identity | bin/rtk` before state changes.
- Verify target account, `aws_region`, VPC CIDR, and KMS encryption posture before running `terraform` or CDK mutations.
- Run source-level 6-Pillar checks when auditing application or IaC code:
  ```bash
  bash .agent/skills/skill-aws/scripts/aws_discovery.sh | bin/rtk
  aws s3api list-buckets --query 'Buckets[*].Name' | bin/rtk
  aws ec2 describe-vpcs --query 'Vpcs[*].{ID:VpcId,CIDR:CidrBlock}' --output table | bin/rtk
  /usr/bin/python3 .agent/skills/skill-code-map/scripts/well_architected_audit.py <target_dir> | bin/rtk
  ```

### 2. Architectural Hard Rules
- **Zero-Trust Networking**: Backend workloads require private subnets, VPC Endpoints / PrivateLink, or VPC Lattice; never assign public IPs to data or compute tiers.
- **Encryption & Identity**: Enforce KMS Customer Managed Keys (CMK) at rest and IAM Identity Center / short-lived role assumption (`gopass` or environment credentials only).
- **Serverless & Observability**: Require CloudWatch Embedded Metric Format (EMF), X-Ray tracing, and idempotent replay rules on durable Lambda and Step Functions workflows.

## Reference & Script Routing Index

Select the target `reference_file` under `{SKILL_DIR}/references/` or `{SKILL_DIR}/scripts/` based on task domain:

| Capability Domain | Trigger / Scope | Reference Runbooks & Scripts (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **Account & CLI Discovery** | Active caller identity, region, VPC/S3 inventory | `scripts/aws_discovery.sh`, `references/directory-management.md` |
| **Foundation (IAM, VPC, EC2, RDS, S3)** | Least-privilege IAM, VPC Lattice/Endpoints, EC2, RDS, S3 | `references/aws-foundation.md`, `references/iam-identity.md`, `references/iam-guide.md`, `references/vpc-networking.md`, `references/networking-guide.md`, `references/ec2-guide.md`, `references/rds-guide.md`, `references/s3-storage.md` |
| **Well-Architected & FinOps** | 6-Pillar review, cost optimization, cloud migration | `references/well-architected.md`, `references/finops.md`, `references/aws-migration.md`, `references/design-refs/` |
| **Serverless & Lambda** | Event-driven Lambda, durable execution, Step Functions, SAM/CDK | `references/aws-serverless.md`, `references/serverless-excellence.md`, `references/lambda-guide.md`, `references/lambda-durable-guide.md`, `references/lambda-step-functions.md`, `references/deployment-guide.md` |
| **API Gateway** | REST/HTTP/WebSocket APIs, auth, custom domains, limits, observability | `references/api-gateway-guide.md`, `references/api-gateway-architecture-patterns.md`, `references/api-gateway-authentication.md`, `references/api-gateway-security.md`, `references/api-gateway-troubleshooting.md` |
| **SageMaker & HyperPod** | Model fine-tuning, dataset evaluation, HyperPod EKS/Slurm clusters | `references/aws-sagemaker.md`, `references/finetuning.md`, `references/dataset-evaluation.md`, `references/model-deployment.md`, `references/hyperpod-ssm.md`, `references/clustering/`, `references/phases/` |
| **Specialized Services** | Amplify full-stack workflows, Aurora DSQL, Amazon Location Service | `references/amplify-workflow/guide.md`, `references/dsql/`, `references/location-service/` |
