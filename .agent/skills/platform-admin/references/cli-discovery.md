# CLI Discovery & Environmental Reconnaissance

This guide provides instructions for experts at exploring unknown or complex CLI environments. You do not rely solely on static knowledge; you use the tools to "learn" the environment and the APIs you are working with.

## The Discovery Protocol

### Phase 1: Help Tree Exploration
If you are unsure of a command's capability, explore the help tree recursively.
1. **Root Discovery**: `[tool] --help` to see high-level groups.
2. **Component Discovery**: `[tool] [group] --help` to see specific resources.
3. **Action Discovery**: `[tool] [group] [resource] --help` to see available verbs (list, describe, create, update).

### Phase 2: Schema Discovery
To understand the structure of a resource without a manual:
1. **List Resources**: `[tool] [group] [resource] list --limit=1`
2. **Describe Schema**: Use `--format=json` or `--format=yaml` to see the full object structure.
3. **Analyze Fields**: Capture the output and analyze the hierarchy to identify key fields (e.g., status, metadata, spec).

### Phase 3: Environment Reconnaissance
Map the current state before taking action:
- **Project/Context**: `gcloud config get-value project` or `kubectl config current-context`.
- **Active Resources**: `gcloud compute instances list` or `aws ec2 describe-instances --max-items 5`.
- **Identity check**: `gcloud auth list` or `aws sts get-caller-identity`.

## Operational Principles
1. **Trust-but-Verify**: Always use `list` or `describe` to verify that a resource exists before attempting to modify it.
2. **Recursive Strategy**: If a command fails with "Invalid Argument", immediately run the `--help` flag for that specific command to check for syntax changes in the local CLI version.
3. **Dynamic Documentation**: Use discovered help text to refine your understanding of "Best Practices" for a specific CLI version.