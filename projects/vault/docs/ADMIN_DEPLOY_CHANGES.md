# Cluster Information
Each cluster will then be setup to apply json changes to the cluster from the config/json_workspaces directory that the target cluster users. Two folders will be made available for each cluster:

* admin - used by infrastructure teams to manage cluster specific information that are set at the root level. Namespaces will be onboarded here and the default access to manage said namespaces will also be located here.
* namespaces - each namespace will be dedicated to a certain service or duty at clover. Different auth methods and secret engines will be available in each.

Basic Required Cluster Information:

* api_port:         8200                - This value should not change often by take care to set it if you update Puppet code that configures the API to a non-default value
* api_url:          NA                  - This URL will be a target HA Load Balancer that consumers will use to access Vault
* config_env:       <<nonprod|prod>>    - This value will determine which subfolder under json_workspaces to use for apply target changes via API calls when setting cluster up
* key_encrypt:      true|false          - Determines if the sharded master key is encrypted with keyholder PGP Keys. Suggested to be set to true
* key_send_email:   true|false         - Determine if email is sent out with PGP encrypted master key to each keyholder in addition to being printed out to console and log file. Suggested to be set to true
* key_threshold:    2                   - Minimum Number of Keyholders required to perform Keyholder actions
* servers:          NA                  - Currently this module does not attempt to use MDB to lookup host information, and requires instance names to be provided in case load balancer is not yet ready
* key_holders:      NA                  - Keyholders PGP files that match the owner's email address. Will use each file to re-key Vault and then use the email address to send out an email to them

Each script by default will log information at a log-level of INFO. If you need to debug changes, you can change the value to DEBUG.

## Manage Cluster State

Operations and Application teams will mostly be using a singular script to deploy changes from config/json_workspaces/<<target_cluster>>/<<admin|namespace>> to Vault using the manage-data script. The scripts will authenticate with a variety of auth-methods to perform changes against Vault. Input can either be a directory path or a file path like below:

Be sure to have installed all required python3 libraries by running pip3 install -r requirements.txt --user

```bash
python3 bin/manage_data.py --name=<<vault-cluster-name>> --path=./config/json_workspaces/<<nonprod|prod>>/<<admin/namespace>>/auth.json --log-level=<<INFO|DEBUG> --auth-method=<<ldap|cert|approle|token|k8s>> --mount-path=<<whatever your mount path is. Typically it will be same as auth-method>>
or
python3 bin/manage_data.py --name=<<vault-cluster-name>> --path=./config/json_workspaces/<<nonprod|prod>>/<<admin/namespace>> --log-level=<<INFO|DEBUG> --auth-method=<<ldap|cert|approle|token|k8s>>
```

If passed a directory, all json files will be processed by the script and applied to the Vault Cluster.

Required Sensitive Environment Variables for login:

* approle - APPROLE_ID, SECRET_ID
* cert - CERT_PATH, KEY_PATH, ROLE_NAME
* k8s - JWT_TOKEN, ROLE_NAME
* ldap - LDAP_USERNAME, LDAP_PASSWORD
* token - VAULT_TOKEN

### JSON Payload

Each payload will have the following setup:

```bash
{
  "owner": ["<<Owning Groups Email addresses or Names>>"],
  "api_paths": [
    {
      "api_path": "<<Vault API Path>>",
      "api_action": "<<post|delete",
      "api_payload": { },
      "convert_base64_keys": ["<<some_key_value>>"],
      "wrapped_token": ""
    }
  ]
}
```

Each call will be a separate API_PATH object and each API call requires an API Path, Action, and Payload. The payload can be tweaked or overridden by either the convert_base64_keys or wrapped_token operational values:

* convert_base64_keys - Will convert any target value associated in this array to base64 (useful for bringing in large binary values for Vault)
* wrapped_token - Principally any API payload that is sensitive should never be written to source control. Instead, teams will generate a temporary wrapped token with sensitive Vault JSON information in Vault's Cubbeyhole secret engine that this script will decrypt or use the transit engine to encrypt secrets (preferred)

API action should be type "post" for all actions that you require to create or update information. All delete actions will be type: "delete". Be aware that delete actions are inherently destructive, but they are non-recursive.

API payload supports secrets as strings, arrays of strings and nested objects.

Transit encoded keys should follow the key structure of the API payload, joining nested keys separated by `/`. 
```json
{
  "api_payload": {
    "secret1": "vault:v1:<<encrypted value>>",
    "nested_hash": {
      "secret2": "vault:v1:<<encrypted value>>"
    },
    "secret_array": [
      "vault:v1:<<encrypted value>>",
      "vault:v1:<<encrypted value>>"
    ]
  },
  "transit_encoded_keys": [
    "secret1",
    "nested_hash/secret2",
    "secret_array"
  ]
}
```

Please see following vendor links for how JSON files should be structured for each API endpoint:

* [Auth Methods](https://www.vaultproject.io/api/auth/index.html)
* [Secrets/Secret Engines](https://www.vaultproject.io/api/secret/index.html)
* [System Settings](https://www.vaultproject.io/api/system/index.html)

### Transit Encryption

All namespaces within Vault are created with a defacto transit secret engine. This functionality allows Vault to encrypt a value on behalf of an encoder and then allows a decoder with another role to decode that value. The secret to decode that value is safely stored in Vault and rotated frequently in a keyring. This forces all new values to be encrypted with new encryption key, but always allow preexisting values to always be decrypted. Please see vendor documentation [here](https://learn.hashicorp.com/vault/encryption-as-a-service/eaas-transit) for more details on the transit backend.

To encrypt values stored in any target namespace, you have to ensure your username has the associated namespace-encryption-encrypt role tied to it. Decrypters (typically ops) that will store your data into vault must have the associated namespace-encryption-decrypt role.

You can encrypt values any file to use transit engine by writing it to location:

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

Then encrypt the api payloads by running the following python script:

```
export LDAP_USERNAME=<<your username>>
export LDAP_PASSWORD=<<your password>>
python3 bin/encrypt_secret_data.py --name=vault-nonprod01 --path=./config/json_workspaces/nonprod/namespaces/techops/secrets/encrypt_data.json --auth-method=ldap --mount-path=ldap --namespace=<<target_namespace>
```

The example file will then be encrypted in place like the below and encoders can safely source control this file in the namespace:

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

Then someone with access to cluster may write the data using the manage_data script.

Example run demonstrating the values being decrypted at runtime to store in vault would be:
```bash
richard.whitney@richard vault % python3 bin/encrypt_secret_data.py --name=vault-nonprod01 --path=./config/json_workspaces/nonprod/namespaces/techops/secrets/encrypt_data.json --auth-method=ldap --mount-path=ldap --log-level=DEBUG --namespace=techops
Encrypt Data - INFO - Authorization is successful against https://vault-nonprod01.corp.pdx02.clover.network:8200/v1/auth/ldap/login/richard.whitney. Access is granted to ACL Policies: ["default", "namespace-admin-reader", "namespace-admin-writer", "namespace-encryption-decrypt", "namespace-encryption-encrypt", "namespace-encryption-reader", "namespace-encryption-writer", "namespace-reader", "namespace-writer"]
Encrypt Data - INFO - Writing {u'_namespace': u'techops', u'api_paths': [{u'api_path': u'v1/techops-admin/test_secret', u'transit_encoded_keys': [u'username', u'password'], u'transit_secret_engine': 'transit', u'api_payload': {u'username': u'vault:v1:qCfQ4TUjxOiuAOjWp+cZsgcyNBF5LpzFkLo7rddXHUg=', u'password': u'vault:v1:QfbVnB7wiQiKD+sA0SrsTuBwdClGmHxNDp41QBsaCNBD23ZAGXrjEALHYtGN7w=='}, u'transit_key': 'namespace-encryption', u'api_action': u'post'}, {u'api_path': u'v1/techops-admin/test_secret_base64', u'transit_encoded_keys': [u'username', u'password'], u'transit_secret_engine': 'transit', u'api_payload': {u'username': u'vault:v1:M+uGPrJVKbu8AP4ieqJ7WtQhTjv+d4lvVi09M2hLG0U=', u'password': u'vault:v1:arTTdvusm8J3gWmXBQ4/m+9DFH09J3jnmG3F9icLxtNhmnyrYUWEF5HQAM0WJg=='}, u'transit_key': 'namespace-encryption', u'api_action': u'post'}]} to ./config/json_workspaces/nonprod/namespaces/techops/secrets/encrypt_data.json
richard.whitney@richard vault % python3 bin/manage_data.py --name=vault-nonprod01 --path=./config/json_workspaces/nonprod/namespaces/techops/secrets/encrypt_data.json --auth-method=ldap --mount-path=ldap --log-level=DEBUG
Manage Data - INFO - Authorization is successful against https://vault-nonprod01.corp.pdx02.clover.network:8200/v1/auth/ldap/login/richard.whitney. Access is granted to ACL Policies: ["admin-access", "default"]
Manage Data - INFO - Processing ./config/json_workspaces/nonprod/namespaces/techops/secrets/encrypt_data.json
Manage Data - INFO - Performing post action against API Path and namespace techops: https://vault-nonprod01.corp.pdx02.clover.network:8200/v1/techops-admin/test_secret
Manage Data - DEBUG - API Payload is: {
    "username": "test",
    "password": "supposedtobesecret"
}
Manage Data - INFO - Performing post action against API Path and namespace techops: https://vault-nonprod01.corp.pdx02.clover.network:8200/v1/techops-admin/test_secret_base64
Manage Data - DEBUG - API Payload is: {
    "username": "test",
    "password": "supposedtobesecret"
}
```

If you need to only encrypt a single value, please run the following script:

```bash

richard.whitney@richard vault % python3 bin/encrypt_secret_string.py --name=vault-nonprod01 --string=test --auth-method=ldap --mount-path=ldap --namespace=puppet --encode-string=True
Encrypt Data - INFO - Encoding string into base64 value
Encrypt Data - INFO - Encrypted String is vault:v1:YRktjBY/az4cxqjJGP/5vahqYVNjvUvXNlxi8UyTWto=
```

If you want the script to skip converting an already base64 string and providing input directly, you can perform the following:

```bash

richard.whitney@richard vault % python3 bin/encrypt_secret_string.py --name=vault-nonprod01 --
string=test --auth-method=ldap --mount-path=ldap --namespace=puppet --encode-string=False
Encrypt Data - INFO - Encrypted String is vault:v1:+DcDXvAfH4GgJGNS4mNvbhxCQbh5lIuFxvXflayEMg
```

## Sync Data from K/V to Source Control

If you have need to ensure all secrets are source controlled in this project, you can perform a sync action from the source-kv and have it encrypted with the current namespace's transit key:

```bash
python3 bin/sync_local_secrets.py --name=vault-nonprod01 --source-namespace=kubernetes --source-kv=feedback-dev --file-path=./config/json_workspaces/nonprod/namespaces/kubernetes
python3 bin/sync_local_secrets.py --name=vault-prod01 --source-namespace=puppet --source-kv=puppet --file-path=./config/json_workspaces/prod/namespaces/puppet
```

Be aware that all secrets under the path will be overwritten with what the K/V has and re-encrypted by Vault. If you have a specific path you want to encrypt only, you can specify --source-path=/dev/cos/ or --source-path=/dev/cos/apk_sign_keystore_passwd. All target folders must end with a '/'. A target secret should not.

For syncing all clusters run:
```bash
# Production
export VAULT_ADDR="https://vault-usprod01.corp.clover.com/"
export LDAP_USERNAME=$USER
export LDAP_PASSWORD=$(gopass ldap/prod)
export VAULT_TOKEN=$(vault login -token-only=true -method=ldap -path=prod-ldap username=$LDAP_USERNAME password=$LDAP_PASSWORD
for namespace in $(vault namespace list -format=json | jq -r '.[]' | tr -d '/'); do
  for secret_engine in $(vault read -format=json sys/mounts | jq -r '.data | to_entries[] | select(.value.type == "kv") | .key' | tr -d '/'); do
    python3 bin/sync_local_secrets.py --name=vault-usprod01 --auth-method=ldap --mount-path=prod-ldap --source-namespace=$namespace --source-kv=$secret_engine --source-path=/ --file-path="./config/json_workspaces/prod/namespaces/${namespace}";
  done
done

# Corporate
export VAULT_ADDR="https://vault-nonprod01.corp.clover.com/"
export LDAP_USERNAME=$USER
export LDAP_PASSWORD=$(gopass ldap/corp)
export VAULT_TOKEN=$(vault login -token-only=true -method=ldap -path=ldap username=$LDAP_USERNAME password=$LDAP_PASSWORD)
for namespace in $(vault namespace list -format=json | jq -r '.[]' | tr -d '/'); do
  for secret_engine in $(vault read -format=json sys/mounts | jq -r '.data | to_entries[] | select(.value.type == "kv") | .key' | tr -d '/'); do
    python3 bin/sync_local_secrets.py --name=vault-nonprod01 --auth-method=ldap --mount-path=ldap --source-namespace=$namespace --source-kv=$secret_engine --source-path=/ --file-path="./config/json_workspaces/nonprod/namespaces/${namespace}";
  done
done


# Admin
export VAULT_ADDR="https://vault-admin01.corp.clover.com/"
export LDAP_USERNAME=$USER
export LDAP_PASSWORD=$(gopass ldap/prod)
export VAULT_CLUSTER="vault-admin01"
export VAULT_TOKEN=$(vault login -token-only=true -method=ldap -path=ldap username=$USER password=$LDAP_PASSWORD)
for secret_engine in $(vault read -format=json sys/mounts | jq -r '.data | to_entries[] | select(.value.type == "kv") | .key' | tr -d '/'); do
    python3 bin/sync_local_secrets.py --name=$VAULT_CLUSTER --auth-method=ldap --mount-path=ldap --source-kv=$secret_engine --source-path=/ --file-path="./config/json_workspaces/admin01/admin";
done
```