# GCP Reference: Operational Excellence & Observability

Following the Google Cloud Architecture Framework: Operational Excellence.

## 1. Automation & Deployment
- **Infrastructure as Code (IaC)**: Use Terraform with the Cloud Foundation Fabric for reproducible environments.
- **CI/CD Pipelines**: Use Cloud Build or GitHub Actions to automate testing and deployment.
- **Canary & Blue/Green**: Use Cloud Run or GKE services to manage safe traffic shifting during deployments.

## 2. Monitoring & Logging (Cloud Operations)
- **Cloud Logging**: Centralized logging for all GCP services. Use Log Sinks to export important logs to BigQuery for analysis.
- **Cloud Monitoring**: Dashboards and alerting for service health (SLIs/SLOs). Use Uptime Checks for external verification.
- **Error Reporting**: Automatically aggregates application errors for fast debugging.

## 3. Capacity & Cost Management
- **Quotas**: Manage project-level limits proactively via the API.
- **Cost Allocation**: Use Labels and Tags to track spend by project, team, and environment.
- **Sustainability**: Use the Carbon Footprint tool to monitor and reduce the environmental impact of your workloads.

## 4. Disaster Recovery (DR)
- **Snapshot Schedules**: Automated backups for GCE and Cloud SQL.
- **Regional Failover**: Designing architectures that can recover in a secondary region using Cloud DNS and Global Load Balancing.