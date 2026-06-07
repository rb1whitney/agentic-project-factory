---
name: skill-gcp-setup
description: Identity manager for initial GCP environment verification and ADC/kubectl authentication alignment.
metadata:
  version: 0.0.2
---
# GCP Environment Setup

Use this skill to verify and harmonize your GCP identities at the start of an investigation or session.

## Core Workflow

1.  **Identity Verification**: Run the bundled `gcp-whoami.sh` script to check all three major identities (gcloud, ADC, and kubectl).
2.  **Harmonization**: If identities mismatch, offer to fix them.
    *   To fix `gcloud`: `gcloud auth login [ACCOUNT]`
    *   To fix ADC: `gcloud auth application-default login`
    *   To fix GKE/kubectl: `gcloud container clusters get-credentials [CLUSTER] --region [REGION] --project [PROJECT]`

## Bundled Scripts

- `{SKILL_DIR}/scripts/gcp-whoami.sh`: Displays current identities for gcloud, ADC, and kubectl.

## Safe Mode Support

If `SAFE_MODE="enabled"` is found in the environment or `.env` file, you MUST activate the `safe-sre-investigator` skill immediately after verifying the initial setup. This ensures all subsequent operations use read-only/non-mutating service accounts.

Note that the `SAFE_MODE` might impact kubectl authorization via RBAC.
