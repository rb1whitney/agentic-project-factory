# GCP Reference: Security Foundations & Hardening

Following the Google Cloud Architecture Framework: Security, Privacy, and Compliance.

## 1. Identity and Access Management (IAM)
- **Principle of Least Privilege (PoLP)**: Only grant necessary permissions. Use predefined or custom roles instead of primitive ones (Owner/Editor).
- **Service Accounts**: Use dedicated service accounts for applications. Never share service accounts between different tiers.
- **Workload Identity Federation**: The GOLD standard for GKE and external workloads to access GCP APIs without keys.

## 2. Networking Security
- **Shared VPC**: Centralizes network management and security policy enforcement.
- **Firewall Rules**: Use "Deny All" by default and allow specific traffic using Network Tags or Service Accounts.
- **Cloud Armor**: Protects against DDoS and WAF threats at the global load balancer.
- **Private Google Access**: Allows private nodes to access Google APIs without a public IP.

## 3. Data Protection
- **CMEK (Customer Managed Encryption Keys)**: Use Cloud KMS to manage your own keys for data at rest across GCS, BigQuery, and GCE.
- **Secret Manager**: Secure storage for API keys, passwords, and certificates.
- **VPC Service Controls**: Creates a security perimeter to prevent data exfiltration.

## 4. Hierarchy Policies
- **Organization Policies**: Enforce account-level guardrails (e.g., "Restrict Public IP addresses", "Enforce CMEK").