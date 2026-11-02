---
name: skill-gcp
description: Holistic Google Cloud expert focusing on production-ready standards and dynamic gcloud discovery.
---
# Skill: Google Cloud Platform Architecture & Operations (`skill-gcp`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: gcp-cloud-ops-triage] parent=skill-gcp required_inputs=['project_id', 'gcp_zone']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
gcloud config get-value project | bin/rtk
gcloud container clusters list --project={project_id} --zone={gcp_zone} | bin/rtk
gcloud logging read 'severity>=ERROR' --project={project_id} --limit=20 --format=json | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_gcp_workflow(project_id, gcp_zone):
  1. PRE-CHECK: gcloud ADC authenticated; Read-only observation commands executed first
  2. result <- invoke(gcp-cloud-ops-triage, {project_id: "<project_id>", gcp_zone: "<gcp_zone>"})
  3. POST-CHECK: GCP project and cluster health verified with zero unmanaged mutation
  4. RETURN {Location, Problem, Fix, outputs: ['identity_state', 'resource_diagnostics', 'remediation_cmd']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: gcp-cloud-ops-triage`**
  - `trigger`: Verify GCP ADC identity, configure OneMCP servers, and execute read-only gcloud GKE, IAM, and playbook inspections
  - `inputs`: required `['project_id', 'gcp_zone']`, optional `['cluster_name']`
  - `outputs`: `['identity_state', 'resource_diagnostics', 'remediation_cmd']`
  - `preconditions`: gcloud ADC authenticated; Read-only observation commands executed first
  - `postconditions`: GCP project and cluster health verified with zero unmanaged mutation
  - `side_effects`: filesystem=none, network=read-only GCP API
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Verify GCP ADC identity (`identity_state`), configure OneMCP servers, and execute read-only `gcloud` GKE (`cluster_name`), IAM, Cloud Run, and playbook inspections in `project_id` and `gcp_zone` to produce `resource_diagnostics` and `remediation_cmd`.

### 1. Identity & Inventory Discovery
- Confirm active ADC identity and project context via `.agent/skills/skill-gcp/scripts/gcp-whoami.sh` and `.agent/skills/skill-gcp/scripts/gcp_inventory.py` before running service queries.
- Execute read-only `gcloud` observation commands piped through `bin/rtk`; route all state-modifying infrastructure changes through declarative Terraform.
  ```bash
  bash .agent/skills/skill-gcp/scripts/gcp-whoami.sh | bin/rtk
  python3 .agent/skills/skill-gcp/scripts/gcp_inventory.py | bin/rtk
  gcloud services list --enabled --project=<project_id> | bin/rtk
  gcloud compute instances list --project=<project_id> | bin/rtk
  ```

### 2. Security & Architecture Hard Rules
- **Private-First**: Enforce VPC-native GKE clusters, Private Google Access, and zero external IPs on databases or build nodes.
- **Identity-First**: Require Workload Identity Federation and short-lived tokens; prohibit long-lived service account JSON keys.

## Reference & Script Routing Index

| Capability Domain | Trigger / Scope | Reference Runbooks & Scripts (`.agent/skills/skill-gcp/`) |
| :--- | :--- | :--- |
| **ADC Setup & Inventory Discovery** | Verify gcloud auth, project inventory, OneMCP server wiring | `references/environment-setup.md`, `references/onemcp-setup.md`, `scripts/gcp-whoami.sh`, `scripts/gcp_inventory.py`, `scripts/verify_setup.py`, `scripts/setup_onemcp.py`, `scripts/test_mcp_endpoint.sh` |
| **GKE & Container Operations** | VPC-native clusters, Workload Identity, Binary Auth, Gateway API | `references/gke-operations.md`, `references/googleapis.com/container.md` |
| **Cloud Run, Build & Resource Manager** | Serverless revisions, error reporting by revision, org/folder hierarchy | `references/googleapis.com/run.md`, `references/googleapis.com/cloudbuild.md`, `references/googleapis.com/cloudresourcemanager.md`, `scripts/report_errors_by_revision.py` |
| **Security & IAM Hardening** | IAM least privilege, Cloud Armor, VPC Service Controls, zero-trust | `references/security-foundations.md` |
| **System Design & Ops Playbooks** | Architecture patterns, operational excellence, triage | `references/architecture-docs.md`, `references/system-design.md`, `references/operational-excellence.md`, `references/sre-playbooks.md`, `references/gke-cloudrun-cloudsql-troubleshooting.md` |
