# Maintaining Vault at Clover

Vault maintenance and configuration is divided into three main areas: Re-keying, Upgrading, and Deploying new changes.  Monitoring is also a crucial aspect.

## I. Re-keying Vault Cluster

The re-keying process rotates the sharded master keys, requiring all Vault key holders to participate.  This process generates a new key pair using existing keys and then re-encrypts data if necessary.

**Process:**

1. **Admin Initiates Rekey:** An administrator starts the rekey process using a rekey script (e.g., `bin/cluster_rekey.py`).
2. **Key Holders Input Keys:** Each key holder inputs their key using the rekey script.
3. **Threshold Met, New Key Generated:** Once the required key threshold is met, the final key input generates the new key and sends a response (if applicable) to the key holders.


**Adding/Managing Key Holders:**

1. **Clone Repo:** `git clone git@github.corp.clover.com:clover/vault.git`
2. **Create Branch:** `git checkout -b vault_rekey`
3. **Generate PGP Key (for each keyholder):**

```bash
export PGP_USER="Richard Whitney"
export PGP_EMAIL="richard.whitney@clover.com"
export PGP_PASSPHRASE="Your super secret passphrase"
cat >pgp_key_info <<EOF
%echo Generating a basic OpenPGP key
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
%echo done
EOF

gpg --batch --full-generate-key pgp_key_info
rm -f pgp_key_info
gpg --armor --export $PGP_EMAIL > "config/pgp_keys/$PGP_EMAIL.asc"
git add "config/pgp_keys/$PGP_EMAIL.asc"
git commit -m "Adding new keyholder"
git push origin vault_rekey
```

4. **Update `config/ops.json`:** Add the keyholder's email to the `config/ops.json` file.  This allows the keyholder to target any cluster. Merge changes into the master branch.


**Rundeck Process:**

1. **Authenticate to Rundeck:** [Rundeck Authentication Link (Not Provided)]
2. **Start Rekey Event:** Navigate to the appropriate Rundeck job (e.g., `vault/<<target cluster>>/Cluster Re-key (<<target cluster>>)`).
3. **Init Event:** Set the event to `init`, provide LDAP credentials, and click "Run."  The job returns a nonce value.
4. **Key Input Event:** Navigate to the same Rundeck job, set the event to `key-input`, provide LDAP credentials, the nonce value, and each key holder's individual key.
5. **Retrieve Keys:** Examine the Rundeck output for new GPG-encrypted keys and distribute them to the key holders. Keys are also available at the `/sys/rekey/backup` endpoint accessible via the Vault CLI or UI: `vault read sys/rekey/backup`

**Command Line Process (Alternative to Rundeck):**

1. **Clone Repo:** `git clone git@github.corp.clover.com:clover/vault.git`
2. **Init:** `python3 bin/cluster_rekey.py --name=vault-nonprod01 --auth-method=ldap --rekey-event=init`
3. **Key Input (Repeat for each keyholder):**
    * Set `NONCE` environment variable to the nonce value from the `init` step.
    * Set `VAULT_KEY` environment variable to the keyholder's key.
    * Run: `python3 bin/cluster_rekey.py --name=vault-nonprod01 --auth-method=ldap`
4. **Update `config/current_keys/`:**  The command-line process updates the relevant JSON file. Commit and push changes.


## II. Upgrading Vault with Puppet/Updating RPMs

# Upgrading Vault and Consul Clusters

Upgrading Vault requires a phased rollout to maintain high availability.  Upgrade each instance individually, saving the leader for last. This is crucial for both Vault and Consul backend instances, as leader election can fail if the leader's version differs from the rest of the cluster.  Vault instances will automatically seal upon restart unless Auto-Unseal is enabled at the node level in Puppet.  Vault and Consul components can be updated concurrently, following these steps:


## Download Binaries

Download the necessary Vault and Consul binaries.  Open source binaries are available at:

* **Vault:** [https://releases.hashicorp.com/vault](https://releases.hashicorp.com/vault)
* **Consul:** [https://releases.hashicorp.com/consul](https://releases.hashicorp.com/consul)


For macOS, download the `darwin_amd64` binaries; `linux_amd64` is incompatible.  Both `linux_amd64` and `darwin_amd64` are usually provided.

## Deploy to Artifactory

Enterprise binaries must be downloaded from the vendor and deployed to Artifactory. Open source binaries can be found at the links above.

1. Log into Artifactory using your LDAP credentials.  (Contact Clover DevOps for upload permissions to `ext-vendor-local` if needed.)
2. Navigate to `Artifactory` -> `Artifacts` -> `ext-vendor-local`.
3. Click "Deploy" and upload the binaries to the appropriate folders (`vault/` or `consul/`).
4. Note the artifact URLs for later use in updating node information.

## Manage Packages using rpm-vault Repo (Optional)

For managing Vault RPM packages, utilize the `rpm-vault` repository. This requires Docker. Deployment to DEV and PROD distribution servers takes approximately 24 hours. Address any ownership issues in `/var/lib/reposync` and sync the Clover legacy repo if necessary.

## Update Puppet Node Information

Update the Puppet Hiera node information ([link to Hiera node information needed here]) for all Vault instances.  Look for files starting with `vault-*.yaml` and `vault-backend-*.yaml`.  In NONPROD environments, Consul and Vault are co-located, eliminating separate backend hosts. Update the `vault::package_ensure` and `consul::package_ensure` parameters as needed (example below).  Commit your changes.

```yaml
vault::package_ensure: "1.2.2-1.el7"
consul::package_ensure: "1.7.2-1.el7"
consul::version: "1.7.2"
```


## Submit Package PRs

Submit your package changes via a pull request following Puppet and get a review following this process [here](https://confluence.corp.clover.com/pages/viewpage.action?pageId=62301062).

## Rundeck Upgrade Process

Use Rundeck ([link to Rundeck job needed here]) to perform the upgrade in the following stages:

**Rundeck Job Order for Upgrades (Individual Clusters):**

* `0 - Pause Puppet on Target Vault Cluster`
* `1 - Check Consul Cluster Package Versions`
* `2 - Check Vault Cluster Package Versions`
* `3 - Upgrade Vault Backend (Raft Peers)`
* `4 - Upgrade Vault Backend (Raft Leader)`
* `5 - Upgrade Vault (Standby Servers)`
* `6 - Upgrade Vault (Active Server)`
* `1 - Check Consul Cluster Package Versions` (Re-run for verification)
* `2 - Check Vault Cluster Package Versions` (Re-run for verification)

Jobs are located [here](https://rundeck.corp.clover.com/project/patch_management/jobs/vault)

**Upgrade Order:** `nonprod02`, `nonprod01`, `laprod02`, `laprod01`, `euprod02`, `euprod01`, `usprod02`, `usprod01`, `prod02`, `prod01`, `admin01`.

**Deploying New Rundeck Jobs:** Follow the installation instructions in the GitLab project ([GitLab Project Link (Not Provided)]).  Do not deploy manually.  Updating existing templates:

```bash
export LDAP_USERNAME=<<username>>
export LDAP_PASSWORD=<<password>>
python bin/rundeck/import_rundeck_lib.py
python bin/rundeck/import_rundeck_templates.py --name nonprod01
python bin/rundeck/import_rundeck_templates.py --name nonprod02  #(repeat for other clusters)
```


## IV. Monitoring

Vault monitoring uses Telegraf to send metrics to Grafana. Please refer to https://clovernetwork.grafana.net/goto/MyYU34GNR?orgId=1.


## V. Rollback Procedures

Rollback procedures are available via Rundeck jobs for restoring Consul and Vault states from backups.  These jobs are referenced within the document and should be added with appropriate links if known.  Also, manual intervention might be necessary (re-initiating the cluster and re-configuring the backend).

Jobs are located [here](https://rundeck.corp.clover.com/project/release/jobs/vault)