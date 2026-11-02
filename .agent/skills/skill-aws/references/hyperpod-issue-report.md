# HyperPod Issue Report

Collect diagnostic logs from HyperPod cluster nodes via SSM, store results in S3. Supports both EKS and Slurm clusters with auto-detection. Collects over SSM node by node.

## Prerequisites

- AWS CLI configured with permissions: `sagemaker:DescribeCluster`, `sagemaker:ListClusterNodes`, `ssm:StartSession`, `s3:PutObject`, `s3:GetObject`, `eks:DescribeCluster`
- SSM Agent running on target nodes; node IAM roles need `s3:GetObject`/`s3:PutObject` on the report bucket
- For EKS clusters: kubectl installed and configured (see Workflow step 2)

## Workflow

### 1. Gather Information

Collect from the user:

- **Cluster identifier** (required): accepts cluster name or full cluster ARN (e.g., `arn:aws:sagemaker:us-west-2:123456789012:cluster/abc123`)
- **AWS region** (required unless extractable from ARN)
- **S3 path** for report storage (required, e.g. `s3://bucket/prefix`). If the user doesn't have a bucket, create one (e.g., `s3://hyperpod-diagnostics-<account-id>-<region>`)
- **Issue description** (optional)
- **Target scope**: all nodes, specific instance groups, or specific node IDs (optional)
- **Additional commands** to run on nodes (optional)

### 2. Verify Environment

```bash
aws sts get-caller-identity
aws sagemaker describe-cluster --cluster-name <name-or-arn> --region <region>
```

If the S3 bucket doesn't exist, create it:

```bash
aws s3 mb s3://<bucket-name> --region <region>
```

**For EKS clusters** (check `Orchestrator.Eks` in describe-cluster output):

1. Ensure kubectl is installed (`which kubectl`). If missing, install it for the current platform.
2. Configure kubeconfig using the EKS cluster name from the describe-cluster response:

   ```bash
   aws eks update-kubeconfig --name <eks-cluster-name> --region <region>
   ```

### 3. Collect Diagnostics

The bundled collection script is not part of this repo. Collect per node over SSM, following `hyperpod-ssm.md` (resolve the cluster ID and nodes once, then one `aws ssm start-session` per node, within the 3 TPS limit). Suggested read-only commands per node:

- `cat /var/log/provision/provisioning.log` (lifecycle logs)
- `nvidia-smi`, `df -h && lsblk`, `free -h` (GPU, disk, memory)
- `sudo journalctl -u amazon-cloudwatch-agent --since "-1h"` (agent)

Write results to the S3 path from step 1 with `aws s3 cp` run on the node, and report the S3 location.

### 4. Present Results

Report the S3 location and offer to:

- Download the report locally
- Help analyze the collected diagnostics
- Prepare a summary for AWS Support
