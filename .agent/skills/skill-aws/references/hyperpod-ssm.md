# HyperPod SSM Access

## SSM Target Format

Target: `sagemaker-cluster:<CLUSTER_ID>_<GROUP_NAME>-<INSTANCE_ID>`

- `CLUSTER_ID`: Last segment of cluster ARN (NOT the cluster name). Extract via `aws sagemaker describe-cluster` (below).
- `GROUP_NAME`: Instance group name  retrieve via `aws sagemaker list-cluster-nodes` (below).
- `INSTANCE_ID`: EC2 instance ID (e.g., `i-0123456789abcdef0`)

## Resolve the cluster and its nodes (once)

```bash
# CLUSTER_ID is the last segment of the cluster ARN, not the cluster name.
aws sagemaker describe-cluster --cluster-name <name> --region <region> --query ClusterArn --output text | awk -F/ '{print $NF}'
# One row per node: group, instance ID, status. The CLI paginates list-cluster-nodes automatically.
aws sagemaker list-cluster-nodes --cluster-name <name> --region <region> \
  --query 'ClusterNodeSummaries[].[InstanceGroupName,InstanceId,InstanceStatus.Status]' --output text | bin/rtk
```

Build each target as `sagemaker-cluster:<CLUSTER_ID>_<GROUP_NAME>-<INSTANCE_ID>`. Resolve once, then run per node.

## Running Commands Across Many Nodes

SSM `start-session` rate limit: **3 TPS** per account. Plan batch size and delay accordingly.

`aws ssm send-command` does NOT support `sagemaker-cluster:` targets  only `start-session` works.

## Manual SSM Commands

Run a command on a node with `aws ssm start-session` and `AWS-StartNonInteractiveCommand`:

```bash
cat > /tmp/cmd.json << 'EOF'
{"command": ["bash -c 'echo hello && whoami'"]}
EOF

aws ssm start-session \
  --target sagemaker-cluster:{CLUSTER_ID}_{GROUP_NAME}-{INSTANCE_ID} \
  --region REGION \
  --document-name AWS-StartNonInteractiveCommand \
  --parameters file:///tmp/cmd.json
```

Always use a JSON file for `--parameters`  inline parameters break with special characters.

## Common Diagnostic Commands

| Task             | Command                                                        |
| ---------------- | -------------------------------------------------------------- |
| Lifecycle logs   | `cat /var/log/provision/provisioning.log`                      |
| Memory           | `free -h`                                                      |
| Disk/mounts      | `df -h && lsblk`                                               |
| GPU status       | `nvidia-smi`                                                   |
| GPU memory       | `nvidia-smi --query-gpu=memory.used,memory.total --format=csv` |
| EFA/network      | `fi_info -p efa`                                               |
| CloudWatch agent | `sudo systemctl status amazon-cloudwatch-agent`                |
| Top processes    | `ps aux --sort=-%mem \| head -20`                              |

## Key Details

- Default SSM non-interactive user is `root`.
- SSM rate limit: **3 TPS** per account.
- For interactive sessions (rare), omit `--document-name` to get a shell.
- Interactive commands (vim, top) are not supported via `AWS-StartNonInteractiveCommand`.
- Large outputs may be truncated by SSM.
