# Onboarding Kubernetes Workloads to HashiCorp Vault: A Best Practices Approach

This document outlines the process of onboarding Kubernetes workloads to HashiCorp Vault for secrets management.  This approach replaces alternative methods and adheres to vendor best practices for enhanced security and operational efficiency. We'll use the `platform-example-java-nonprod` service as an example, with all configuration examples located in the Vault repository:

**Repo:** [git@github.corp.clover.com:clover/vault.git](git@github.corp.clover.com:clover/vault.git)


## Why Use This Approach?

This method leverages HashiCorp Vault's capabilities for secure secrets management, improving security posture and operational efficiency by:

* **Centralized Secrets Management:** Consolidates all secrets in a single, secure location, reducing the risk of scattered credentials and improving auditability.
* **Improved Security:** Enhances security by utilizing Vault's encryption, access control, and auditing features, minimizing the risk of unauthorized access to sensitive information.
* **Automation:** Enables automation of secrets provisioning and management, reducing manual effort and improving efficiency.
* **Vendor Best Practices:** Aligns with HashiCorp's recommended approach to Kubernetes secrets management for optimal performance and security.  This approach reduces the attack surface and simplifies management compared to alternatives such as directly embedding secrets in Kubernetes configurations.


## Step-by-Step Onboarding Process

This process involves creating a secrets engine, defining access policies, associating those policies with LDAP groups, and finally granting access to Kubernetes service accounts.

### 1. Create a Secrets Mount Point

Each microservice should have its own secrets engine mount point. This approach is preferred over using namespaces to enhance isolation and security.  This example configuration is found in `platform-example-java-nonprod.json` within the `kubernetes` namespace directory in the `nonprod` workspace.  Remember to replace `platform-example-java-nonprod` with your microservice's name. The configuration file should be named after your microservice.

[Example Configuration](https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/namespaces/kubernetes/platform-example-java-nonprod.json)

```json
{
    "_namespace": "kubernetes",
    "api_paths": [
        {
            "api_action": "post",
            "api_path": "v1/sys/mounts/platform-example-java-nonprod",
            "api_payload": {
                "config": {
                    "default_lease_ttl": "30m",
                    "listing_visibility": "unauth",
                    "max_lease_ttl": "60m"
                },
                "description": "Used for platform-example-java-nonprod KV Secrets",
                "type": "kv"
            }
        }
    ]
}
```

### 2. Create Read and Write Access Policies

Define separate policies for read and write access to the secrets engine. This is also within the same `platform-example-java-nonprod.json` file.  Again, replace placeholders with your microservice name.

```json
{
    "api_action": "post",
    "api_path": "v1/sys/policy/platform-example-java-nonprod-read-access",
    "api_payload": {
        "path": {
            "platform-example-java-nonprod/*": {
                "capabilities": [
                    "read",
                    "list"
                ]
            }
        }
    }
},
{
    "api_action": "post",
    "api_path": "v1/sys/policy/platform-example-java-nonprod-write-access",
    "api_payload": {
        "path": {
            "platform-example-java-nonprod/*": {
                "capabilities": [
                    "create",
                    "update",
                    "delete"
                ]
            }
        }
    }
}
```

### 3. Assign Policies to LDAP Groups

Configure LDAP group access in the `ldap-groups-policies.json` file located within the `kubernetes` namespace directory in the `nonprod` workspace.  **Important:** Each LDAP group can only be configured once.  Adding a policy to an existing group will overwrite the previous configuration.

```json
{
    "api_action": "post",
    "api_path": "v1/auth/ldap/groups/svr-infra",
    "api_payload": {
        "policies": [
            "platform-example-java-nonprod-read-access",
            "platform-example-java-nonprod-write-access"
        ]
    }
}
```

### 4. Enable Kubernetes Service Account Access

Grant access to specific Kubernetes service accounts by associating policies within the `platform-example-java-nonprod.json` file. This example grants read access to the `platform-example-java` service account.

```json
{
    "api_action": "post",
    "api_path": "v1/auth/dev-us-west1-cluster/role/platform-example-java-nonprod-role",
    "api_payload": {
        "bound_service_account_names": [
            "platform-example-java"
        ],
        "bound_service_account_namespaces": "*",
        "max_ttl": "60m",
        "policies": [
            "platform-example-java-nonprod-read-access"
        ]
    }
}
```

This completes the onboarding process.  Your Kubernetes pods can now securely access secrets from Vault. Remember to replace placeholder names with your actual microservice and service account names.  Consistent naming conventions are crucial for maintainability.