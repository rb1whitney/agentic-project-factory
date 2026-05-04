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

## Architecture & Design

### 1. Discovery Layer (The Truth)
The discovery layer uses the AWS and Google Cloud CLI tools to fetch current network state. 
- **Design Choice**: We query the AWS/GCP APIs directly instead of relying solely on Terraform state. This allows the tool to detect "out-of-band" changes and drift.

### 2. Policy Engine (The Logic)
A rules-based engine that evaluates the `context.json` against policies defined in `bin/policies.yaml`.
- **Deterministic**: We use a strictly rules-based engine rather than an LLM. Network configurations require 100% predictability.
- **Algebraic IPAM**: The engine performs an O(n^2) overlap check using the standard `ipaddress` library.
- **Generic Templates**: To avoid code bloat, we use generic classes like `ResourceAttributePolicy`.

### 3. Networking Best Practices
- **BGP Peering**: We use BGP with private ASNs (AWS: 64512, GCP: 64600) for all cross-cloud links.
- **MTU 1440**: Tunnels are standardized at 1440 MTU to avoid packet fragmentation.
- **Route Summarization**: We advertise aggregate blocks (e.g., /16) to keep routing tables manageable.

## Troubleshooting Common Issues

| Issue | Likely Cause | Fix |
| :--- | :--- | :--- |
| BGP Session Down | ASN Mismatch | Run `./bin/nit-fabric remediate --explain` to check ASNs. |
| Packet Loss | MTU Issues | Ensure tunnel MTU is set to 1440. |
| CIDR Conflict | Overlapping Subnets | Check the overlap output in violations.json. |
| Discovery Failure | Auth Error | Run `aws sts get-caller-identity` to check credentials. |

## TODO / Known Issues
- [ ] GCP discovery is still a bit basic (need to add more resource types).
- [ ] Terraform provider needs better error handling for complex HCL.
- [ ] Add support for Azure (long term).
- [ ] Performance: O(n^2) CIDR check is slow if you have 1000+ subnets.

## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for details on adding new policies and running tests.