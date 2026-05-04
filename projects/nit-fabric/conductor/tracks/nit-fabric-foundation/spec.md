# Technical Spec: nit-fabric-foundation (Phase 1)

**Mission**: Instantiating the deterministic Hub-and-Spoke TGW foundation.

##  Technical Architecture
- **Provider Aliasing**: AWS us-east-1 (Primary) and GCP us-central1 (Secondary).
- **TGW Foundation**: Regional Transit Gateway with isolated route tables.
- **IPAM Math**: Non-overlapping CIDR verification for AWS VPC and GCP VPC.

##  Industrial Safety
1. **Live-State Refresh**: `nit-fabric` must execute state-verification before attachment.
2. **Deterministic Validation**: ASN range check to prevent collisions with legacy Direct Connect.