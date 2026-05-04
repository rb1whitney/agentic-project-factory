# nit-fabric Architecture

**Status**: Work in Progress | **Version**: 0.10.0

## Overview
**nit-fabric** is a Python-based utility for managing network connectivity in multi-cloud environments. It focuses on ensuring subnets don't overlap and that security rules are consistently applied across AWS and GCP.

## System Components

### 1. Discovery Layer (The Truth)
The discovery layer uses the AWS and Google Cloud CLI tools to fetch current network state. 
- **Design Choice**: We query the AWS/GCP APIs directly instead of relying solely on Terraform state files. This allows the tool to detect "out-of-band" changes and drift that occurred outside of IaC.
- **Output**: Generates a `context.json` file used as the "Live Truth" source for the scanner.

### 2. Policy Engine (The Logic)
A rules-based engine that evaluates the `context.json` against policies defined in `bin/policies.yaml`.
- **Deterministic Approach**: We use a strictly rules-based engine rather than an LLM for remediation analysis. Network configurations require 100% predictability; identical inputs must always produce identical results.
- **Algebraic IPAM**: The engine performs an O(n^2) overlap check across all cloud and on-prem pools using the standard `ipaddress` library.
- **Generic Abstractions**: To avoid code bloat, we use generic classes like `ResourceAttributePolicy`. This allows us to add most new security checks just by updating the YAML configuration.

### 3. Remediation & Advice
Generates "Tactical" fixes (shell commands) or "Strategic" fixes (Terraform patches).
- **Template-Based**: Uses Jinja2 to format the output, ensuring fixes are modular and reusable.
- **Advisor Mode**: Includes an `--explain` flag. Sometimes an SRE doesn't need a script; they need an explanation. In this mode, the tool provides a plain-text guide on why a violation occurred and how to fix it.

## Networking Best Practices
These standards are enforced by the engine across all multi-cloud links:
- **BGP Peering**: We use BGP with private ASNs (AWS: 64512, GCP: 64600) for all VPN/Interconnect links. This is preferred over static routing for faster failover and easier scaling.
- **MTU 1440**: All cross-cloud VPN tunnels are standardized at 1440 MTU to avoid packet fragmentation caused by IPSec overhead.
- **Route Summarization**: To keep routing tables manageable, we advertise aggregate blocks (e.g., /16) instead of individual subnets.

## Operational Principles
- **Isolation**: AWS and GCP configurations are kept separate to minimize the blast radius of any single change.
- **Manual Oversight**: The tool identifies and proposes fixes, but it never applies them automatically. Final execution is always a human decision.

## Future Improvements
- Moving from CLI-based discovery to native SDKs (Boto3/Google Cloud SDK).
- Better integration with CI/CD pipelines.
- Adding a web UI for visualizing the network graph.