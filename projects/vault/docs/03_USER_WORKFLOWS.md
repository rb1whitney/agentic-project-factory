# Vault Automation: User Workflows

This guide is for **Developers and End-Users** utilizing the cluster to interact with secrets, transit encryption, and wrapped tokens.

## Secret Injection & Wrapped Tokens

Instead of putting passwords directly in your `.json` configuration files, Vault can wrap a secret and give you a single-use token. This is handled natively.

If you have a JSON file containing a wrapped token payload:
```json
{
    "api_objects": [
        {
            "api_method": "post",
            "api_path": "vault-admin/wrapped-token-test",
            "wrapped_token": "s.1234abcd"
        }
    ]
}
```

You can deploy it directly via:
```bash
python3 bin/cluster_secret_data.py --name dev --path ./wrapped-token-test.json
```

## Transit Encryption Operations

You can leverage Vault's Transit Secret Engine to encrypt and decrypt files without Vault ever storing the contents. This uses the `cluster_encrypt_ops.py` script.

### Encrypt a String
```bash
python3 bin/cluster_encrypt_ops.py encrypt-string --name dev --path /transit/encrypt/my-key --string "my secret string"
```

### Encrypt a File
```bash
python3 bin/cluster_encrypt_ops.py encrypt --name dev --path /transit/encrypt/my-key --file my_data.txt --output my_data.enc
```

### Decrypt a File
```bash
python3 bin/cluster_encrypt_ops.py decrypt --name dev --path /transit/decrypt/my-key --file my_data.enc --output my_data.txt
```

> [!TIP]
> Ensure your Vault Token has the necessary permissions to the `/transit` endpoints.
