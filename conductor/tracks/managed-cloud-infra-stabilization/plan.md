# Implementation Plan: Managed Cloud Infra Stabilization

## 🔍 Analysis & Context
*   **Objective**: Modernize `projects/managed-cloud-infra` to ACS-2026 standards, fix broken dependencies, and promote functional Terraform orchestration.
*   **Affected Files**:
    *   `projects/managed-cloud-infra/.agent/` (New)
    *   `projects/managed-cloud-infra/manifest.json` (New)
    *   `projects/managed-cloud-infra/acs.yaml` (New)
    *   `projects/managed-cloud-infra/terraform/main.tf` (New)
    *   `projects/managed-cloud-infra/AGENT.md` (Update)
    *   `projects/managed-cloud-infra/.gemini/`, `.claude/`, `.copilot/` (Delete)
*   **Key Dependencies**: Terraform, Unified Agentic Standard (ACS-2026).
*   **Risks/Edge Cases**:
    *   Broken symlinks might hide missing logic.
    *   Nested Terraform logic in `2hour-kubernetes` might have hardcoded paths.

## 📋 Micro-Step Checklist
- [x] Phase 1: Standardize Directory Structure
  - [x] Step 1.1: Create `.agent/` directory hub.
  - [x] Step 1.2: Replace broken `agents/` and `skills/` symlinks with physical resident experts.
  - [x] Step 1.3: Decommission legacy vendor directories (`.gemini/`, `.claude/`, `.copilot/`).
- [x] Phase 2: Implement ACS Metadata
  - [x] Step 2.1: Initialize `manifest.json` for Unified Agentic Standard.
  - [x] Step 2.2: Initialize `acs.yaml` for tiered context loading.
  - [x] Step 2.3: Update `AGENT.md` to reflect ACS-2026 protocols.
- [x] Phase 3: High-Fidelity Terraform Orchestration
  - [x] Step 3.1: Create `terraform/variables.tf` with toggle and configuration variables.
  - [x] Step 3.2: Create root `terraform/main.tf` with submodule toggling for AWS and GCP.
  - [x] Step 3.3: Create `terraform/providers.tf` and `terraform/outputs.tf`.
  - [x] Step 3.4: Verify `terraform plan` execution with various toggle combinations.

## 📝 Step-by-Step Implementation Details

### Phase 1: Standardize Directory Structure
1. **Step 1.1 (Create .agent Hub)**:
    *   **Action**: `mkdir -p projects/managed-cloud-infra/.agent/{agents,skills,policies,rules}`
2. **Step 1.2 (Fix Dependencies)**:
    *   **Action**: Remove broken symlinks `projects/managed-cloud-infra/agents` and `projects/managed-cloud-infra/skills`.
    *   **Action**: Populate `.agent/agents/` and `.agent/skills/` with required specialist logic.
3. **Step 1.3 (Decommission Legacy)**:
    *   **Action**: `rm -rf projects/managed-cloud-infra/{.gemini,.claude,.copilot,.cursorrules}`

### Phase 2: Implement ACS Metadata
1. **Step 2.1 (Manifest Initialization)**:
    *   **Target File**: `projects/managed-cloud-infra/manifest.json`
    *   **Content**: Standard v1.8.0 manifest structure.
2. **Step 2.2 (ACS Configuration)**:
    *   **Target File**: `projects/managed-cloud-infra/acs.yaml`
    *   **Content**: Tiered context loading rules (v1.2.0).
3. **Step 2.3 (Protocol Update)**:
    *   **Target File**: `projects/managed-cloud-infra/AGENT.md`
    *   **Action**: Replace legacy content with ACS-2026 System Protocol.

### Phase 3: High-Fidelity Terraform Orchestration
1. **Step 3.1 (Variable Definition)**:
    *   **Target File**: `projects/managed-cloud-infra/terraform/variables.tf`
    *   **Action**: Define `enable_aws` and `enable_gcp` booleans. Define configuration variables (project_id, region, etc.) for both providers.
2. **Step 3.2 (Submodule Toggling)**:
    *   **Target File**: `projects/managed-cloud-infra/terraform/main.tf`
    *   **Action**: Implement `module "aws_infra"` and `module "gcp_infra"` using the `count` or `for_each` pattern based on the toggle variables.
3. **Step 3.3 (Infrastructure Composition)**:
    *   **Target File**: `projects/managed-cloud-infra/terraform/main.tf`
    *   **Action**: Pass configuration variables from the root to the submodules.
4. **Step 3.4 (Verification)**:
    *   **Action**: Run `terraform init` and `terraform plan -var="enable_aws=true" -var="enable_gcp=false"`.
    *   **Success**: Plan generates showing only AWS resources.

## ✅ Success Criteria
1. Project structure adheres to ACS-2026 (Unified `.agent` hub).
2. All broken symlinks removed and replaced with physical resident experts.
3. `manifest.json` and `acs.yaml` present and valid.
4. Terraform root orchestrates submodules with functional toggling and variable exposure.
