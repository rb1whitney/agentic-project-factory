# Safe SRE Investigator

This skill helps set up and use dedicated read-only Service Accounts for investigating GCP and Kubernetes resources.
It provides wrapper scripts `safe_gcloud` and `safe_kubectl` to ensure commands are run with these limited-privilege accounts.
When suggesting commands, it includes a risk assessment.


## Core Tasks

1.  **Setup GCP:** Initialize the GCP service account and `safe_gcloud` script.
2.  **Setup Kubernetes:** Initialize the Kubernetes service account and `safe_kubectl` script for a specific cluster.
3.  **Suggest Commands:** Provide `gcloud` or `kubectl` commands with risk assessments.

## 1. Setup GCP (`safe_gcloud`)

When first using this skill for a project, or if the user asks for setup, guide them through the one-time setup process for GCP access.

**Action:** Ask the user for the Project ID.

**Script:** Run the setup script:
```bash
bash ./scripts/setup_safe_sre_investigator.sh PROJECT_ID
```
*   This script is idempotent.
*   It creates `~/bin/safe_gcloud`.
*   The user might need to re-source their shell profile.
*   IAM roles are in `references/sre-investigator-iam-roles.md`.

## 2. Kubernetes Read-Only Access

The upstream Kubernetes setup (`setup_safe_kubectl.sh`, `safe_kubectl_wrapper.sh`, `k8s_readonly_role.yaml`) was never bundled in this repo. Do not invoke them.

**Action:** Ask the user for the cluster context, then use the built-in `view` ClusterRole and read-only verbs only (`get`, `describe`, `logs`). Creating ServiceAccounts or ClusterRoleBindings requires explicit user approval.

## 3. Suggesting Commands

When the user asks for a command:

*   **GCP:** Use `safe_gcloud PROJECT_ID <gcloud commands>`.
*   **Kubernetes:** Use `safe_kubectl CLUSTER_NAME -- <kubectl commands>`.
*   **Risk Assessment:** ALWAYS include a risk assessment block. See `references/risk-assessment.md`.
*   **Write Operations:** For commands requiring write access, provide the standard `gcloud` or `kubectl` command and warn the user to run it with their own credentials, noting the risks.

**Example `safe_gcloud`:**

```bash
# Check GKE cluster status
# Risk: NONE: This is a read-only operation.
safe_gcloud my-project container clusters list
```

**Example `safe_kubectl`:**

```bash
# List pods in the default namespace
# Risk: NONE: This is a read-only operation.
safe_kubectl my-cluster -- get pods -n default
```

## Bundled Resources

*   `scripts/setup_safe_sre_investigator.sh`: GCP setup.
*   `scripts/safe_gcloud_wrapper.sh`: Template for `~/bin/safe_gcloud`.
*   `references/sre-investigator-iam-roles.md`: GCP IAM roles.
*   `references/risk-assessment.md`: Risk assessment format.
