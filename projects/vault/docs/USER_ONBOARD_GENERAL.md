# Clover Vault Enterprise Namespace Management

This document outlines Clover's approach to secret management using HashiCorp Vault Enterprise and namespaces, aligning with vendor best practices for enhanced security and operational efficiency.  We leverage Vault Namespaces to provide isolated environments for each team, promoting better security and reducing the blast radius of potential incidents.  This approach enhances both security and operational efficiency.

**Why Namespaces?**

Adopting a namespace-based model for Vault offers several key advantages:

* **Enhanced Security:**  Namespaces provide strong isolation between teams, preventing accidental or malicious access to sensitive data belonging to other teams. This minimizes the impact of security breaches and simplifies auditing.
* **Improved Operational Efficiency:** Team-specific delegated administrators manage their own namespaces, reducing the burden on central Vault system administrators. This allows for faster onboarding and more agile responses to team needs.
* **Compliance:** Namespaces help meet compliance requirements by enforcing stricter access controls and providing clear accountability for secret management within each team.
* **Vendor Best Practices:** This approach aligns with HashiCorp's recommended practices for managing large-scale deployments of Vault, ensuring scalability and maintainability.


**Namespace Structure and Components:**

Each team receives its own namespace, functionally a "Vault within a Vault." These namespaces are completely isolated and contain:

* **Secret Engines:** Mechanisms to store and generate secrets (e.g., key/value, Transit, database, GCP secrets).  Most teams will start with key/value and then transition to more advanced dynamic secret engines as needed.
* **Authentication Methods:** Define how clients authenticate (e.g., LDAP, AppRole, Cert, GCP, Kubernetes).  Human and application server authentication will typically use different methods.
* **Policies:** Access Control Lists (ACLs) defining permissions for each identity.  Policies should be granular, granting either read/list or create/update/delete access, not both.
* **Identities (Entities, Groups):**  Specific instances managed under authentication methods that grant Vault access. Entities and groups are created upon client login, tied to a token.
* **Tokens:** Short-lived tokens granting access; tied to an identity and revoked upon expiration.
* **Secrets:** The sensitive information managed within the namespace.

Delegated administrators can manage their namespaces and create child namespaces, further enhancing granular control and delegation. Child namespaces can inherit policies from their parent namespaces.


**Important Considerations:**

* **Production Changes:** Application teams remain subject to existing processes for modifying secrets in production clusters.  All changes require proper review and approval.
* **Understanding Definitions:** Teams must understand the above definitions to effectively manage their namespaces.

**Onboarding Process:**

Teams onboard a new namespace by creating a pull request to the Vault source repository or requesting admin assistance.  This involves modifying the Vault configuration files:

1. **Create Namespace:** Modify `json_workspace/<<environment>>/admin/_namespace.json` (example: [https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/admin/_namespaces.json](https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/admin/_namespaces.json)). Add a new entry with a unique namespace name:

```json
{
    "api_path": "v1/sys/namespaces/<<namespace_name>>",
    "api_action": "post",
    "api_payload": {}
}
```

2. **Configure Namespace:** Create a namespace folder and default configuration under `json_workspace/<<environment>>/namespace/<<namespace>>`. (example: [https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/namespaces/kubernetes/](https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/namespaces/kubernetes/)).  This includes configuring authentication methods, policies, and initial secrets.  An example `_auth.json` file is provided below.

```json
{
  "_namespace": "<<namespace_name>>",
  "api_paths": [
    {
      "api_path": "v1/sys/auth/ldap",
      "api_action": "post",
      // ... LDAP configuration ...
    },
    {
      "api_path": "v1/sys/policy/namespace-manager",
      "api_action": "post",
      // ... Policy configuration ...
    },
    // ... other auth methods and configurations ...
  ]
}
```

**(Example `_auth.json` with LDAP,  replace placeholders with your actual values):**

```json
{
  "_namespace": "<<namespace_name>>",
  "api_paths": [
    {
      "api_path": "v1/sys/auth/ldap",
      "api_action": "post",
      "api_payload": {
        "description": "Enable Default LDAP Auth Method",
        "type": "ldap",
        "config": {
          "default_lease_ttl": "30m",
          "max_lease_ttl": "60m"
        }
      }
    },
    {
      "api_path": "v1/auth/ldap/config",
      "api_action": "post",
      "api_payload": {
        "binddn": "cn=binduser,dc=clover,dc=com",
        "case_sensitive_names": false,
        // ... rest of LDAP configuration ...
      }
    },
    {
      "api_path": "v1/sys/policy/namespace-manager",
      "api_action": "post",
      "api_payload": {
        "path": {
          "*": {
            "capabilities": [
              "create",
              "read",
              "update",
              "delete",
              "list",
              "sudo"
            ]
          },
          "sys/mounts/kub-admin": {
            "capabilities": ["read", "list", "create", "update", "delete"]
          },
          "sys/mounts/kub-secrets": {
            "capabilities": ["read", "list", "create", "update", "delete"]
          }
        }
      }
    },
		// ... other auth method and user/group mappings ...
  ]
}
```

**(Example JSON for Puppet TLS Access - replace placeholders with your actual values):**

```json
{
  "_namespace": "<<namespace_name>>",
  "api_paths": [
    {
      "api_path": "v1/sys/auth/puppet_tls",
      "api_action": "post",
      "api_payload": {
        "description": "Enable Global Puppet Certificate Auth Method",
        "type": "cert"
      }
    },
		// ...rest of Puppet TLS configuration...
  ]
}
```


3. **Deploy Changes:** Follow the "How do I deploy data into Vault" guide.  Namespace creation targets the root namespace (e.g., `nonprod/admin/_namespaces.json`), while configuration targets the new namespace (e.g., `nonprod/namespaces/kub_poc`).


**Do's and Don'ts:**

* **Do:** Use unique namespace names. Deploy changes to the correct namespace, specifying the `_namespace` value in each config.
* **Don't:** Use `sudo` policy access, grant both read/list and create/update/delete privileges in a single policy, expose secrets in plain text (including base64-encoded secrets), access root secret engines, use token-based authentication, exceed 30-minute token TTLs (renew instead), attach policies outside the namespace's available policies, or grant access to secret engines outside the namespace.


**Allowed Authentication Methods:**

* AppRole
* Cert
* GCP
* Kubernetes
* LDAP


By following these guidelines, Clover ensures secure and efficient secret management across all teams while adhering to HashiCorp's best practices.  Consult with NIT for assistance with crafting specific configurations.
