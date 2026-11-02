# AWS Application & Serverless Deployment Index (CDK & SAM)

 Take any application and deploy it to AWS with minimal user decisions, dev-sized cost defaults, and shift-left IaC security checks (`cfn-nag`, `checkov`).

## Deployment & IaC Runbook Index

| Capability | When to Read | Runbook Path (`.agent/skills/skill-aws/`) |
| :--- | :--- | :--- |
| **CDK Project Setup** | Bootstrapping AWS CDK apps, stacks, environments, and TypeScript/Python layout | `references/deployment-cdk-project-setup.md` |
| **CDK Lambda Constructs** | Packaging Lambda functions, layers, destinations, and permissions in CDK | `references/deployment-cdk-lambda-constructs.md` |
| **CDK Serverless Patterns** | EventBridge, Step Functions, SQS, DynamoDB, and API Gateway CDK patterns | `references/deployment-cdk-serverless-patterns.md` |
| **SAM Project Setup** | AWS SAM `template.yaml` scaffolding, `sam build`, and local invocation | `references/deployment-sam-project-setup.md` |
| **SAM & CDK Coexistence** | Using SAM CLI local testing with CDK stacks or migrating between SAM and CDK | `references/deployment-sam-cdk-coexistence.md` |
| **Service Architecture Refs** | Compute, database, networking, messaging, storage, and AI design rules | `references/design-refs/index.md` |

## Core Deployment Workflow

1. **Analyze**: Scan codebase for runtime framework, database, and event dependencies.
2. **Recommend & Estimate**: Select target AWS services using `references/design-refs/index.md` and estimate monthly cost before generating IaC.
3. **Synthesize & Audit**: Generate CDK or SAM templates with encryption at rest, private subnets, and least-privilege IAM.
