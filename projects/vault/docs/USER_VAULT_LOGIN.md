# Accessing the Clover Vault

This document outlines the process for accessing the Clover Vault, adhering to vendor best practices for secure access and management of secrets.  We utilize HashiCorp Vault to securely store and manage sensitive information across various Clover environments.  Different environments and access levels require specific login procedures.  Failure to follow these instructions may result in access denial.

## Accessing Different Vault Environments

The following URLs are used to access different Vault environments.  Note that access to specific environments may be restricted based on your role and responsibilities.

| Environment     | URL                                                | Notes                                                                                                           |
|-----------------|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| Non-Production  | `https://vault-nonprod01.corp.clover.com/ui/`     | Used for testing and development purposes.                                                                      |
| Production (Global) | `https://vault-prod01.corp.clover.com/`       |  Global production environment.                                                                                  |
| Production (US)  | `https://vault-usprod01.corp.clover.com/`       | Primary US production environment. Changes here replicate to EUPROD and LAPROD.                                |
| Production (EU)  | `https://vault-euprod01.corp.clover.com/`       | Replicates from USPROD; direct access is generally unnecessary.                                                   |
| Production (LA)  | `https://vault-laprod01.corp.clover.com/`       | Replicates from USPROD; direct access is generally unnecessary.                                                   |


## Logging into Non-Production

To access the non-production Vault, follow these steps:

1. **Navigate to the URL:** `https://vault-nonprod01.corp.clover.com/ui/`
2. **Select Namespace:** Choose the appropriate namespace from the following options:
    * `<<leave empty>>`: Root namespace; access restricted to SRE for escalated admin duties.
    * `puppet`: Stores Puppet secrets for all development and corporate environments.  *This is the most common namespace for most users.*
    * `kubernetes`: Stores secrets used by Kubernetes clusters.
    * `gcp`: Temporary escalated access credentials for Google Cloud Platform (GCP).
    * `jenkins`: Secrets used by Jenkins.
    * `techops`: Secrets for Site Reliability Engineering (SRE) Operations.
    * `security`: Secrets for Security Operations.
3. **Select Authentication Method:** Choose "ldap".
4. **Enter Credentials:** Log in using your corporate credentials.
5. **Click Sign-In:** This will take you to the Vault dashboard.  An example dashboard for the Puppet namespace is shown below (image would go here).


## Logging into Production

Production access requires stricter security measures.

1. **Navigate to the appropriate URL:** Select the appropriate URL from the table above depending on your geographic region, though access to `usprod` should be sufficient for most use-cases due to replication.
2. **Select Namespace:** Choose the appropriate namespace:
    * `<<leave empty>>`: Root namespace; access restricted to SRE for escalated admin duties.
    * `device`: Specialized secrets for the device team only.
    * `puppet`: Stores Puppet secrets for all development and corporate environments. *This is the most common namespace for most users.*
    * `kubernetes`: Stores secrets used by Kubernetes clusters.
    * `gcp`: Temporary escalated access credentials for Google Cloud Platform (GCP).
    * `terraform`: Access to secrets for Terraform Enterprise workspaces.
    * `techops`: Secrets for Site Reliability Engineering (SRE) Operations.
    * `security`: Secrets for Security Operations.

3. **Authentication:**
    * **Standard Access (Limited):**  Using "ldap" authentication with your corporate credentials will grant you limited access: encrypting secrets, wrapping temporary tokens for sharing with other Clover employees, and viewing older secret engine structures.  *This does *not* provide escalated access.*
    * **Elevated Access (Requires Production Credentials):**  For escalated access (read access to secrets), you must use a production LDAP account.  To do this:
        * Select "More Options" (located below the password field).
        * Change the mount path to `prod-ldap`.
        * Enter your production credentials.
