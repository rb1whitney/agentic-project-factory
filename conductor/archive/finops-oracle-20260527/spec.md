# Mission Specification: FinOps Oracle Implementation

## Objective
Realize the "FinOps Oracle" vision by implementing high-fidelity cost ingestion, AI-powered resource optimization, and automated decommissioning across the project factory.

## Success Criteria
1.  **Tagging Compliance**: 100% of resources tagged with `Cost-Center` and verified via OPA.
2.  **Cost Ingestion**: Functional Python CLI for querying AWS Athena (CUR) and GCP BigQuery (Billing).
3.  **Ghost Detection**: Gemini-powered detection of orphaned and idle cloud resources.
4.  **Automated PRs**: Generation of "Waste Removal" PRs to surgically decommission identified waste.

## Requirements
- Support for AWS and GCP providers.
- Integration with local project Conductors.
- Adherence to ACS-2026 Unified Standards.
