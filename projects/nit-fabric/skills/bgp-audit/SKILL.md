---
name: bgp-audit
description: Multi-Cloud BGP status auditing and identity verification.
---
# BGP Audit (nit-fabric Skill)

This skill audits the health and identity of cross-cloud BGP peering sessions.

## Logic Overview
- **Liveness**: Checks for ESTABLISHED stated in Cloud API.
- **Identity**: Verifies ASN alignment (No ibgp leakage).