## Secure Secret Sharing at Clover using HashiCorp Vault:

This document outlines the procedure for securely sharing secrets within Clover using HashiCorp Vault. This change aligns with Clover's commitment to following industry best practices for secret management and enhancing our overall security posture.  Using Vault ensures:

* **Single-use tokens:** Each secret is wrapped in a unique, single-use token. This prevents unauthorized access if the token is intercepted.  Multiple tokens can be created for sharing with multiple individuals.
* **Time-based expiration:**  Secrets have a defined Time-To-Live (TTL). This ensures secrets are automatically deleted after a specified time, reducing the risk of prolonged exposure.
* **Centralized management:**  Vault provides a centralized platform for managing secrets, enabling better control and auditability.
* **Enhanced security:** Vault leverages industry-standard encryption and access control mechanisms, offering a significantly more secure solution compared to third-party services like PrivNote.


**Procedure for Sharing Secrets using Vault:**

The following steps detail how to securely share a secret with another Clover employee using HashiCorp Vault:


**1. Sharing a Secret:**

* **Determine Cluster Endpoint:**
    * **Non-Production:** [https://vault-nonprod01.corp.clover.com/ui/vault/auth?with=ldap](https://vault-nonprod01.corp.clover.com/ui/vault/auth?with=ldap)
    * **Production:** [https://vault-usprod01.corp.clover.com/ui/vault/tools/wrap?namespace=puppet](https://vault-usprod01.corp.clover.com/ui/vault/tools/wrap?namespace=puppet)

* **Authenticate:** Navigate to the appropriate URL above and authenticate using your corporate LDAP credentials. Click the "Sign In" button.

* **Wrap the Secret:** Go to `Tools -> Wrap`. Enter the secret you wish to share securely.  **Critically**, set a reasonable TTL (Time-To-Live) for this token.  The secret will expire if not read by the recipient before the TTL elapses. Click the "Wrap Data" button.

* **Share the Wrapped Token:** Select the "Copy" button to copy the generated wrapped token. Share this token securely (e.g., via a secure messaging system) with the intended recipient.


**2. Receiving and Unwrapping a Secret:**

* **Authenticate:** The recipient should navigate to the appropriate URL (based on Production or Non-Production environment) and authenticate using their corporate LDAP credentials. Click the "Sign In" button.

* **Unwrap the Secret:** Go to `Tools -> Unwrap`. Paste the received wrapped token into the designated field and click the "Unwrap Data" button.

* **Retrieve the Secret:** Select the "Copy" button to copy the unwrapped secret to their clipboard.


**Important Considerations:**

* **TTL:** Choose an appropriate TTL for your secret based on its sensitivity and required lifespan.  A shorter TTL minimizes risk.
* **Security:**  Avoid sharing wrapped tokens via insecure channels (e.g., email). Use a secure communication method.
* **Access Control:**  Ensure that only authorized individuals have access to the Vault instance and appropriate permissions.
* **Auditing:** HashiCorp Vault provides robust auditing capabilities, allowing you to track all access and modifications to secrets.

By following these steps and adhering to the principles of secure secret management, Clover can maintain a more secure and auditable environment for handling sensitive information. 