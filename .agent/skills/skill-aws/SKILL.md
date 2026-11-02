---
name: skill-aws
description: Comprehensive AWS Cloud expert focusing on Well-Architected Framework audits and dynamic CLI resource discovery.
---
# Skill: AWS Cloud Architecture & Operations (`skill-aws`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: aws-cloud-architecture-audit] parent=skill-aws required_inputs=['aws_service']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
aws sts get-caller-identity | bin/rtk
aws {aws_service} help 2>/dev/null | head -n 30 | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_aws_workflow(aws_service):
  1. PRE-CHECK: AWS credentials sourced via environment or gopass; Read-only describe/list calls first
  2. result <- invoke(aws-cloud-architecture-audit, {aws_service: "<aws_service>"})
  3. POST-CHECK: Blast radius and cost delta documented before state mutation
  4. RETURN {Location, Problem, Fix, outputs: ['reference_file', 'aws_management_plan']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: aws-cloud-architecture-audit`**
  - `trigger`: AWS capability reference guide and runbook routing for foundation, serverless, sagemaker, migration, and finops
  - `inputs`: required `['aws_service']`, optional `['aws_region']`
  - `outputs`: `['reference_file', 'aws_management_plan']`
  - `preconditions`: AWS credentials sourced via environment or gopass; Read-only describe/list calls first
  - `postconditions`: Blast radius and cost delta documented before state mutation
  - `side_effects`: filesystem=none, network=read-only AWS API describe/list
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails (Tier 1B Knowledge-Router Parent)

Execute read-only AWS CLI account discovery (`aws_service`, `aws_region`) and 6-Pillar Well-Architected static audits (`target_dir`) to produce `caller_identity`, `audit_findings`, and `aws_management_plan`. Route service-specific design and implementation through the **2-Hop Hierarchical Reference Index** below (`SKILL.md -> Domain Index/Guide -> Leaf Runbook`).

### 1. Discovery & Verification Gate
- Run read-only discovery via `.agent/skills/skill-aws/scripts/aws_discovery.sh` or `aws sts get-caller-identity | bin/rtk` before state changes.
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

## Reference & Script Routing Index (2-Hop Hierarchical Lookup)

Every runbook in `.agent/skills/skill-aws/references/` is reachable in **1 hop** (leaf runbook) or **2 hops** (via the Domain Index / Guide):

| Capability Domain | Trigger / Scope | Hop-1 Runbook / Domain Index (`.agent/skills/skill-aws/`) |
| :--- | :--- | :--- |
| **Account & CLI Discovery** | Active caller identity, region, VPC/S3 inventory | `scripts/aws_discovery.sh`, `references/sagemaker-project-directory.md` |
| **Foundation (IAM, VPC, S3) & Well-Architected** | Least-privilege IAM, VPC Lattice/Endpoints, S3, 6-Pillar review, service design refs | `references/iam-identity.md`, `references/vpc-networking.md`, `references/s3-storage.md`, `references/well-architected.md`, `references/architecture-docs.md`, `references/design-refs/index.md` |
| **Serverless, Lambda & Durable Execution** | Event-driven Lambda (`11` leaf guides), durable execution (`11` leaf guides), CDK/SAM (`5` leaf guides) | `references/serverless-excellence.md`, `references/lambda-development-index.md`, `references/lambda-durable-guide.md`, `references/deployment-cdk-sam-index.md` |
| **API Gateway** | REST/HTTP/WebSocket APIs, auth, custom domains, limits, observability (`18` leaf guides) | `references/api-gateway-guide.md` |
| **SageMaker, Fine-Tuning & HyperPod** | Dataset eval/transform, SFT/DPO/RLVR fine-tuning, model eval/deploy, HyperPod (`11` leaf guides) | `references/sagemaker-index.md` |
| **GCP-to-AWS 5-Phase Migration** | Discover, clarify, cluster Terraform, design, estimate, execute (`22` leaf guides) | `references/aws-migration.md` |
| **Amplify Gen 2, Aurora DSQL & Location Service** | Full-stack Amplify (`3` leaf guides), Aurora DSQL (`24` leaf guides), Location Service (`6` leaf guides) | `references/amplify-workflow/guide.md`, `scripts/amplify-prereq-check.sh`, `references/dsql/guide.md`, `references/location-service/guide.md` |
