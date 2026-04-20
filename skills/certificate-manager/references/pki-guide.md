# PKI Management Specialist

This guide provides instructions for experts in SSL/TLS Certificate Lifecycle Management.

## Capabilities
- **Onboarding**: Automating certificate creation and deployment using tools like `nitsslman`.
- **Validation**: Verifying certificate chains and trust roots.
- **Renewal**: Monitoring and automating the replacement of expiring certificates.

## Implementation Workflow (nitsslman)
1.  **Configuration**: Define certificate requirements in the `config` library (FQDN, SANs, Type: haproxy/keystore).
2.  **Request Initiation**: Ensure JIRA or Service requests include:
    - **Ownership**: Service name, Manager, PagerDuty group.
    - **Vault Details**: Target cluster ID (nonprod/prod), Namespace, and Secret Engine path.
3.  **Deployment**: Verify that ArgoCD or Puppet re-triggers to pick up the new secret from Vault.

## Maintenance
- **Rotation**: Rotate certificates every 13 months (397 days) max.
- **Revocation**: Trigger revocation for compromised keys immediately.