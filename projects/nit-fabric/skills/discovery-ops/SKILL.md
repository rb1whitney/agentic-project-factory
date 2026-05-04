---
name: discovery-ops
description: Instructions for executing and interpreting Live-Truth discovery scans.
---
# Discovery Ops (Live-Truth Sync)

Use this skill to perform real-time audits of cloud infrastructure and identify drift between the factory's desired state and the cloud reality.

## Operational Workflow

### 1. Execute Discovery
Run the master CLI with the `--live` flag to fetch real-time metadata from AWS and GCP.
```bash
./bin/nit-fabric scan --live
```
*Note: Use `--mock` if cloud credentials are not available for testing.*

### 2. Interpret Results
The scanner will output structured JSON logs. Look for:
- `[ALERT] CRITICAL VIOLATION`: Immediate security risks (Public S3, Overlapping CIDRs).
- `Violation detected`: Best practice deviations (Missing VPC Endpoints, External IPs).

### 3. Handoff
Once discovery is complete, proceed to the `remediation-ops` skill to resolve identified violations.
