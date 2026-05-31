

Response
# Migrating Vault off Shamir Cluster Setup for Clover Auto-Unsealing

To enable Clover's auto-unsealing features, Vault must be migrated from a Shamir Cluster setup.  The following instructions combine HashiCorp's guidance with Clover-specific details.

## Clover Instructions

**Phase 1: GCP KMS Setup and Primary Cluster Preparation**

1. **Create GCP KMS Resources:** Create two separate GCP KMS rings and two distinct service account keys for Vault authentication to KMS.  Ensure KMS keys are created as defined in [this Terraform configuration](https://gitlab.dev.clover.com/terraform/workspaces/vault/blob/master/kms.tf).

2. **Disable Primary Cluster Replication:** Disable replication on the primary cluster, revoke the secondary token, and disable secondary cluster replication using the following Rundeck job:

   `vault / <<target primary cluster>> / Manage DR State (<<target primary cluster>>)`

   **Options:**
   * `mount_path: ldap`
   * `vcs_ldap_username: <<corp ldap username>>`
   * `event: disable`
   * `ldap_username: <<corp ldap username if nonprod. otherwise use prod-ldap user account>>`
   * `target: primary`


**Phase 2: Promote and Configure DR Secondary Cluster**

3. **Promote DR Secondary:** Follow the steps for promoting the DR secondary cluster outlined in [this Confluence page](https://confluence.dev.clover.com/display/CO/Manage+Replication+for+Vault+Cluster).

4. **Disable Secondary Cluster Replication:** Disable replication on the secondary cluster, revoke the secondary token, and disable secondary cluster replication using the following Rundeck job:

   `vault / <<target dr cluster>> / Manage DR State (<<target dr cluster>>)`

   **Options:**
   * `mount_path: ldap`
   * `vcs_ldap_username: <<corp ldap username>>`
   * `event: disable`
   * `ldap_username: <<corp ldap username if nonprod. otherwise use prod-ldap user account>>`
   * `target: primary`


5. **Configure GCP KMS Seal in Puppet:** Add a GCP KMS seal configuration with the correct credentials for each cluster to the Puppet code for each node (refer to existing Vault nodes for examples). Commit your code to a branch.  The seal configuration will differ between the primary and secondary clusters and depend on the KMS ring/key created in Terraform.

   ```puppet
   vault::seal:
       gcpckms:
           project: "<<gcp project>>"
           region: "global"
           key_ring: "vault-<<cluster name>>-key-ring"
           crypto_key: "vault-<<cluster name>>-crypto-key"
           disabled: "false"
   ```

6. **Apply Puppet Changes:** Run Puppet on both primary and secondary nodes:

   ```bash
   pausepuppet 500
   runpuppet -e <<your branch>> --force -y
   ```

**Phase 3: Seal Migration and Replication Re-enablement**

7. **Verify Seal Migration Mode:** Check Vault logs (`/var/log/vault.log`) for the following message:

   `2019-06-03T09:09:50.654Z [WARN]  core: entering seal migration mode; Vault will not automatically unseal even if using an autoseal: from_barrier_type=shamir to_barrier_type=gcpckms`

   If this message is absent, restart the Vault service (`systemctl restart vault.service`).

8. **Migrate the Seal:** On one server per cluster, execute the seal migration using the unseal keys:

   ```bash
   VAULT_SKIP_VERIFY=true vault operator unseal -migrate
   ```

   Verify successful migration by checking the logs for:

   `2020-02-10T10:11:09.813Z [INFO]  seal.rewrap: seal re-wrap completed: entry processing stats: succeeded=24 failed=0 total=24`

9. **Restart Standby Instances:** Restart all other standby Vault instances for each cluster:

   ```bash
   systemctl restart vault.service
   ```

10. **Enable Primary Cluster Replication:** Enable replication on the primary cluster using the following Rundeck job:

    `vault / <<target primary cluster>> / Manage DR State (<<target primary cluster>>)`

    **Options:**
    * `mount_path: ldap`
    * `vcs_ldap_username: <<corp ldap username>>`
    * `event: enable`
    * `ldap_username: <<corp ldap username if nonprod. otherwise use prod-ldap user account>>`
    * `target: primary`

11. **Verify DR Replication:** Verify DR replication is running by checking the DR recovery endpoint status for each cluster (e.g., `https://vault-nonprod01.corp.clover.com/v1/sys/replication/dr/status`, `https://vault-nonprod02.corp.clover.com/v1/sys/replication/dr/status`).  Look for `mode: secondary` and `state: stream-wals`.

12. **Rekey Vault:** Rekey the Vault cluster following the instructions in [this Confluence page](https://confluence.dev.clover.com/display/CO/Re-Key+Vault+Cluster). Update `ops.config` to set `cluster.recovery_keys: true`.


## HashiCorp Instructions (Supplemental)

These instructions provide additional context and are largely superseded by the Clover-specific steps above, but are included for completeness.

**(Note:  Many of these steps are implicitly covered in the Clover instructions above.)**

1. Create two separate GCP kms_rings and two different service account keys.

2. Disable replication on the primary cluster.
   * Revoke secondary token: [Documentation](https://www.vaultproject.io/api-docs/system/replication/replication-dr/#revoke-dr-secondary-token)
   * Disable DR replication: [Documentation](https://www.vaultproject.io/api-docs/system/replication/replication-dr/#disable-dr-primary)


3. **DR Cluster Shutdown and Reconfiguration:**
   * Shutdown the DR cluster.
   * Add GCP KMS seal configuration to all DR cluster nodes:

     ```puppet
     seal "gcpckms" {
         credentials = "/usr/vault/vault-project-user-creds.json"
         project = "corps-managed"
         region = "global"
         key_ring = "vault-nonprod01-key-ring"
         crypto_key = "vault-nonprod01-crypto-key"
     }
     ```
   * Clear the storage backend (using `consul kv delete -recurse vault/` on the Consul leader).

4. **DR Cluster Startup and Initialization:**
   * Start a DR node and initialize Vault, saving recovery keys and the temporary root token.
   * Start remaining DR nodes, verifying they join and enter standby mode.


5. **Primary Cluster Shutdown and Reconfiguration:**
   * Shutdown the primary cluster.
   * Add the GCP KMS seal configuration (with `disabled = false`) to one node's configuration.  Optionally, add a Shamir dummy seal with `disabled = true`.
   * Start Vault and wait for the seal migration mode warning in the logs.
   * Migrate the seal using `vault operator unseal -migrate`.
   * Generate and save recovery keys using `vault operator rekey -init -target=recovery` and `vault operator rekey -target=recovery`.  [Recovery key documentation](https://www.vaultproject.io/docs/enterprise/hsm/behavior/#recovery-key)
   * Add the GCP KMS seal to remaining primary nodes and start them, verifying they enter standby mode.


6. **Enable DR Replication:**
   * Enable DR replication on the primary cluster (`vault write -f sys/replication/performance/primary/enable` and create a new DR token).
   * Enable replication on the DR cluster (`vault write sys/replication/performance/secondary/enable`).
   * Verify DR replication is running (`vault read sys/replication/dr/status`).  Look for `mode: secondary` and `state: stream-wals`.

This comprehensive guide should help you successfully migrate your Vault cluster and enable auto-unsealing for Clover.  Remember to replace placeholders like `<<...>>` with your specific values.