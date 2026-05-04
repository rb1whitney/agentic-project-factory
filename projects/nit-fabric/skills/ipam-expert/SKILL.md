---
name: ipam-expert
description: Bit-mask algebra expert for VPC CIDR disjointness verification.
---
# IPAM Expert (nit-fabric Skill)

This skill provides a deterministic IP Address Management (IPAM) controller.

## Logic Overview
- **Verification**: Uses Python `ipaddress` to prove disjointness between sets of network ranges.
- **Algebra**: Prevents CIDR fragmentation by enforcing regional parent block contiguity.

## Usage
```python
from skills.ipam_expert import logic
logic.verify_disjointness(...)
```