# Managing Secrets in Vault: Best Practices and Access Control

This document outlines the procedures for Clover engineers to manage secrets within HashiCorp Vault, emphasizing vendor best practices for security and access control.  Vault operates on a "secure by default" principle, meaning access is granted only through explicitly defined policies linked to LDAP groups, not individual usernames. This approach minimizes the risk of unauthorized access and improves overall security posture.

## Default Access and Secret Deployment Options

By default, all Clover engineers have basic read-only access to the Puppet namespace in Vault. This allows them to list secrets (without viewing their values) and utilize the transit encryption functionality for infrastructure-as-code (IaC) deployments (see [How do I work with Vault when using Puppet](link_to_how_to_work_with_vault_when_using_puppet)).  However, deploying new secrets requires one of the following options:

### Option 1: Seed Puppet Secrets with Infrastructure as Code (IaC)

This method leverages the Bedrock team and their access to the Puppet secret engine for secure secret deployment. The process involves:

1. **Download the Vault configuration repository:** [https://github.corp.clover.com/clover/vault](https://github.corp.clover.com/clover/vault)
2. **Encrypt the secret:** Use the Rundeck job "Encrypt a secret to store in Vault as Infra as Code (Puppet)" to encrypt the target secret.
3. **Store the encrypted secret:** Create a JSON file (following the example below) in [https://github.corp.clover.com/clover/vault/tree/master/config/json_workspaces](https://github.corp.clover.com/clover/vault/tree/master/config/json_workspaces) specifying the desired path and encrypted values.  Example:

```json
{
    "_namespace": "puppet",
    "api_paths": [
        {
            "api_action": "post",
            "api_path": "v1/puppet/inpreprod/cos/mysecret",
            "api_payload": {
                "secret1": "vault:v1:vHIf3LdhfqhV0+R4tNxxtoif5m/cnR4Mfi4bVPugIoO2wSpb74sXsMk8wDNcf4UHJf7Zx0iYXczc3knVLVE40wfzg5tN",
                "secret2": "vault:v1:BnkKTE7ahJlULp0I5hs6BfPoMkZgGdmxlqriVd8/bZ44HQeQCifsyeRTR2yXTroO8r2Z5niNnpk=",
                "secret3": "vault:v1:SSI0CNN2otnty+AFAICndxwqE2p9GS7MxXnhYuC6r4GEI34nmarf8JXDAgJIt1NRwtbF2EoJePfiqgElWGFveO7ZtMC/IkhDKQyT73/dN7H7LLIW7Xi/fZy6WL2II8tNCA==",
            },
            "transit_encoded_keys": [
                "secret1",
                "secret2",
                "secret3"
            ],
            "transit_key": "namespace-encryption",
            "transit_secret_engine": "transit"
        }
    ]
}
```
4. **Raise a Pull Request:** Submit a PR via [https://github.corp.clover.com/clover/vault/pulls](https://github.corp.clover.com/clover/vault/pulls) and follow the process outlined in [How to get a Vault change reviewed](link_to_how_to_get_a_vault_change_reviewed).
5. **Deployment:** Notify `@vault-reviewers` in the #vault Slack channel to deploy the change.

The secret will then be accessible in Puppet Hiera Data using the following format:

```puppet
cos::mysecret1: "%{lookup('vault:cos/mysecret/secret1')}"
cos::mysecret1: "%{lookup('vault:cos/mysecret/secret2')}"
cos::mysecret2: "%{lookup('vault:cos/mysecret/secret3')}"
```

**Benefits:**  Formal review process, no special access requests needed.
**Downsides:** Requires waiting for reviewers, developers lack direct ownership and visibility of the secret.

### Option 2: Self-Service Access in Vault

This option empowers teams to manage their secrets directly within Vault, provided they have the necessary access controls.  This involves:

1. **Access Vault:** Log into the target Vault cluster (see [How can I login into Vault](link_to_how_can_i_login_into_vault)).
2. **Manual Secret Editing:** Navigate to the Puppet path and modify the secret directly.  Alternatively, for Jasypt encryption:
    * Use the Rundeck job "Encrypt and store a secret in Vault (Puppet)".
    * Provide the secret, path (`e.g., cos/my_secret`), and ensure appropriate ACLs are in place.
    * Possess valid LDAP credentials.

To enable self-service, teams must onboard appropriate policies to their LDAP groups. This requires creating read and write ACL policy files (similar to [https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/namespaces/puppet/_auth_corp_policies.json](https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/nonprod/namespaces/puppet/_auth_corp_policies.json)) which explicitly define access paths.  Globs (`*`) or plus signs (`+`) can be used for wildcard matching, but should be used cautiously.


**Example ACL Policy:**

```json
{
    {
        "api_action": "post",
        "api_path": "v1/sys/policy/puppet-cosbilling-reader",
        "api_payload": {
            "path": {
                "puppet/dev/cos/supersecret": {
                    "capabilities": ["read", "list"]
                },
                "puppet/stg1/cos/*": {
                    "capabilities": ["read", "list"]
                },
                "puppet/stg1/+/startup_password": {
                    "capabilities": ["read", "list"]
                }
            }
        }
    },
    {
        "api_action": "post",
        "api_path": "v1/sys/policy/puppet-cosbilling-writer",
        "api_payload": {
            "path": {
                "puppet/dev/cos/supersecret": {
                    "capabilities": ["create", "delete", "update"]
                },
                "puppet/stg1/cos/*": {
                    "capabilities": ["create", "delete", "update"]
                },
                "puppet/stg1/+/startup_password": {
                    "capabilities": ["create", "delete", "update"]
                }
            }
        }
    }
]
```

This example creates reader and writer policies granting access to specific paths.

After creating the ACLs, associate them with the team's LDAP group (using a posix group if necessary - create one via an IT Request if needed) in [https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/{nonprod|inprod|inpreprod|prod}/namespaces/puppet/ldap-groups-policies.json](https://github.corp.clover.com/clover/vault/blob/master/config/json_workspaces/{nonprod|inprod|inpreprod|prod}/namespaces/puppet/ldap-groups-policies.json).  See the example below for the LDAP group role policy mapping:

**Example LDAP Group Role Policy Mapping:**

```json
{
    "_namespace": "puppet",
    "api_paths": [
        ...
        {
            "api_action": "post",
            "api_path": "v1/auth/ldap/groups/cosbillinggroup",
            "api_payload": {
                "policies": [
                    "puppet-cosbilling-reader",
                    "puppet-cosbilling-writer"
                ]
            }
        }
    ]
}
```

Finally, submit a SECREQ ticket for security review.  Upon approval, follow the [How to get a Vault change reviewed](link_to_how_to_get_a_vault_change_reviewed) process.  Use the Rundeck job "List Vault Secret in Puppet Namespace" to verify secrets.

**Benefits:** Self-service, bypasses review process.
**Downsides:** No versioning safeguards, requires careful ACL management, and justification of access to security.  Unauthorized overwrites result in secret loss.


**Example Successful and Unsuccessful Secret Deployment:**

The output of the Rundeck job will clearly distinguish between successful and unsuccessful deployments based on ACL permissions.  Look for the `403 Forbidden` error which indicates ACL issues.

Remember to always follow security best practices and carefully manage access control policies to ensure the confidentiality and integrity of your secrets.  Use of least privilege is key here; avoid granting broad access where more granular control can be implemented.
