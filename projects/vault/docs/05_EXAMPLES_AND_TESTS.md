# Vault Automation: Examples and Test Scenarios

This document breaks down the scenarios evaluated in our test suite (`tests/test_integration.py`) so users can replicate them manually.

## Scenario 1: Spinning up a Base Configuration

Deploying the root administrative setup.

```bash
# Point to your Vault server
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="<your_root_token>"

# Deploy Admin Configuration
python3 bin/cluster_secret_data.py --name dev --path ./config/admin
```

## Scenario 2: LDAP Authentication Test

After the admin configuration is successfully deployed, an LDAP method is created. Our fixtures include a mock LDAP user named `vaultdeveloper1`.

You can test LDAP login manually using the credentials parsed from `tests/fixtures/ldap.ldif`:

```bash
vault login -method=ldap username=vaultdeveloper1 password=<password_from_ldif>
```
> Our test suite verifies this returns an exit code of `0`, and also checks that an incorrect password yields an exit code of `2`.

## Scenario 3: Generating and Using Wrapped Tokens

Vault can generate a wrapped token that acts as a secure, one-time passcode.

```bash
# 1. Create a wrapped token payload
vault write sys/wrapping/wrap blah=blah

# 2. Extract the wrapping_token from the output, e.g., 's.wXyZ1234'
# 3. Create a JSON payload:
```

```json
{
    "api_objects": [
        {
            "api_method": "post",
            "api_path": "vault-admin/wrapped-token-test",
            "wrapped_token": "s.wXyZ1234"
        }
    ]
}
```

```bash
# 4. Deploy the wrapped token configuration
python3 bin/cluster_secret_data.py --name dev --path ./wrapped-token-test.json
```

## Scenario 4: Transit Key Restoration (App1)

If you have an exported transit key, you can force-restore it into the `/transit/restore/` endpoint.

```bash
# Ensure App1 config is deployed first
python3 bin/cluster_secret_data.py --name dev --path ./config/app1/secret_engines.json

# Read the backup fixture and restore it
BACKUP_PAYLOAD=$(cat tests/fixtures/app1-transit-key)
vault write /transit/restore/app1-transit-key backup=$BACKUP_PAYLOAD force=true
```
