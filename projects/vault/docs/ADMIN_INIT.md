# Cluster Initializing
This document outlines the process of initializing a Vault cluster, a crucial step that configures Vault for the first time. This process happens only once per cluster, regardless of the number of servers in an HA setup.

Keys will be sharded in this way:

<img src="https://github.corp.clover.com/clover/vault/blob/master/images/Initialization.png?raw=true" width="25%" height="25%"/>

## Understanding Initialization
During initialization, Vault performs the following actions:

* Establishes Communication: Connects securely with the Consul backend (typically used for durable storage) using the Consul ACL token.
* Generates and Shards Master Key: Creates and splits the master key into shares using Shamir's secret sharing algorithm for enhanced security. Alternatively, encrypts the master key using a Hardware Security Module (HSM) like GCP KMS.
* Initializes Backend: Writes the initial configuration to the Vault backend, usually Consul.
* Generates Root Token: Creates a non-expiring root token with unrestricted access to Vault.
* Important Note: The Consul storage backend is considered untrusted. It stores encrypted data, and Vault decrypts this data only when unsealed.

# Unsealing Vault
After initialization, Vault remains in a sealed state. To make it operational, you need to unseal it:

* Shamir's Secret Sharing: Provide a sufficient number of key shares (as defined during initialization) to reconstruct the master key and unseal Vault.
* HSM (e.g., GCP KMS): Vault automatically accesses the encrypted master key from the HSM to unseal itself.
Once unsealed, Vault loads configurations for audit devices, authentication methods, and secrets engines.

# Initializing via Rundeck
For Clover's setup, Rundeck simplifies the initialization process:

* Login: Access Rundeck at the provided URL (replace placeholders with actual values): https://rundeck.corp.clover.com/project/release/jobs/vault
* Navigate to Job: Go to vault/<<target cluster>>/Cluster Init (<<target cluster>>)
* Execute: Enter your LDAP credentials and click "Run" to initiate the Cluster Init job.

# Post-Initialization Steps
After successful initialization, the first Vault instance becomes the leader and automatically performs these tasks:
* Unseals All Instances: Uses the provided unencrypted key shares to unseal all Vault instances in the cluster.
* Rekeys Cluster: Encrypts the master key using PGP keys provided by Vault keyholders.
* Configures Basic Access by enabling
```bash
1. Enables audit logging for tracking actions.
2. Sets up LDAP authentication for employee access.
3. Enables TLS, Kubernetes, and AppRole authentication for machine access.
```
* Configures admin policies for managing the cluster without the root token.
* Revokes Root Token: Deactivates the initial root token to enhance security.

# Troubleshooting
If initialization fails, follow these steps:

* Access Vault Server: Log in to the first Vault server as root.
* Inspect Consul Configuration: Check the Consul configuration file for the master ACL token: less /etc/consul/config.json
* Delete Vault Data: Clear the Vault state in Consul: CONSUL_HTTP_SSL_VERIFY=false CONSUL_HTTP_SSL=true CONSUL_HTTP_ADDR=127.0.0.1:8501 consul kv delete -recurse -token=<<master_acl_token>> -http-addr=https://<<any one vault backend servers>>:8501
* Restart Vault: systemctl restart vault.service
* Retry Initialization: Rerun the cluster initialization process.
