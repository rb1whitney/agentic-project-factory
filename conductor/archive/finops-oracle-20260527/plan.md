# Implementation Plan: FinOps Oracle Lifecycle

## Phase 1: Strategic Discovery
- **Action**: Map cloud-specific billing schemas (AWS CUR, GCP BigQuery).
- **Action**: Analyze current Terraform state for tagging non-compliance.

## Phase 2: Tactical Planning
- **Action**: Define implementation plans for `cloud-boot-app` and `managed-cloud-infra`.
- **Action**: Design Python CLI structure and Gemini prompt strategies.

## Phase 3: Execution
- **Task A: cloud-boot-app**
    - Remediated Terraform tagging (mandatory `Cost-Center`).
    - Implemented OPA tagging enforcement policies.
    - Bootstrapped `bin/finops/oracle.py` for AWS ingestion.
- **Task B: managed-cloud-infra**
    - Configured BigQuery billing export stubs.
    - Implemented `bin/finops/ghost_hunter.py` (Gemini-powered).
    - Implemented `bin/finops/pr_generator.py` (Automated decommissioning).

## Phase 4: Verification
- **Action**: Verified Terraform validation and OPA test passes.
- **Action**: Confirmed successful CLI bootstrap and logic integration.
