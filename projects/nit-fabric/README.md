# nit-fabric | Multi-Cloud Network Auditor

A tool for auditing and fixing connectivity issues across AWS and GCP. It helps prevent CIDR overlaps and ensures security best practices are followed.

## Features
- **CIDR Validation**: Prevents overlapping IP ranges across clouds.
- **Discovery**: Queries AWS/GCP APIs to see what's actually running.
- **Remediation**: Generates shell scripts or Terraform patches to fix findings.
- **Advisor Mode**: Explains what's wrong and how to fix it manually.
- **Security Checks**: Audits S3 buckets, GKE clusters, and Firewall rules.

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run a scan**:
   ```bash
   # Make sure you have aws/gcloud credentials configured
   ./bin/nit-fabric scan --mode cli
   ```

3. **See findings & advice**:
   ```bash
   ./bin/nit-fabric remediate --explain
   ```

4. **Generate a fix script**:
   ```bash
   ./bin/nit-fabric remediate --provider cli > fix.sh
   ```

## Workflow
The tool works in three stages:
1. **Discover**: Pulls data from cloud APIs (or local mock for testing).
2. **Scan**: Runs the data through a set of rules defined in `bin/policies.yaml`.
3. **Fix**: Proposes ways to repair the violations.

## Troubleshooting Common Issues

| Issue | Likely Cause | Fix |
| :--- | :--- | :--- |
| BGP Session Down | ASN Mismatch | Run `./bin/nit-fabric remediate --explain` to check ASNs. |
| Packet Loss | MTU Issues | Ensure tunnel MTU is set to 1440. |
| CIDR Conflict | Overlapping Subnets | Check `docs/ARCHITECTURE.md` for IPAM principles. |
| Discovery Failure | Auth Error | Run `aws sts get-caller-identity` to check credentials. |

## TODO / Known Issues
- [ ] GCP discovery is still a bit basic (need to add more resource types).
- [ ] Terraform provider needs better error handling for complex HCL.
- [ ] Add support for Azure (long term).
- [ ] Performance: O(n^2) CIDR check is slow if you have 1000+ subnets.

## Documentation
- [Architecture](docs/ARCHITECTURE.md)
- [Technical Decisions](docs/DECISIONS.md)