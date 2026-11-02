# GCP Operations: Read the Signals

**Read when**: checking whether a project is observable, recoverable, and inside its quotas. Orient with the log sink and alert policy probes from the `gcp-cloud-ops-triage` contract; this page interprets results. All changes are propose-only.

Probe status: commands checked with `--help` only; no GCP project was available.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| No log sinks | `gcloud logging sinks list --project <p>` | Logs stay only in default buckets with their retention. Propose a sink to storage or BigQuery if audit retention is required. |
| No alert policies | `gcloud monitoring policies list --project <p> --format='value(displayName)'` | Nothing pages anyone. Propose alerts on the service's SLI before adding dashboards. |
| No uptime checks on a public service | `gcloud monitoring uptime list-configs --project <p>` | Propose an external check from outside the project network. |
| A quota is near its limit | `gcloud compute regions describe <region> --format='yaml(quotas)'`; `gcloud compute project-info describe --format='yaml(quotas)'` | Compare `usage` to `limit`. Propose a quota increase request ahead of a launch, not after a failure. |
| No snapshot schedule on persistent disks | `gcloud compute resource-policies list --format='table(name,region.basename(),snapshotSchedulePolicy.schedule)'` | Propose a schedule and a retention period; state the storage cost. |
| Cloud SQL not highly available or backups off | `gcloud sql instances list --format='table(name,region,settings.availabilityType,settings.backupConfiguration.enabled)'` | `ZONAL` or backups disabled: propose regional availability and backups for production. |
| Deployments are manual | `gcloud builds list --limit 10`; `gcloud deploy delivery-pipelines list --region <r>` | Report what automation exists. Do not add a pipeline when the repo already uses GitHub Actions. |

## Gotchas
- A log sink exports entries written after it is created. It does not back-fill earlier logs.
- Cost attribution depends on labels being present when spend happens. Check label coverage before promising a cost breakdown.
- Alert on symptoms users feel (error rate, latency) before causes (CPU). Use the SLO skill path for burn-rate alerts.
- A snapshot schedule is not a restore test. Propose a periodic restore drill into a scratch project.
