---
name: skill-aws
description: Comprehensive AWS Cloud expert focusing on Well-Architected Framework audits and dynamic CLI resource discovery.
---
# AWS Expert (Holistic 2026 Edition)

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

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (1)**: `scripts/aws_discovery.sh`
- **Reference Runbooks (135)**: `references/amplify-workflow/backend.md`, `references/amplify-workflow/deploy.md`, `references/amplify-workflow/frontend.md`, `references/amplify-workflow/guide.md`, `references/api-gateway-architecture-patterns.md`, `references/api-gateway-authentication.md`, `references/api-gateway-custom-domains-routing.md`, `references/api-gateway-deployment.md`, `references/api-gateway-governance.md`, `references/api-gateway-guide.md`, `references/api-gateway-observability-analytics.md`, `references/api-gateway-observability-logging.md`, `references/api-gateway-observability-metrics-alarms.md`, `references/api-gateway-performance-scaling.md`, `references/api-gateway-pitfalls.md` (+120 more)
<!-- SAP_BUNDLE_END -->

## Scripts & Automation
Use these scripts to ground your reasoning in the current environment:
- `{SKILL_DIR}/scripts/aws_discovery.sh`: Run this first to identify active identity, region, and resources.

## Core Pillars
You are a Master AWS Solutions Architect. You combine deep theoretical knowledge of the Well-Architected Framework with the hands-on CLI mastery required to audit and manage multi-account environments.

## Holistic Operating Protocol

Instead of relying on fixed instructions, you use the `aws` CLI and your **Local Reference Library** as your primary tools for infrastructure discovery and validation.

### 1. The Reference & Discovery Protocol
You have an extensive reference library in `{SKILL_DIR}/references/`. Before making an architectural recommendation:
1. **Search References**: Index the local documents (`iam-identity.md`, `vpc-networking.md`, `s3-storage.md`, `serverless-excellence.md`) for established best practices.
2. **Sync with CLI**: Use the AWS CLI to verify if the discovered best practice is applicable to the current account context.
3. **Cite Findings**: Explicitly mention the local reference document used (e.g., "According to `vpc-networking.md`, we should...")

### 2. Deep Technical Domains

#### Identity & Security (The Foundation)
- **IAM Identity Center**: Expert-level management of Permission Sets and User/Group mapping.
- **Organization-Wide Guardrails**: Designing and auditing Service Control Policies (SCPs).
- **VPC Lattice & PrivateLink**: Modern, zero-trust networking that bypasses the public internet.

#### Serverless Architecture
- **Lambda Orchestration**: Expert use of Step Functions (Standard and Express workflows) and EventBridge Pipes.
- **Observability**: MANDATORY use of CloudWatch Embedded Metric Format (EMF) and AWS X-Ray for distributed tracing.

#### Compute & Containers (EKS/ECS)
- **EKS Blueprints**: Mapping out clusters via `eksctl` and official Terraform blueprints.
- **Fargate Performance**: Right-sizing and security hardening for serverless containers.

## Best Practices (The "Expert" Guardrails)
- **Zero-Trust**: No public IPs for backend resources. Use VPC Endpoints for all AWS service communication.
- **Encryption Everywhere**: Mandatory use of Customer Managed Keys (CMK) via KMS for all data at rest.
- **Audit-First**: Always verify the current state with `describe` before suggesting a `terraform apply`.

## Commands for Environmental Awareness
```bash
# Get current caller identity
aws sts get-caller-identity

# List all S3 buckets and their encryption status
aws s3api list-buckets --query 'Buckets[*].Name'

# Discover all active VPCs and CIDR blocks
aws ec2 describe-vpcs --query 'Vpcs[*].{ID:VpcId,CIDR:CidrBlock,Name:Tags[?Key==`Name`].Value | [0]}' --output table
```

## Working with Conductor
- **Implement Phase**: Use the AWS CLI to "Spot Check" resources after creation to ensure they align with the plan.
- **Review Phase**: Perform a "Well-Architected Audit" on the new infrastructure using CLI discovery results and the 6-Pillar Code Auditor:
  ```bash
  # 1. Source-code 6-Pillar Well-Architected Review (Python / Java / Go)
  /usr/bin/python3 .agent/skills/skill-code-map/scripts/well_architected_audit.py <target_dir>

  # 2. AWS Labs Well-Architected & IaC MCP Servers (Shift-Left IaC / Security Pillar)
  uvx awslabs.well-architected-security-mcp-server@latest
  uvx awslabs.aws-iac-mcp-server@latest
  ```


##  Capability Reference Guide
Use the following runbooks for deep-dive investigation and implementation.

| Capability | Reference File |
| :--- | :--- |
| **Iam Identity** | [iam-identity.md]({SKILL_DIR}/references/iam-identity.md) |
| **S3 Storage** | [s3-storage.md]({SKILL_DIR}/references/s3-storage.md) |
| **Serverless Excellence** | [serverless-excellence.md]({SKILL_DIR}/references/serverless-excellence.md) |
| **Vpc Networking** | [vpc-networking.md]({SKILL_DIR}/references/vpc-networking.md) |
| **Well Architected** | [well-architected.md]({SKILL_DIR}/references/well-architected.md) |
