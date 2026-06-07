# Ghost Resource Behavioral Signatures (2026 Standard)

This document defines the signatures used by the FinOps Oracle v2 to identify "Ghost Resources"—cloud assets that are incurring costs but providing no value.

## 1. AWS Signatures (CUR v2 + Resource Explorer V2)

### 1.1 Unattached EBS Volumes
- **Signature ID**: `AWS-EBS-001`
- **Detection Logic**: `line_item_resource_id` exists in CUR v2 with `usage_type` like `%EBS:VolumeUsage%` AND `resource_explorer_v2_status` is `available` (not `in-use`).
- **2026 Attributes**:
  - `last_accessed_via_agentless_scan`: Timestamp of last block-level I/O detected by SCC/Resource Explorer.
  - `cur_v2_line_item_usage_amount`: Cost incurred in the last 24 hours.
  - `ebs_last_attachment_timestamp`: Extracted from CloudTrail/Config.

### 1.2 Idle Load Balancers (ALB/NLB)
- **Signature ID**: `AWS-ELB-002`
- **Detection Logic**: `ActiveConnectionCount` < 5 over 7 days AND `RequestCount` < 10 over 7 days.
- **2026 Attributes**:
  - `network_explorer_v2_flow_logs_active`: Boolean indicating if any VPC Flow Logs show traffic to the LB.
  - `last_request_timestamp`: High-precision timestamp from Nova 2 analysis of access logs.

### 1.3 Orphaned Snapshots
- **Signature ID**: `AWS-EBS-003`
- **Detection Logic**: Snapshot exists but parent volume is deleted.
- **2026 Attributes**:
  - `parent_volume_exists`: Boolean.
  - `snapshot_age_days`: Integer.

## 2. GCP Signatures (BigQuery Billing + SCC Agentless)

### 2.1 Orphaned Persistent Disks
- **Signature ID**: `GCP-GCE-001`
- **Detection Logic**: `usage.amount` > 0 in BigQuery billing AND `scc_agentless_scan_last_seen` > 30 days ago OR null.
- **2026 Attributes**:
  - `scc_agentless_scan_status`: `INACTIVE` or `UNMAPPED`.
  - `bq_billing_usage_amount`: Daily cost.
  - `disk_last_attach_time`: Metadata from Compute Engine API.

### 2.2 Idle Cloud Run Services
- **Signature ID**: `GCP-RUN-002`
- **Detection Logic**: `request_count` = 0 over 14 days AND `spend_caps_status` is `ACTIVE`.
- **2026 Attributes**:
  - `cloud_run_last_request_time`: High-fidelity timestamp from Cloud Logging.
  - `min_instances_config`: Check if `min-instances` > 0 (forcing cost).

### 2.3 Unused Static IPs
- **Signature ID**: `GCP-NET-003`
- **Detection Logic**: IP address status is `RESERVED` but not `IN_USE`.
- **2026 Attributes**:
  - `ip_reservation_age_days`: Time since reservation.
  - `associated_resource_url`: Null if orphaned.

## 3. Cross-Cloud Reasoning Attributes
- `reasoning_engine_confidence`: 0.0-1.0 score from Gemini 3.1 Pro / Nova 2.
- `remediation_risk_level`: `LOW` (Delete), `MEDIUM` (Snapshot & Delete), `HIGH` (Stop/Notify).
- `last_human_interaction_timestamp`: Last time a human touched the resource or its parent project.
