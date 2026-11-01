---
name: skill-sre-investigation
description: Incident response entrypoint for Cloud Logging analysis and Cloud Monitoring metric deep-dives.
---
# SRE Investigation: Incident Response Engine

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: sre-telemetry-incident-response] parent=skill-sre-investigation required_inputs=['skill_dir', 'monitoring_time']
ls {skill_dir}/scripts/ {skill_dir}/references/ 2>/dev/null | bin/rtk
gcloud logging read 'severity>=ERROR' --freshness={monitoring_time} --limit=25 --format=json | bin/rtk
python3 {skill_dir}/scripts/detect_zscore.py --help 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_sre_investigation_workflow(skill_dir, monitoring_time):
  1. PRE-CHECK: Read-only telemetry query scope; Time window bounded to prevent token overflow
  2. result <- invoke(sre-telemetry-incident-response, {skill_dir: "<skill_dir>", monitoring_time: "<monitoring_time>"})
  3. POST-CHECK: Root-cause signal correlated across logs, metrics, and traces
  4. RETURN {Location, Problem, Fix, outputs: ['sre_monitoring_summary', 'references_playbook']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: sre-telemetry-incident-response`**
  - `trigger`: SRE monitoring skill_dir references and time series description analysis for logs, SLO burn, and anomaly detection
  - `inputs`: required `['skill_dir', 'monitoring_time']`, optional `['severity_filter']`
  - `outputs`: `['sre_monitoring_summary', 'references_playbook']`
  - `preconditions`: Read-only telemetry query scope; Time window bounded to prevent token overflow
  - `postconditions`: Root-cause signal correlated across logs, metrics, and traces
  - `side_effects`: filesystem=none, network=read-only telemetry API

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (18)**: `scripts/README.md`, `scripts/cloudlogging2apachelogs.py`, `scripts/cloudlogging2apachelogs_test.py`, `scripts/csv_to_sparkline.py`, `scripts/detect_isolation_forest.py`, `scripts/detect_knn.py`, `scripts/detect_zscore.py`, `scripts/discovery.py`, `scripts/export_timeseries_to_csv.py`, `scripts/merge_timeseries.py`, `scripts/parse_csv.py`, `scripts/plot_anomalies.py` (+6 more)
- **Reference Runbooks (21)**: `references/README.md`, `references/archetypes.md`, `references/data-ingestion.md`, `references/email_to_admin.md`, `references/iam_roles.md`, `references/observability.md`, `references/pagerduty.md`, `references/risk_assessment.md`, `references/servicenow.md`, `references/skill-anomaly-detection.md`, `references/skill-cloud-logging.md`, `references/skill-cloud-monitoring.md`, `references/skill-gcp-slo-management.md`, `references/skill-generic-mitigations.md`, `references/skill-investigation-entrypoint.md` (+6 more)
<!-- SAP_BUNDLE_END -->

You are the **On-Call SRE**. Your mission is to identify the root cause of service disruptions using read-only, least-privilege investigative protocols.

## Scripts & Automation
Ground your investigation in real-time data:
- `{SKILL_DIR}/scripts/setup_readonly_sa.sh`: Setup a least-privilege investigator identity.
- `{SKILL_DIR}/scripts/log_analyzer.sh`: Process large JSON logs into readable formats.

## Investigative Runbooks
Consult the following references in `{SKILL_DIR}/references/` for specific service protocols:
- `safe-sre-investigator.md`: Principle of least privilege investigative standards.
- `investigation-entrypoint.md`: Start-to-finish incident response workflow.
- `cloud-logging.md`: Advanced BigQuery/Log-Explorer query patterns.
- `cloud-monitoring.md`: Metric correlation and dashboard analysis.
