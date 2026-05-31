# Updating HashiCorp Vault and Consul Licenses

This document outlines the procedure for updating licenses on HashiCorp Vault and Consul servers.  It emphasizes best practices for securely managing credentials and efficiently updating multiple instances.

**Before you begin:**

* **Obtain your HashiCorp licenses:**  Ensure you have the latest license keys for both Vault and Consul from HashiCorp.  These will be in a format suitable for pasting directly into the `vault write` and `consul license put` commands.  **Do not** hardcode licenses directly into scripts.
* **Understand your environment:** Identify all your Vault and Consul servers, their addresses, and the appropriate authentication methods (LDAP in this case).
* **Secure credential management:** Using `gopass` (or a similar secure secrets manager) is crucial.  Never hardcode passwords directly in scripts.

## Update Vault and Consul Licenses (Post 1.13)
1. Engage support@clover.com and Sim for new license. PDF will be sent with the key:
2. Follow Standard Vault Change and update following locations:
./config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet/default/consul_license.json
./config/json_workspaces/nonprod/namespaces/puppet/secrets/puppet/default/hashicorp_licenses.json
./config/json_workspaces/prod/namespaces/puppet/secrets/puppet/default/consul_license.json
./config/json_workspaces/prod/namespaces/puppet/secrets/puppet/default/hashicorp_licenses.json
./config/json_workspaces/prod/namespaces/puppet/secrets/puppet/default/vault_license.json
3. Perform a restart of Vault or Consul services using Rundeck [here](https://rundeck.corp.clover.com/project/patch_management/job/show/4b0a5d42-4410-4b1b-874b-39cd7983140a).
* use a regex like vault.*<<prod|admin|dev>>.* and action is restart

## Updating Vault Licenses (Before 1.13)

This section details updating Vault licenses.  Refer to the official HashiCorp Vault documentation for the most up-to-date information: [https://learn.hashicorp.com/tutorials/vault/licenses](https://learn.hashicorp.com/tutorials/vault/licenses)

The following steps illustrate updating the license on multiple Vault instances. Replace placeholders with your actual values.

```bash
# Function to update Vault license on a single instance
update_vault_license() {
  local vault_addr=$1
  local ldap_path=$2
  local vault_namespace=$3

  export VAULT_ADDR="$vault_addr"
  export LDAP_PASSWORD=$(gopass "$ldap_path")
  export LDAP_USERNAME="$USER" # Or a specific username if needed

  vault login -method=ldap -path="$ldap_path" username="$LDAP_USERNAME" password="$LDAP_PASSWORD"

  # Retrieve the current license (optional)
  vault read sys/license

  # Update the license.  Replace  "<<YOUR_VAULT_LICENSE>>" with your actual license.  The format should be a single line string.
  vault write sys/license text="<<YOUR_VAULT_LICENSE>>"

  # Verify the license update
  vault read sys/license
}

# Example usage for multiple Vault instances:
update_vault_license "https://vault-usprod01.corp.clover.com:8200" "prod-ldap" ""
update_vault_license "https://vault-nonprod01.corp.clover.com:8200" "ldap" "puppet"
update_vault_license "https://vault-euprod0101.prod.fra01.clover.network:8200" "prod-ldap" ""
```

**Important Considerations:**

* **`vault_namespace`:**  The `vault_namespace` parameter allows for targeting specific namespaces within Vault if your architecture uses them.  If not needed, leave it blank.
* **Error Handling:** The provided script lacks error handling.  Production-ready scripts should include checks for command success and appropriate logging.
* **License Format:** The Vault license needs to be a single line string.  If your license is multiline, you'll need to adapt it accordingly.


## Updating Consul Licenses (Before 1.13)

This section describes updating Consul licenses. Refer to the official HashiCorp Consul documentation for the most up-to-date information: [https://www.consul.io/docs/agent/options#license](https://www.consul.io/docs/agent/options#license)

The following script updates Consul licenses on multiple servers.  It retrieves an ACL token from Vault to securely manage Consul access.  Replace the placeholders with your actual values.

```bash
# Function to update Consul license on a single server
update_consul_license() {
  local server_name=$1
  local consul_token=$2
  local http_addr="https://${server_name}:8501" # Assumes port 8501

  consul license -token="$consul_token" -http-addr="$http_addr" put "<<YOUR_CONSUL_LICENSE>>"

  # Verify the license update
  consul license -token="$consul_token" -http-addr="$http_addr" get
}


# Example usage, retrieving tokens from Vault:
export LDAP_PASSWORD=$(gopass ldap/corp)
export LDAP_USERNAME=richard.whitney

# Non-prod Consul Servers
export VAULT_ADDR="https://vault-nonprod01.corp.clover.com:8200"
export VAULT_NAMESPACE=puppet
vault login -no-print=true -method=ldap -path=ldap username="$LDAP_USERNAME" password="$LDAP_PASSWORD"
CONSUL_TOKEN=$(vault read puppet/corp/vault/consul --format=json | jq -r '.data.acl_api_token')

while IFS= read -r server; do
  update_consul_license "$server" "$CONSUL_TOKEN"
done < <(tee server.txt <<< "<<nonprod consul servers>>")


# Prod Consul Servers (repeat for other environments like usprod, euprod, etc)
export LDAP_PASSWORD=$(gopass ldap/prod)
export VAULT_ADDR="https://vault-usprod01.corp.clover.com:8200"
export VAULT_NAMESPACE=puppet
vault login -no-print=true -method=ldap -path=ldap username="$LDAP_USERNAME" password="$LDAP_PASSWORD"
CONSUL_TOKEN=$(vault read puppet/usprod/vault/consul --format=json | jq -r '.data.acl_api_token')

while IFS= read -r server; do
  update_consul_license "$server" "$CONSUL_TOKEN"
done < <(tee server.txt <<< "<<usprod consul servers>>")

```

**Important Considerations:**

* **Server List:**  Replace `"<<nonprod consul servers>>"` and `"<<usprod consul servers>>"` with actual lists of your Consul server hostnames or IPs.  Consider using a more robust method for managing server lists than `tee` and a text file,  perhaps a configuration file or a dedicated server inventory system.
* **Error Handling:**  Similar to the Vault script, add error handling and logging for robustness.
* **ACL Tokens:**  Using ACL tokens from Vault provides a more secure way to manage Consul access than hardcoding API keys.
* **`http_addr`:**  Adjust the `http_addr` variable if your Consul servers use a different port or protocol.  Ensure that SSL verification (`CONSUL_HTTP_SSL_VERIFY`) is appropriately set based on your environment.
