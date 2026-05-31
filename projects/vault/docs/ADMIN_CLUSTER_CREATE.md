# Launching a New Vault Cluster (not using Performance Replication)

These steps assume a completed Terraform infrastructure for Vault installation with correct Puppet roles assigned.  We'll use `appenv=uspreprod` as an example.

## Stage 1: Seed Initial Secrets

To overcome the chicken-and-egg problem with Puppet, we'll use an existing Vault cluster (e.g., `usprod01` or `nonprod01`) to store secrets needed for launching the new cluster.  Add the following secrets:

* **Consul API Token:** Generate using `uuidgen | tr "[:upper:]" "[:lower:]"` on your local terminal.
* **Encryption Token:** Generate using `brew install consul; consul keygen` on your local terminal.
* **Vault License Key:** Add to: [https://vault-usprod01.prod.dsm01.clover.network:8200/ui/vault/secrets/puppet/list/uspreprod/vault/?namespace=puppet](https://vault-usprod01.prod.dsm01.clover.network:8200/ui/vault/secrets/puppet/list/uspreprod/vault/?namespace=puppet)


## Stage 2: Configure Puppet

Update `puppet/hiera.yaml` to point the new environment to the `usprod` Vault cluster for secrets and use `puppet/<<appenv>>` for environment-specific secrets.  Refer to:

* [https://github.corp.clover.com/clover/puppet/blob/2ee2ed15347f5b6a79731564fddc071ad712db90/hiera.yaml#L92](https://github.corp.clover.com/clover/puppet/blob/2ee2ed15347f5b6a79731564fddc071ad712db90/hiera.yaml#L92)

For new environments, also configure:

* [https://github.corp.clover.com/clover/puppet/pull/4230/files](https://github.corp.clover.com/clover/puppet/pull/4230/files)
* [https://github.corp.clover.com/clover/puppet/pull/4233/files](https://github.corp.clover.com/clover/puppet/pull/4233/files)

The initial Vault configuration will use the production US cluster for setup secrets:

* [https://github.corp.clover.com/clover/puppet/blob/3f889ccb3bdd6039dff3a24d5464cb22773ad0c7/hieradata/appenv/uspreprod/vault.yaml](https://github.corp.clover.com/clover/puppet/blob/3f889ccb3bdd6039dff3a24d5464cb22773ad0c7/hieradata/appenv/uspreprod/vault.yaml)


## Stage 3: Launch Vault Infrastructure

Ensure VMs hosting Vault and Consul are running.  If the Vault cluster is sealed without unseal keys, instead of deleting and relaunching:

1. Log into the Consul backend.
2. List all keys: `curl https://127.0.0.1:8501/v1/kv/?recurse -k | jq .`
3. Delete all Vault keys: `curl --request DELETE https://127.0.0.1:8501/v1/kv/vault/?recurse -k`
4. Restart the Vault service.


## Stage 4: Unseal and Configure Vault

After the initial Puppet run (Vault will be sealed), use the following script to initialize and unseal:

* [https://github.corp.clover.com/clover/vault/blob/master/bin/cluster_init.py](https://github.corp.clover.com/clover/vault/blob/master/bin/cluster_init.py)

Alternatively, use Rundeck jobs:

* `python3 ./bin/rundeck/import_rundeck_templates.py --name=uspreprod01`
* `python3 ./bin/rundeck/import_rundeck_templates.py --name=uspreprod02`

Store unseal keys at: [https://github.corp.clover.com/clover/vault/tree/master/config/current_keys](https://github.corp.clover.com/clover/vault/tree/master/config/current_keys)


## Stage 5: DR Replication

Pair the secondary cluster with the primary in DR mode:

`python3 bin/manage_dr_state.py --name vault-uspreprod01 --mount-path prod-ldap --event enable`


## Stage 6: Generate and Load Base Secrets

Use the automation script: [https://github.corp.clover.com/clover/nit-tools-dcauto](https://github.corp.clover.com/clover/nit-tools-dcauto)  This will load base secrets to the new cluster.


## Stage 7: Final Puppet Configuration

Update `puppet/hiera.yaml` to use the new Vault cluster.