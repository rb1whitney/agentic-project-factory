# FinOps Oracle v2: 2026 High-Fidelity Implementation Plan

## 1. Strategic Objective
Replace legacy 2025 FinOps stubs with autonomous, 2026-standard cost optimization engine. Leverage Gemini 3.1 Pro and Amazon Nova 2 for high-reasoning "Ghost Hunting" and automated remediation.

## 2. Technical Stack (2026 Standards)
- **GCP Ingestion**: BigQuery Detailed Billing Exports + Spend Caps API.
- **AWS Ingestion**: Cost and Usage Report (CUR) v2 (Data Exports) + S3 Tables (Iceberg v3).
- **Query Engine**: Athena v4 (AWS) / BigQuery Omni (Cross-Cloud).
- **Reasoning Engine**: Gemini 3.1 Pro (thinking_level: MEDIUM) / Amazon Nova 2 / Claude 4.8 Opus.
- **Discovery**: SCC Agentless Scanning (GCP) / Resource Explorer V2 (AWS).
- **Automation**: Compute Optimizer Automation Rules.

## 3. Phase 1: Characterization & TDD (Success Wall)
- [x] **Step 1.1**: Define "Ghost Resource" behavioral signatures (e.g., unattached EBS, idle LB, orphaned snapshots).
- [x] **Step 1.2**: Write `tests/finops/test_ghost_detection.py` using synthetic billing data.
- [x] **Step 1.3**: Write `tests/finops/test_remediation_safety.py` to verify "Dry Run" logic and PR generation.

## 4. Phase 2: High-Fidelity Data Ingestion
- [x] **Step 2.1 (AWS)**: Configure CUR v2 Data Exports to S3 Tables (Iceberg v3 format).
- [x] **Step 2.2 (AWS)**: Initialize Athena v4 workgroups for Iceberg table optimization.
- [x] **Step 2.3 (GCP)**: Enable Detailed Billing Export to BigQuery.
- [x] **Step 2.4 (GCP)**: Configure Spend Caps API integration for real-time budget enforcement.

## 5. Phase 3: "Ghost Hunting" Discovery Layer
- [x] **Step 3.1 (AWS)**: Implement Resource Explorer V2 aggregator for multi-region asset discovery.
- [x] **Step 3.2 (GCP)**: Integrate SCC Agentless Scanning to identify unmanaged/shadow infrastructure.
- [x] **Step 3.3**: Normalize discovery data into a unified "Asset Inventory" schema.

## 6. Phase 4: Autonomous Reasoning & Remediation
- [x] **Step 4.1**: Implement reasoning logic using Gemini 3.1 Pro (GCP) and Nova 2 (AWS) to correlate billing anomalies with discovery data.
- [x] **Step 4.2**: Configure Compute Optimizer Automation Rules for low-risk rightsizing (e.g., instance type changes).
- [x] **Step 4.3**: Develop "Remediation Agent" to generate GitHub PRs for infrastructure-as-code (Terraform) updates.

## 7. Phase 5: Verification & Governance
- [ ] **Step 5.1**: Execute end-to-end "Ghost Hunt" in staging environment.
- [ ] **Step 5.2**: Verify 100% tagging compliance via automated audit.
- [ ] **Step 5.3**: Final review by `@swarm-auditor`.

## 8. Verification Commands
- **GCP Billing**: `gcloud beta billing accounts exports list --billing-account=$BILLING_ID`
- **AWS CUR v2**: `aws bcm-data-exports list-exports`
- **Ghost Hunt**: `python3 bin/finops_oracle.py --mode=discover --provider=all`
- **Remediation**: `python3 bin/finops_oracle.py --mode=remediate --dry-run`
