# Interacting with Vault and Consul Clusters via Clover's Vault API Project

This guide outlines how to interact with Vault and Consul clusters using Clover's Vault API project.  It assumes you're working on a local Mac workstation.

## 1. Download and Extract Vault and Consul Enterprise

Download the necessary binaries from Artifactory and HashiCorp releases:

```bash
wget https://releases.hashicorp.com/vault/1.7.3/vault_1.7.3_darwin_amd64.zip
wget https://artifactory-ro.corp.clover.com:443/artifactory/ext-vendor-local/consul/consul-enterprise_1.6.2_linux_amd64.zip
unzip vault_1.7.3_darwin_amd64.zip
unzip consul-enterprise_1.6.2_linux_amd64.zip
```

**Note:**  The Consul download link points to a Linux binary. Ensure you download the correct version for your macOS system from Artifactory if this is not suitable.


## 2. Interact with Vault

You'll need to log into the Vault cluster to perform most actions. While some actions can be performed via the Vault GUI, commands like `vault operator debug` and `regenerate root key` require CLI access.

### 2.1 Set Environment Variables

Replace `<cluster address>` with your cluster's address:

```bash
export VAULT_SKIP_VERIFY=true
export VAULT_ADDR=https://vault-nonprod0101.corp.pdx02.clover.network:8200/
```

### 2.2 Login and List Secrets

Log in using LDAP and list available secrets:

```bash
vault login -method=ldap username=richard.whitney
vault secrets list
```

This will output a table similar to:

```
Path          Type         Accessor              Description
----          ----         --------              -----------
admin/        kv           kv_ea9d2e28           Used for Admin KV Secrets
cubbyhole/    cubbyhole    cubbyhole_ea0ec589    per-token private secret storage
demo/         kv           kv_ee9ee42b           Used for Demoing Seeding Secrets
identity/     identity     identity_897f32c4     identity store
pki/          pki          pki_2e315420          Enable Vault PKI Backend
puppet/       kv           kv_c88b413d           Used for Puppet KV Secrets
sys/          system       system_7feb1714       system endpoints used for control, policy and debugging
```

### 2.3 Generate and Manage Root Tokens

For detailed information on Vault operator commands, refer to the [HashiCorp Vault documentation](https://www.vaultproject.io/docs/).

The following steps demonstrate generating, using, and revoking a root token.  **Handle root tokens with extreme caution.**

**Generate Encrypted Operator Token:**

```bash
vault operator generate-root -generate-otp
```

This will output an OTP (One-Time Password).

**Start the Root Token Generation Process:**

```bash
vault operator generate-root -init -otp=<your_otp>
```

Replace `<your_otp>` with the OTP from the previous step. This will display a nonce and progress.  You'll need to repeat the `vault operator generate-root` command until the process is complete (Progress 2/2).


**Decode the Encoded Token:**

```bash
vault operator generate-root -decode=<encoded_token> -otp=<your_otp>
```

Replace `<encoded_token>` and `<your_otp>` with the values obtained from the previous steps. This will output the decoded root token.

**Verify the Root Token:**

```bash
vault token lookup <root_token>
```

This will verify that the token has the `root` policy.

**Revoke the Root Token:**

```bash
vault token revoke <root_token>
```

Remember to revoke the root token as soon as you're finished with it.


## 3. Interact with Consul

To interact with Consul, you'll need the master ACL token.  This token is stored in `hieradata/creds/dev/vault.eyaml` and `hieradata/creds/usprod/vault.eyaml`.

```bash
CONSUL_HTTP_SSL_VERIFY=false consul members -token=<<token>> -http-addr=https://vaultbackend-dr0101.prod.dsm01.clover.network:8501
```

Replace `<<token>>` with your master ACL token. This command will list the Consul cluster members.  You'll see output similar to:


```
Node                 Address            Status  Type    Build      Protocol  DC          Segment
vaultbackend-dr0101  10.130.7.197:8301  alive   server  1.6.1+ent  2         vault-dr01  <all>
vaultbackend-dr0102  10.130.7.196:8301  alive   server  1.6.1+ent  2         vault-dr01  <all>
vaultbackend-dr0103  10.130.7.198:8301  alive   server  1.6.1+ent  2         vault-dr01  <all>
vault-dr0101         10.130.7.201:8301  alive   client  1.6.1+ent  2         vault-dr01  <default>
vault-dr0102         10.130.7.199:8301  alive   client  1.6.1+ent  2         vault-dr01  <default>
```

For more advanced Consul commands (e.g., `operator raft`, `members`, `debug`), consult the [HashiCorp Consul documentation](https://www.consul.io/docs/).