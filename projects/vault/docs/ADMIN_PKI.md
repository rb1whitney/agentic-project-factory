# Establishing a Vault-Based Certificate Authority for Clover Internal Infrastructure

This document details the process of creating a Certificate Authority (CA) within HashiCorp Vault to manage certificates for Clover's internal infrastructure.  This approach aligns with industry best practices for secure certificate management, improving the overall security posture and streamlining certificate lifecycle operations.  Using Vault centralizes certificate management, enhances auditability, and reduces the risk associated with managing certificates manually.

We'll be creating three separate intermediate CAs within Vault:

* **Test CA:**  Used for non-production application servers. This allows for testing and development without impacting production environments.
* **PROD CA:** Used for production application servers. This ensures high security and reliability for critical systems.
* **CORP CA:** Used for infrastructure requiring trust from both production and non-production environments (e.g., LDAP). This provides a bridge between the different environments while maintaining appropriate security boundaries.

This tiered approach follows industry best practices by separating environments and reducing the blast radius of any potential compromise.  Each CA will be signed by a separate, offline root CA, further enhancing security.


## Generating Certificate Signing Requests (CSRs)

The following commands generate Certificate Signing Requests (CSRs) for each intermediate CA.  These CSRs will be subsequently signed by the offline root CA maintained by the security team.

**Prerequisites:**

* **LDAP Credentials:** Ensure you have the necessary LDAP username and password with appropriate permissions.  These credentials are used for authenticating to Vault.  **Never hardcode these credentials directly into scripts; use environment variables or a secrets management solution instead.**
* **Vault Access:**  Ensure you have the necessary permissions to interact with the Vault instance.

**Environment Variables:**

```bash
export LDAP_PASSWORD=<YOUR_LDAP_PASSWORD>  # **DO NOT HARDCODE THIS - USE A SECURE METHOD**
export LDAP_USERNAME=<YOUR_LDAP_USERNAME>  # **DO NOT HARDCODE THIS - USE A SECURE METHOD**
export VAULT_SKIP_VERIFY=true # Should only be used for initial setup and testing, remove for production
export VAULT_ADDR="https://vault-admin0101.admin.pdx01.clover.network:8200"
```

**Generating CSRs:**

```bash
vault login -method=ldap -path=ldap username=$LDAP_USERNAME password=$LDAP_PASSWORD

vault write -format=json ca_test_clover_2020/intermediate/generate/internal common_name="Clover Network Test Intermediate Authority" organization="Clover Network" country="United States of America" province="CA" | jq -r '.data.csr' > test_pki_intermediate.csr

vault write -format=json ca_corp_clover_2020/intermediate/generate/internal common_name="Clover Network Corporate Intermediate Authority" organization="Clover Network" country="United States of America" province="CA" | jq -r '.data.csr' > corp_pki_intermediate.csr

vault write -format=json ca_prod_clover_2020/intermediate/generate/internal common_name="Clover Network Production Intermediate Authority" organization="Clover Network" country="United States of America" province="CA" | jq -r '.data.csr' > prod_pki_intermediate.csr
```

These commands generate CSRs and save them to `test_pki_intermediate.csr`, `corp_pki_intermediate.csr`, and `prod_pki_intermediate.csr` respectively.


## Signing the CSRs and Importing Certificates

The generated CSRs (`*.csr` files) need to be signed by the offline root CA.  **This step must be performed by the security team following their established procedures.**  Once signed, the resulting certificates can be imported into Vault.

**Example for `test_pki_intermediate.csr` (Repeat for other CAs):**

```bash
vault write -format=json rootca_test_clover_2020/root/sign-intermediate csr=@test_pki_intermediate.csr ttl=87600h | jq -r '.data.certificate' > intermediate.cert.pem
vault write ca_test_clover_2020/intermediate/set-signed certificate=@intermediate.cert.pem
```


## Accessing the CA Chain

Once the certificates are signed and imported, the complete CA chain is available via these URLs:

* **Test CA Chain:** `curl -k --request GET https://vault-admin01.admin.pdx01.clover.network:8200/v1/ca_test_clover_2020/ca_chain`
* **Corp CA Chain:** `curl -k --request GET https://vault-admin01.admin.pdx01.clover.network:8200/v1/ca_corp_clover_2020/ca_chain`
* **Prod CA Chain:** `curl -k --request GET https://vault-admin01.admin.pdx01.clover.network:8200/v1/ca_prod_clover_2020/ca_chain`

**Note:** The `-k` flag in the `curl` commands disables SSL verification.  This should only be used during initial setup and testing.  Remove this flag in a production environment and ensure proper certificate validation is in place.  Using `-k` weakens security, use a secure method to check certificate chains in production.