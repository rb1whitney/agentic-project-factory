# Managing Secrets in Vault at Clover (General)

This document outlines the process for managing secrets and Vault configurations at Clover, emphasizing self-service options and aligning with vendor best practices for security and operational efficiency.

## Automated Secret and Configuration Deployments
If you are an ops (security / platform) engineer, you can leverage Rundeck to perform changes against Vault Clusters:
* Prepare Changes in Vault Github Repo: Merge in changes https://github.corp.clover.com/clover/vault/pulls
  * Log into Rundeck: Log into https://rundeck.corp.clover.com using SSO
* Access Rundeck Job for target Cluster: Access the Rundeck Job to Apply Changes into Cluster:
  * Admin: https://rundeck.corp.clover.com/project/release/job/show/d9ad977b-5586-484b-ba1b-d33010209b07
  * Non-Production: https://rundeck.corp.clover.com/project/release/job/show/b61adbba-33fb-4c1f-91b3-ac1c29f72ea0
  * Prod (makes change to prod, laprod, euprod, and usprod at the same time via replication): https://rundeck.corp.clover.com/project/release/job/show/fcbf4158-1a12-49bc-a940-997fdb2cb4b3
* Prepare Single Change: Copy path from PR into job so its in path. /* will run all files. Normally, you should only have a specific file: Should look like something.
  * Example Admin Change: config/json_workspaces/admin/service_account_json_file.json
  * Example Non-Production Change: config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet/nastagingpci/db_backup/service_account_json_file.json
  * Example Production Change: config/json_workspaces/prod/namespaces/puppet/secrets/puppet/pciprod/db_backup/service_account_json_file.json
  * Example Change for applying entire folder: config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet/nastagingpci/db_backup/*
* Enter username and password. Set mount_path to ldap or prod-ldap
  * Admin: ldap
  * Use your corporate ldap credentials)
  * Non-Production: ldap
* Use your corporate ldap credentials)
  * Production: prod-ldap (unless kubernetes namespace which is ldap)
  * Use your production ldap credentials unless the kubernetes namespace which is the corporate ldap credentials)
* Click Run Job Now Button

## Manual Secret and Configuration Deployment

Secrets and Vault configurations can be deployed to the root namespace or a specific application team workspace. Clover uses JSON-formatted code for deployments. All Vault APIs are configurable, including:

* **Auth Methods**
* **Secret Engines**
* **System**

Each API command requires careful configuration and adherence to expected formats.  The JSON configuration follows this structure:

```json
{
  "api_paths": [
    {
      "api_path": "v1/sys/mounts/demo",
      "api_action": "post",
      "api_payload": {
        "type": "kv",
        "description": "Used for Demoing Seeding Secrets"
      }
    }
  ]
}
```

Each API call requires an `api_path`, `api_action`, and `api_payload`. The `api_payload` can be modified using the following operational values:

* **`convert_base64_keys`**: Converts target values to Base64 encoding (useful for large binary values).
* **`wrapped_token`**:  Sensitive API payloads should *never* be committed to source control. Instead, use Vault's Cubbyhole secret engine to generate a temporary wrapped token containing the sensitive JSON data. The deployment script will decrypt this token before applying the changes.

`api_action` should be `"post"` for creating or updating information and `"delete"` for deleting.  Delete actions are destructive and non-recursive. List commands are available for inspecting the Vault state, but "get" requests are prohibited by default, enhancing security.

**Following industry best practices, all infrastructure as code for Vault is managed using GitOps.**


## GitOps and Source Control

All source code for managing Vault is located at [https://github.corp.clover.com/clover/vault](https://github.corp.clover.com/clover/vault) and should be treated with a GitOps approach. This ensures auditable, reproducible, and reliable management of Vault configurations.

Secrets are stored in the GitHub repository under:

* `config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet`
* `config/json_workspaces/prod/namespaces/puppet/secrets/puppet`

Each secret resides in its own file. Automation deploys these changes to the Vault clusters, maintaining a consistent state between Git and the Vault instances.  Each config file contains an `api_path` and `api_payload`.  All secrets in these folders are encrypted by Vault and prefixed with `vault:v1`.


## Managing Secret Data with Transit Engine (Enhancing Security with Encryption at Rest)

All Vault namespaces utilize the Transit secret engine.  This allows Vault to encrypt values using a key that's rotated frequently, ensuring robust data protection. The decryption key is safely stored and managed within Vault.

* **Encryption:** To encrypt values, your username needs the `namespace-encryption-encrypt` role.
* **Decryption:**  Decrypters (typically operations teams) who store data in Vault require the `namespace-encryption-decrypt` role.

The provided Python script encrypts values using the Transit engine:

```bash
git clone git@github.corp.clover.com:clover/vault.git
cd vault
set +o history
export LDAP_USERNAME=$USER
export LDAP_PASSWORD=<<your password>> # **Replace with your actual password**
set -o history
python3 bin/encrypt_secret_data.py --name=vault-nonprod01 --path=test.json --auth-method=ldap --mount-path=ldap --log-level=DEBUG --namespace=puppet
```

Remember to modify LDAP credentials, file path, and target namespace (e.g., `puppet`, `kubernetes`, or `gcp`) as needed.  The vendor documentation for the Transit backend is available [here](link_to_transit_docs).


**Example:** Encrypting a sample JSON file:


**Plaintext Input:**

```json
{
  "_namespace": "techops",
  "api_paths": [
    {
      "api_path": "v1/techops-admin/test_secret",
      "api_action": "post",
      "api_payload": {
        "username": "test",
        "password": "supposedtobesecret"
      }
    },
    {
      "api_path": "v1/techops-admin/test_secret_base64",
      "api_action": "post",
      "decode_base64_keys": [
        "password"
      ],
      "api_payload": {
        "username": "test",
        "password": "c3VwcG9zZWR0b2Jlc2VjcmV0"
      }
    }
  ]
}
```

**Encrypted Output:**

```json
{
  "_namespace": "techops",
  "api_paths": [
    {
      "api_action": "post",
      "api_path": "v1/techops-admin/test_secret",
      "api_payload": {
        "password": "vault:v1:QfbVnB7wiQiKD+sA0SrsTuBwdClGmHxNDp41QBsaCNBD23ZAGXrjEALHYtGN7w==",
        "username": "vault:v1:qCfQ4TUjxOiuAOjWp+cZsgcyNBF5LpzFkLo7rddXHUg="
      },
      "transit_encoded_keys": [
        "username",
        "password"
      ],
      "transit_key": "namespace-encryption",
      "transit_secret_engine": "transit"
    },
    {
      "api_action": "post",
      "api_path": "v1/techops-admin/test_secret_base64",
      "api_payload": {
        "password": "vault:v1:arTTdvusm8J3gWmXBQ4/m+9DFH09J3jnmG3F9icLxtNhmnyrYUWEF5HQAM0WJg==",
        "username": "vault:v1:M+uGPrJVKbu8AP4ieqJ7WtQhTjv+d4lvVi09M2hLG0U="
      },
      "transit_encoded_keys": [
        "username",
        "password"
      ],
      "transit_key": "namespace-encryption",
      "transit_secret_engine": "transit"
    }
  ]
}
```

After committing the encrypted file to Git, request review from `@vault-approvers` in the #vault Slack channel.


## Decrypting Data

```bash
export LDAP_USERNAME=<username>
export LDAP_PASSWORD=<password>
export VAULT_NAMESPACE=puppet
export VAULT_ADDR="https://vault-usprod01.corp.clover.com"
vault login -method=ldap -path=prod-ldap username=$LDAP_USERNAME password=$LDAP_PASSWORD
vault write transit/decrypt/namespace-encryption ciphertext=<<cipher text>>
echo "<<base64 content from above>>" | base64 -D
```

## Deploying with Rundeck (Automated Deployments)

Once merged into master, Infrastructure and Application teams use Rundeck jobs to deploy changes from the Vault Git project (`config/json_workspaces/<target_cluster>/<admin|namespace>`) to Vault using the `manage-data` script. The directory structure is:

```
json_workspaces
├── nonprod
│   ├── admin/<<json code>>
│   └── namespaces
│       ├── <<target_namespace>>/<<json code base>>
│       └── <<target_another_namespace>>/<<json code base>>
└── prod
    ├── admin/<<json code>>
    └── namespaces
        ├── <<target_namespace>>/<<json code base>>
        └── <<target_another_namespace>>/<<json code base>>
```

Only administrators can modify code in the `admin` folder. Other teams should use their dedicated namespaces.

**Deployment Steps:**

1. Request deployment from infra/security teams via a Rundeck job.
2. A Support Engineer logs into Rundeck's release project and runs the Vault / `<target cluster>` / Manage Cluster Data (`<target cluster>`) job.
3. Enter LDAP credentials and the request payload (e.g., `nonprod/admin` or `nonprod/namespace/kub_poc`).
4. Click "Run Job".

# Managing Secrets in Vault at Clover (Kubernetes)
Please refer to latest documentation [here](https://github.corp.clover.com/clover/gke-cluster-manager/wiki/Vault)

# Managing Secrets in Vault at Clover (Puppet)
Vault is now used to store Puppet secrets.  The following sections detail how to interact with Vault for secret management:

## Installing HVAC

If you are using our custom Vault Python code on your personal laptop, ensure Python 3 is installed and then install all requirements using the repository's local requirement file:

```bash
pip3 install -r requirements.txt --user
```

## Looking up Secrets in Vault

### Using Hiera Lookups

A specialized Puppet lookup function retrieves secrets from Vault.  Unlike Puppet eyaml lookups, all Puppet nodes using Vault must set one of the following:

* Child App Env (e.g., `dev::dev25`)
* App Env (e.g., `dev` or `usprod`)
* Env (e.g., `prod` or `usprod`)

Unlike eyaml, if a secret lookup fails, the function won't return an empty value; instead, it will fail. For example:

```
Executing: /opt/puppetlabs/bin/puppet agent --test --noop --environment=production --detailed-exitcodes
Info: Using configured environment 'production'
Info: Retrieving pluginfacts
Info: Retrieving plugin
Info: Retrieving locales
Info: Loading facts
Error: Could not retrieve catalog from remote server: Error 500 on SERVER: Server Error: [hiera_vault_lookup] Unable to find value for key vault:cos/lightweight_merchant_inquiries_service_security_token/skcrypted on node dev1-cos02.dev.pdx10.clover.network
Warning: Not using cache on failed catalog
Error: Could not retrieve catalog; skipping run
WARNING: Possible failure (1) - FAIL, compile failed or another run in progress
Reminder: noop run, no changes actually applied
```

In this case, ensure a secret exists in one of these Vault locations under the Puppet namespace:

* Child AppEnv Location: `/v1/puppet/dev1/cos/lightweight_merchant_inquiries_service_security_token`
* App Env or Legacy Env Location: `/v1/puppet/dev/cos/lightweight_merchant_inquiries_service_security_token`
* Default Secret Location: `/v1/puppet/default/cos/lightweight_merchant_inquiries_service_security_token`

To look up a secret, specify:

```puppet
encrypt_secret: "%{lookup('vault:encrypted_json/encrypted_secret')}"
```

The plugin will search for a secret in the following order:

1. Child AppEnv: `/v1/puppet/dev25/encrypted_json`
2. AppEnv: `/v1/puppet/dev/encrypted_json`
3. Legacy Env: `/v1/puppet/prod/encrypted_json`
4. Default: `/v1/puppet/default/encrypted_json`

This precedence allows inheritance without specifying all environments.  The absence of an MDB tag simply skips that location.  These locations are configured via the Vault Hiera Lookup Function in the `hiera.yaml` file in the Puppet repo.  Production environments should reside in production clusters, and non-production secrets in non-production clusters. Refer to the `hiera.yaml` file for cluster mappings.


### Using a Puppet Read Function

Unlike Hiera lookups, using the Puppet read function requires knowing the secret's path and cluster:

```puppet
$vault_url = lookup('vault::cluster_url')
$encrypted_secrets = vault_read($vault_url, "/v1/puppet/${::_appenv}/clover_encrypted_secret", $vault_namespace)
$clover_encrypted_username = $encrypted_secrets['username']
$clover_encrypted_password = $encrypted_secrets['password']
```

Ideally, secrets should be passed via Hiera lookups as sensitive values to avoid Vault-specific logic within Puppet modules.


## Deploying and Managing Secrets

### Deploying a Secret via the GUI

**Do not update production secrets via the GUI except in break-glass situations with leadership approval.** All GUI changes must be immediately committed to source control.

* **Non-Production:**
    * URL: [https://vault-nonprod01.corp.clover.com/ui/vault/auth?namespace=puppet&with=ldap](https://vault-nonprod01.corp.clover.com/ui/vault/auth?namespace=puppet&with=ldap)
    * Credentials: Corporate LDAP
    * Namespace: Puppet
* **Production:**
    * URL: [https://vault-usprod01.corp.clover.com/ui/vault/auth?namespace=puppet&with=ldap](https://vault-usprod01.corp.clover.com/ui/vault/auth?namespace=puppet&with=ldap)
    * Credentials: Production LDAP
    * Namespace: Puppet


Secrets are created/edited under the appropriate `App Env`, `Env`, or `default` location.  Use the JSON tab for JSON secrets.  Remember: the Puppet namespace does not use KV2; there's no backup unless committed to the Puppet repo.  All GUI changes *must* be source controlled.


### Encrypting a Secret with the Transit Engine

To encrypt a secret for source control without Python scripts:

1. Log into the Vault cluster using LDAP credentials. Select the correct namespace (`puppet`/`kubernetes`/etc.).
2. Open the terminal in the upper left corner.
3. Run this command (the plaintext value must be a Base64 encoded string *without* brackets):

```bash
vault write transit/encrypt/namespace-encryption plaintext=<<base64 text>>
```

To Base64 encode a string:

```bash
echo -n "thisismysecret" | base64
```


### Deploying a Puppet Secret via Rundeck

All production Puppet secrets are deployed via Rundeck. Access is restricted. Source code is located at [https://gitlab.dev.clover.com/operations/vault](https://gitlab.dev.clover.com/operations/vault).  Even in non-production, use Rundeck (especially if you lack Vault GUI access).  Automated Rundeck jobs using this code are the standard.  See "How do I deploy data into Vault" for more details.


Secrets are source-controlled in GitLab:

* `config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet`
* `config/json_workspaces/prod/namespaces/puppet/secrets/puppet`

Each secret is in its own file. Automation may overwrite changes if this pattern isn't followed. The Vault folder path is reflected in these folders.  Each secret has an API path and payload.  All secrets are encrypted by Vault and start with `vault:v1`.  Example:

```json
{
    "_namespace": "puppet",
    "api_paths": [
        {
            "api_action": "post",
            "api_path": "v1/puppet/default/sendgrid/client/eut",
            "api_payload": {
                "password": "vault:v1:G4dgxwVpyb1gcaIzfR/r7v2GsGUDex17SVRp27fLFbIGnGuACAUCPDpkbWLbh5kLS8YNYB6jZA==",
                "user": "vault:v1:MmR2YI2PI8BCmqnUaUuLAtMaNCXY24WHJtXB8zq+etK9FSRxVQktXPHkGoBpPvFhtn2GxGHrJg=="
            },
            "transit_encoded_keys": [
                "password",
                "user"
            ],
            "transit_key": "namespace-encryption",
            "transit_secret_engine": "transit"
        }
    ]
}
```

To encrypt this using the provided scripts, follow these steps:

1. Clone the repository: `git clone git@github.corp.clover.com:clover/vault.git`
2. Checkout a new branch: `git checkout -b "rw_sample_branch"`
3. Set LDAP credentials: `export LDAP_USERNAME="<<ldap credentials>>"; export LDAP_PASSWORD="<<ldap credentials>>"`
4. Encrypt the file: `python3 bin/encrypt_secret_data.py --name=vault-nonprod01 --path=./config/json_workspaces/nonprod/namespaces/puppet/secrets/encrypt_data.json --auth-method=ldap --mount-path=ldap --auth-namespace=puppet`

Commit changes to GitLab and create a merge request.


### Syncing Secrets from Vault into the Vault Repository

To sync secrets after GUI changes:

1. Clone the repository.
2. Checkout a new branch.
3. Install requirements: `pip3 install -r requirements.txt --user`
4. Set LDAP credentials.
5. Reconcile secrets: `python3 bin/sync_local_secrets.py --name=vault-nonprod01 --source-namespace=puppet --source-kv=puppet --source-path=/ --file-path=./config/json_workspaces/nonprod/namespaces/puppet`
6. Commit and push changes.  Create a merge request.


The `--source-path` option can limit the sync to a specific path (e.g., `--source-path=/dev/cos/`).  Target folder paths must end with `/`; target secrets should not.


### Handling Sensitive Values and Hashes

Puppet lookup functions default to string casting. To specify Hash or Sensitive types, modify the `hiera.yaml` file:

```yaml
lookup_options:
  '^profile::myapp::sensitivevalue::.*':
    convert_to: 'Sensitive'
  '^profile::my_app::some_hash:
    convert_to: 'Hash'

profile::my_app::sensitivevalue::username: "%lookup('vault:myapp/sensitivevalue/username')"
profile::my_app::sensitivevalue::password: "%lookup('vault:myapp/sensitivevalue/password')"
profile::my_app::some_hash: "%lookup('vault:myapp/some_hash')"
```


### Reading a File as a String

To read a file into Vault:

* Use Ruby to escape the string properly: `sudo cat <<some file>> | /opt/puppetlabs/puppet/bin/ruby -e 'puts ARGF.read.dump'`
* Use Base64 encoding: `base64 <<some file>>`

Note: Extra steps might be needed with Base64 values, as the transit secret engine requires Base64 conversion before encryption.