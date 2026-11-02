# AWS SageMaker, Model Customization & HyperPod Index

Domain index for Amazon SageMaker fine-tuning, dataset preparation, model evaluation, deployment, and HyperPod clusters.

## SageMaker & HyperPod Runbook Index

| Capability | When to Read | Runbook Path (`.agent/skills/skill-aws/`) |
| :--- | :--- | :--- |
| **Use-Case Specification** | Scope model customization goals, latency/accuracy targets, and technique selection | `references/use-case-specification.md` |
| **Dataset Evaluation** | Audit training/validation dataset quality, schema, and token distribution | `references/dataset-evaluation.md` |
| **Dataset Transformation** | Convert raw corpora into JSONL/ChatML/preference formats for SFT/DPO/RLVR | `references/dataset-transformation.md` |
| **Fine-Tuning Setup** | Configure IAM roles, S3 buckets, VPC subnets, and training environment prerequisites | `references/finetuning-setup.md` |
| **Fine-Tuning Execution** | Run LoRA / full SFT, DPO, or RLVR training jobs on SageMaker | `references/finetuning.md` |
| **Model Evaluation** | Evaluate fine-tuned checkpoints using LLM-as-a-Judge and benchmark suites | `references/model-evaluation.md` |
| **Model Deployment** | Deploy custom weights to SageMaker Real-Time Endpoints or Amazon Bedrock | `references/model-deployment.md` |
| **Project Directory Layout** | Standard workspace layout for dataset, training, and evaluation artifacts | `references/directory-management.md` |
| **HyperPod SSM & Access** | Connect to SageMaker HyperPod EKS/Slurm nodes via AWS Systems Manager | `references/hyperpod-ssm.md` |
| **HyperPod Version Checker** | Audit AMI, EKS, and driver versions across HyperPod instance groups | `references/hyperpod-version-checker.md` |
| **HyperPod Issue Reporting** | Collect cluster logs, node health, and NCCL diagnostics for triage | `references/hyperpod-issue-report.md` |

## Standard Execution Sequence

1. **Specify & Audit Data**: Read `references/use-case-specification.md` -> `references/dataset-evaluation.md` -> `references/dataset-transformation.md`.
2. **Provision & Train**: Read `references/finetuning-setup.md` -> `references/finetuning.md` (or `references/hyperpod-ssm.md` for HyperPod clusters).
3. **Evaluate & Deploy**: Read `references/model-evaluation.md` -> `references/model-deployment.md`.
