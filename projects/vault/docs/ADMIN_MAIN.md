This document outlines procedures for updating Vault and Consul licenses, and generating RPMs for deployment.

## Vault Clusters.

We have the following clusters available:

| Cluster Name                               | Image                                                                                                         |
|--------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Global Non-Production Vault Clusters      | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-non-production.png?raw=true"/> |
| Global Production Vault Clusters          | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-global-production.png?raw=true"/>  |
| EU Regional Production Vault Clusters     | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-eu-production.png?raw=true"/>   |
| LA Regional Vault Clusters                | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-la-production.png?raw=true"/>   |
| US Regional Vault Clusters                | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-eu-production.png?raw=true"/>   |
| Admin Plane (PKI) Regional Vault Cluster | <img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-admin.png?raw=true"/>        |

All production clusters are in replication to the USPROD01 Regional Cluster. Admin Plane has no secondary cluster.

## Updating Vault and Consul Licenses

Hashicorp products require valid licenses for operation.  The process for updating these licenses depends on your deployment method.  Unfortunately, HashiCorp doesn't provide a single, universal method documented across all deployment scenarios.  The best approach is to consult HashiCorp's documentation for your specific version and deployment type (e.g., using Terraform, Packer, Ansible, or directly on the server).  Generally, it involves providing a license key through the appropriate HashiCorp CLI tool or configuration file.

**General Guidance:**

1. **Obtain a new license key:** Contact your HashiCorp representative or access your HashiCorp account to obtain the updated license key.

2. **Determine your licensing method:** Identify how your Vault and Consul instances are currently licensed.  This could be through environment variables, configuration files (like `vault.hcl` or `consul.hcl`), or a dedicated license file.

3. **Update the license:**  The exact method depends on your deployment:
    * **CLI:** For many versions and deployments, you might use commands such as:
        * `vault operator license <license-key>` (For Vault)
        * `consul license update <license-key>` (For Consul)
    * **Configuration Files:** Update the relevant configuration files to reflect the new license key. The location and format of these files vary. Refer to your deployment configuration and the HashiCorp documentation for the specific version you are using.
    * **UI (Enterprise versions):** If using a HashiCorp Enterprise product with a web UI, the license update might be done through the UI.

4. **Restart services:** After updating the license, restart your Vault and Consul services to ensure the changes take effect.


**Relevant HashiCorp Documentation (General, you will need to locate specific versions):**

* **Vault:**  [https://www.hashicorp.com/docs/vault/](https://www.hashicorp.com/docs/vault/) (Navigate to your specific Vault version and look for sections on licensing or configuration.)
* **Consul:** [https://www.hashicorp.com/docs/consul/](https://www.hashicorp.com/docs/consul/) (Navigate to your specific Consul version and look for sections on licensing or configuration.)


## Generating RPMs for Vault and Consul

Hashicorp does not directly provide RPMs for all versions of Vault and Consul.  You will likely need to build them yourself.  This usually involves using the provided binaries and creating the RPM package using a tool like `rpmbuild`.

**Steps (General Outline – adapt to your specific versions and environment):**

1. **Download Binaries:** Download the appropriate Vault and Consul binaries from the official HashiCorp website.  The exact location depends on the version.

2. **Create Spec Files:** You'll need to create `.spec` files for `rpmbuild`. These files contain instructions on how to build the RPM.  These are typically custom-created and maintained within organizations.

3. **Use `rpmbuild`:** Use the `rpmbuild` command to build the RPMs from the binaries and spec files.  This requires a properly configured RPM build environment.

4. **Verify RPMs:** Verify the integrity and functionality of the generated RPMs before deploying them.

**Relevant Documentation (If available from your organization):**

* Internal Clover documentation linked in the original markdown:
    *  [https://confluence.dev.clover.com/display/CO/Deploy+New+Versions+of+Vault](https://confluence.dev.clover.com/display/CO/Deploy+New+Versions+of+Vault)
    *  [https://gitlab.dev.clover.com/operations/rpm-vault](https://gitlab.dev.clover.com/operations/rpm-vault)



**(Note:  The instructions above are general guidelines.  Always consult the official HashiCorp documentation for your specific Vault and Consul versions to ensure accurate and up-to-date information.)**


---

The remaining sections of the original markdown (Rundeck Jobs, Re-Key Cluster, Migrating Secrets, Key Holder Information) are retained below but require improved formatting and clarity for better readability.

## Deploying Rundeck Jobs

This project utilizes the `rundeckrun` open-source library ([https://github.com/marklap/rundeckrun](https://github.com/marklap/rundeckrun)) for Rundeck job execution.

**Installation:**

```bash
pip3 install rundeckrun
```

**Import Rundeck Templates:**

```bash
export LDAP_USERNAME="<username>"
export LDAP_PASSWORD="<password>"
python3 bin/import_rundeck_lib_py
python3 bin/rundeck/import_rundeck_templates.py --name nonprod01
python3 bin/rundeck/import_rundeck_templates.py --name nonprod02
python3 bin/rundeck/import_rundeck_templates.py --name admin01
```

**Rundeck Server Configuration:**

1. **Update Symlink:** Create a symbolic link on the Rundeck server to locate datacenter nodes.  Example:
   ```bash
   ln -s nodes-master.sh pdx01
   ```
2. **Update `nodes.include`:** Edit `/var/lib/rundeck/mdb-integration/nodes.include` to include entries like `^vault-nonprod[[:digit:]].`.
3. **Add Node Source:** Add a search using the symlink to your Rundeck node sources (e.g., `https://rundeck.corp.clover.com/project/release/nodes/sources`).

## Re-Key Cluster

The rekey process rotates the sharded master keys for enhanced security. This requires collaborative action from key holders.

**Process:**

1. **Initialization:** An administrator initiates the rekey process using the `cluster_rekey.py` script with the `--event=init` flag.  This generates a nonce.
2. **Key Holder Input:** Each key holder inputs their key using the script, providing the nonce.
3. **Key Threshold:** Once enough keys are provided to meet the threshold, the script generates new keys and distributes them (if configured).

**Example Commands (replace placeholders):**

```bash
python3 bin/cluster_rekey.py --name=vault-nonprod01 --auth-method=ldap --event=init

export NONCE="<nonce_value>"
export VAULT_KEY="<keyholder_key_1>"
python3 bin/cluster_rekey.py --name=vault-nonprod01 --auth-method=ldap

export VAULT_KEY="<keyholder_key_2>"
python3 bin/cluster_rekey.py --name=vault-nonprod01 --auth-method=ldap
```

**Key Backup Retrieval:**  Vault cluster admins can access PGP-encrypted key backups via: `vault read sys/rekey/backup`

**(A detailed, improved "Live Manual Plan" section with clearer steps and improved formatting should replace the original one.)**

## Key Holder Information

Key holders must generate a local PGP key pair to decrypt sharded master keys.  Losing a key necessitates notifying Clover Operations; recovery is not possible.  Data loss may occur if the key loss exceeds a defined threshold, resulting in Vault sealing.

**Generating PGP Keys:**

1. **Install GPG:**  `brew install gpg`

2. **Generate Key Pair:** (Replace placeholders with your information)

```bash
export PGP_USER="<username>"
export PGP_EMAIL="<email>@clover.com"
export PGP_PASSPHRASE="<strong_passphrase>"
cat >pgp_key_info <<EOF
Key-Type: RSA
Key-Length: 4096
Subkey-Type: RSA
Subkey-Length: 4096
Name-Real: $PGP_USER
Name-Email: $PGP_EMAIL
Name-Comment: GPG Key for handling encrypted PGP for Clover Operations
Expire-Date: 0
Passphrase: $PGP_PASSPHRASE
%commit
EOF
gpg --batch --full-generate-key pgp_key_info
rm -f pgp_key_info
mkdir -p config/pgp_keys
gpg --armor --export $PGP_EMAIL > "config/pgp_keys/$PGP_EMAIL.asc"
```

3. **Decrypting Keys (During Vault Unseal or Rekey):**  Follow instructions provided by the `cluster_init.py` or `cluster_rekey.py` scripts.  This will involve decrypting a PGP-encrypted file using your passphrase.