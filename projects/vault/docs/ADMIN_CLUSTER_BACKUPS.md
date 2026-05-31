# Vault Backups and Restores

This document describes how to perform ad-hoc backups of vault clusters. The primary use case for following the steps in this document would be to perform a backup of a vault cluster before deployment new secrets to it. In the event that of data corruption to the cluster, a restore could be performed from the backup.

Daily Consul or Raft Snapshots are available for recovery using Rundeck. They follow this architecture:

Consul Backed Clusters:

<img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-backup-consul.png?raw=true" width="35%" height="35%"/>

Raft Backed Clusters:

<img src="https://github.corp.clover.com/clover/vault/blob/master/images/vault-backup-raft.png?raw=true" width="35%" height="35%"/>


# Requirements
* Python 3.
* Access to the vault github repository.
* Non production and/or production LDAP credentials, depending on which vault cluster needs to be backed up. It's recommended you use gopass to set these correctly and securely.

# Backup Procedure

This procedure will detail how to use the sync_local_secrets python script, available in the vault github repository to copy/sync the secrets in a specific vault location to the corresponding location in the local working copy of the vault github repository. In the event of corruption to the vault cluster, this data could be used to reinstate the vault cluster data.

Create a python virtual environment for the sync_local_secrets python script and install dependencies:

``` bash
python3 -m venv ~/venv/vault-sync
source ~/venv/vault-sync/bin/activate
pip install urllib3 
pip install requests
```

Clone the vault github repository:
```bash 
git clone git@github.corp.clover.com:clover/vault.git
cd vault
git checkout -b synced_secrets
```

Run the sync_local_secrets script, changing the command line arguments as necessary. (e.g. if want to remove extra intervening / then it's Necessary to remove this "--source-path=/ \" )

```bash 
LDAP_PASSWORD=$(gopass prod_ldap) LDAP_USER=<your-ldap-username> python3 bin/sync_local_secrets.py \
    --name=vault-usprod01 \
    --auth-method=ldap \
    --mount-path=prod-ldap \
    --source-namespace=puppet \
    --source-kv=puppet \
    --file-path="./config/json_workspaces/prod/namespaces/puppet"
```
In this example, the entire contents of the vault-usprod01 cluster's puppet namespace has been synced locally to the directory ./config/json_workspaces/prod/namespaces/puppet.

Commit and push the changes made to the local git branch, back to github.
``` bash
git add .
git commit -m message
git push origin synced_secrets
```

# Restore Data
In order to restore data to a vault cluster, the appropriate Rundeck Manage Cluster Data job needs to be executed. Open a PR and merge the git branch from the backup back to master. Use the appropriate Rundeck Manage Cluster Data job to push the vault config from the master branch to the vault cluster. Each cluster has it's own Manage Cluster Data job.

Rundeck jobs are located here: https://rundeck.corp.clover.com/project/release/jobs/vault

# Recover Data
To restore data to a Vault cluster:

* Open a pull request and merge the synced_secrets branch into the master branch of your Vault repository.
* Use the appropriate Rundeck "Manage Cluster Data" job to push the Vault configuration from the master branch to the Vault cluster. Each cluster has its own "Manage Cluster Data" job.

Note: Rundeck jobs are assumed to be located at: https://rundeck.corp.clover.com/project/release/jobs/vault

# Recover Clusters
Leverage the raft or consul snapshots running the restore or backup at: https://rundeck.corp.clover.com/project/release/jobs/vault

Jobs are:
* <>/Snapshot Backup (<>) Takes Raft or Consul Snapshots at daily intervals and deploys to GCP Cluster Bucket
* <>/Snapshot Restore (<>) Restore State from a Raft or Consul snapshot from GCP Cluster Bucket

Rundeck Jobs: Rundeck jobs for managing Vault clusters are assumed to be located at: https://rundeck.corp.clover.com/project/release/jobs/vault
Snapshot Backup/Restore Jobs: Rundeck jobs for snapshot backups and restores are available under the specific cluster's directory within the Vault jobs.
GCP Cluster Bucket: Consul snapshots are stored in a dedicated GCP bucket for each cluster. The bucket name follows the pattern YYYY-MM-DD<<vault cluster name like vault_nonprod01>>.snap.

Otherwise, leverage via vault binary following options:
```bash
vault operator raft snapshot save <snapshot_name>
vault operator raft snapshot restore <snapshot_name>
```