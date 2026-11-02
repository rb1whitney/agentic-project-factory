---
name: skill-sre-investigation
description: Incident response entrypoint for Cloud Logging analysis and Cloud Monitoring metric deep-dives.
---
# Skill: SRE Telemetry & Incident Investigation (`skill-sre-investigation`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: sre-telemetry-incident-response] parent=skill-sre-investigation required_inputs=['monitoring_time']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
gcloud logging read 'severity>=ERROR' --freshness={monitoring_time} --limit=25 --format=json | bin/rtk
python3 .agent/skills/skill-sre-investigation/scripts/detect_zscore.py --help 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_sre_investigation_workflow(monitoring_time):
  1. PRE-CHECK: Read-only telemetry query scope; Time window bounded to prevent token overflow
  2. result <- invoke(sre-telemetry-incident-response, {monitoring_time: "<monitoring_time>"})
  3. POST-CHECK: Root-cause signal correlated across logs, metrics, and traces
  4. RETURN {Location, Problem, Fix, outputs: ['sre_monitoring_summary', 'references_playbook']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: sre-telemetry-incident-response`**
  - `trigger`: SRE monitoring references and time series description analysis for logs, SLO burn, and anomaly detection
  - `inputs`: required `['monitoring_time']`, optional `['severity_filter']`
  - `outputs`: `['sre_monitoring_summary', 'references_playbook']`
  - `preconditions`: Read-only telemetry query scope; Time window bounded to prevent token overflow
  - `postconditions`: Root-cause signal correlated across logs, metrics, and traces
  - `side_effects`: filesystem=none, network=read-only telemetry API
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute read-only SRE monitoring queries and time series description analysis across `monitoring_time` and `severity_filter` for logs, SLO burn, and anomaly detection to produce `sre_monitoring_summary` and `references_playbook`.

### 1. Bounded Read-Only Telemetry Triage
- Bound every log and time-series query with an explicit `monitoring_time` window (`--freshness`) and `--limit` so raw telemetry never overflows context.
- Correlate signals across Cloud Logging, Cloud Monitoring time series, and anomaly detection scripts (`detect_zscore.py`, `detect_isolation_forest.py`, `detect_knn.py`) before proposing mitigations.
  ```bash
  python3 .agent/skills/skill-sre-investigation/scripts/discovery.py --help 2>/dev/null | bin/rtk
  python3 .agent/skills/skill-sre-investigation/scripts/detect_zscore.py --help 2>/dev/null | bin/rtk
  python3 .agent/skills/skill-sre-investigation/scripts/detect_isolation_forest.py --help 2>/dev/null | bin/rtk
  ```

### 2. Incident Governance & Postmortem Discipline
- Enforce read-only least-privilege access (`references/safe-sre-investigator.md`, `references/sre-investigator-iam-roles.md`).
- Document root cause, blast radius, and timeline using the postmortem generator and aggregator playbooks.

## Reference & Script Routing Index

| SRE Capability | Trigger / Scope | Reference Runbooks & Scripts (`.agent/skills/skill-sre-investigation/`) |
| :--- | :--- | :--- |
| **Incident Entrypoint & Safe Triage** | Initial incident triage, read-only SA guardrails, admin IAM request template, risk & mitigations | `references/incident-investigation-entrypoint.md`, `references/safe-sre-investigator.md`, `references/generic-mitigations.md`, `references/sre-investigator-iam-roles.md`, `references/iam-admin-request-email-template.md`, `references/risk-assessment.md`, `scripts/discovery.py` |
| **Cloud Logging Analysis** | Token-efficient log queries, Apache log conversion, error aggregation | `references/cloud-logging-analysis.md`, `references/data-ingestion.md`, `scripts/cloudlogging2apachelogs.py` |
| **Cloud Monitoring & Time Series** | Metric queries, CSV export/merge, sparklines, dual-metric & archetype plots | `references/cloud-monitoring-metrics.md`, `references/monitoring-incident-graphs.md`, `references/monitoring-archetypes.md`, `scripts/export_timeseries_to_csv.py`, `scripts/merge_timeseries.py`, `scripts/preprocess_data.py`, `scripts/csv_to_sparkline.py`, `scripts/plot_archetype.py`, `scripts/reference_dual_plot.py` |
| **Statistical Anomaly Detection** | Z-score, Isolation Forest, and k-NN anomaly detection & plotting | `references/anomaly-detection.md`, `scripts/detect_zscore.py`, `scripts/detect_isolation_forest.py`, `scripts/detect_knn.py`, `scripts/plot_anomalies.py` |
| **SLO Management & Postmortems** | GCP SLO burn analysis, PagerDuty workflows, postmortems | `references/gcp-slo-management.md`, `references/postmortem-generator.md`, `references/postmortem-aggregator.md`, `references/pagerduty.md` |
