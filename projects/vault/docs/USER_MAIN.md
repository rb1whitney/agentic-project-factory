# Vault Documentation
Welcome to the vault developer wiki! Please see the Vault Tech Talk Overview [here](https://docs.google.com/presentation/d/1lVrgLrtq_qvSEJPT0nu5sxg-Qzn14VbCUK7EltlKYU0/edit?ts=60428edd#slide=id.gae5db0da25_0_3681). Video Tutorials are [available](https://confluence.corp.clover.com/display/NIT/Vault+Tutorials) for using Vault on Confluence.

## Why Vault?

Clover selected HashiCorp Vault for several key reasons:

* **Centralized Secret Management:**  Consolidates all secrets into a single, secure location, reducing the risk of scattered credentials and improving overall security posture.
* **Improved Security:** Provides robust features like encryption at rest, dynamic secrets, and fine-grained access control, minimizing the risk of unauthorized access and data breaches.
* **Simplified Operations:** Automates secret provisioning, rotation, and management, reducing operational overhead and freeing up engineering time.
* **Enhanced Compliance:** Enforces consistent security policies and auditing capabilities, facilitating compliance with industry regulations.
* **Infrastructure-as-Code (IaC):** Enables version control, automated deployments, and reproducible configurations for improved reliability and manageability.


## Vault Features Utilized at Clover:

* **Secret Engines:**  We leverage various secret engines including Key/Value, Versioned Key/Value, Transit (for encryption/decryption), Certificate Management, SSH Key Management, and Dynamic Secrets (for short-lived database credentials).
* **Authentication Methods:**  Access to Vault is controlled through various authentication mechanisms: LDAP (for users), TLS certificates (for VMs using Puppet), AppRoles (for VMs and containers), Kubernetes Service Account Tokens (for containers), and GCP Role-Based Access (for VMs).
* **Namespaces:** Teams are assigned dedicated namespaces within Vault to manage their secrets independently, promoting better organization and access control.
* **Secret Lifecycle Management:** Vault enables us to define and manage the entire lifecycle of secrets, from generation and distribution to rotation and revocation.


## Vault Architecture and Deployment:

Vault is deployed in GCP across multiple clusters:

* **Production:**  US, Europe, and Latin America clusters.
* **Non-Production:** For development and testing.
* **Admin (Internal CA):** Used for internal Certificate Authority functions.

Each cluster consists of:

* **Frontend Server (port 443):**  Handles human interactions via a web UI (fronted by Apache HTTPD).
* **Backend Servers (port 8200):** Manage cluster state and secret storage; clients do not directly interact with these.

Data replication and daily backups to GCP buckets are implemented for high availability and disaster recovery. Rundeck orchestrates Vault deployments and secret management.

**Cluster URLs:**

| Cluster           | GUI URL                                    |
|-------------------|--------------------------------------------|
| Production        | `https://vault-prod01.corp.clover.com`     |
| Non-Production    | `https://vault-nonprod01.corp.clover.com`  |
| Admin             | `https://vault-admin01.corp.clover.com`    |

These guides cover topics for both administrators and users.

## For Administrators:

* **Cluster Initialization:**  Detailed instructions on initializing a new Vault cluster, including unsealing, key management, and configuring basic access. This includes setting up appropriate authentication methods and configuring necessary policies.
* **Replication:** Explains how to set up and manage Vault replication for disaster recovery and performance optimization. Covers both Disaster Recovery (DR) and Performance replication modes, ensuring high availability and data redundancy.
* **Backup and Restore:** Provides procedures for backing up and restoring Vault data, including ad-hoc backups using scripts and leveraging Vault's integrated snapshot functionality.  This ensures business continuity and data protection.
* **Managing Cluster State:** Describes how to manage Vault configuration using JSON files and scripts, including encrypting sensitive data with the Transit engine.  This allows for version control and automated configuration management.


## For Users:

* **Vault Login:** Provides URLs and authentication methods for accessing different Vault environments (Non-Production, Production Global, Production US).  This includes instructions on utilizing different authentication mechanisms as defined by Clover's security policies.
* **Sharing Secrets:** Outlines the secure procedure for sharing secrets with other Clover employees using Vault's wrapping mechanism, ensuring confidentiality and time-based expiration. This promotes secure collaboration while maintaining strict access control.
* **Onboarding Kubernetes or Puppet Workloads :** Guides users on integrating microservice platform applications with Vault for seamless secret retrieval. This simplifies Kubernetes deployments and improves security by integrating secret management into the application lifecycle.


## Additional Resources:

* **Rundeck Jobs:** Many administrative tasks are automated through Rundeck jobs. You can find these jobs at: [https://rundeck.corp.clover.com/project/release/jobs/vault?jobListType=](https://rundeck.corp.clover.com/project/release/jobs/vault?jobListType=)
* **Vault UI:** You can access the Vault web UI for various operations at:
    * **Non-Production:** [https://vault-nonprod01.corp.clover.com/ui/vault/auth](https://vault-nonprod01.corp.clover.com/ui/vault/auth)
    * **Production:** [https://vault-prod01.corp.clover.com/ui/vault/auth](https://vault-prod01.corp.clover.com/ui/vault/auth)