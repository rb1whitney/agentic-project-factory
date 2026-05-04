---
name: remediation-ops
description: Workflow for deterministic remediation and patch validation.
---
# Remediation Ops (Deterministic Enforcement)

Use this skill to generate, validate, and apply surgical HCL patches to resolve connectivity and security violations identified during discovery.

## Operational Workflow

### 1. Generate Patches
Run the remediation engine to produce HCL diffs based on the latest truth-report.
```bash
./bin/nit-fabric remediate
```

### 2. Validate Patches (Dry-Run)
Always use the `--validate` flag to perform a simulated `terraform plan` on the generated patches.
```bash
./bin/nit-fabric remediate --validate
```
*Mandatory: Flag any destructive actions (resource deletion) for human review.*

### 3. Apply Remediations
Present the validated HCL patch to the user. Do NOT apply changes automatically unless explicitly authorized.

## Safety Protocols
- **Mathematical Integrity**: Ensure patches do not introduce new CIDR overlaps.
- **Regional Sovereignty**: Verify that resources are confined to the approved primary/secondary regions.
