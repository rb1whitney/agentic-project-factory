# GCP SRE Troubleshooting Guide: GKE, Cloud Run & Cloud SQL

## 1. GKE Connectivity & Resource Health
- **CrashLoopBackOff**: Inspect pod logs (`kubectl logs`) and events (`kubectl describe`). Check for missing ConfigMaps or Secrets.
- **Node Pressure**: Monitor CPU/RAM metrics in Cloud Monitoring. Use GKE Autopilot to automatically scale nodes.
- **Private Cluster Access**: Ensure Cloud NAT is configured for outbound access or Private Google Access is enabled.

## 2. Cloud SQL Connectivity
- **Cloud SQL Auth Proxy**: Verify sidecar container health. Ensure the service account has `roles/cloudsql.client`.
- **Peer Networking**: If using Private IP, verify VPC Peering status and IP range overlap (RFC 1918).
- **Authorized Networks**: For public IP, verify the source IP is whitelisted.

## 3. Cloud Run Service Failures
- **Cold Start Latency**: Use "Minimum Instances" to keep the service warm.
- **Dependency Issues**: Check VPC Connector status if accessing internal DBs/Redis.
- **IAM**: Verify the service identity has permissions for the resource it's trying to access.

## 4. Diagnostic CLI Commands
```bash
# Verify connectivity
gcloud compute networks peerings list --network=[VPC_NAME]

# Check logs for a specific error
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=10

# Describe SQL instance
gcloud sql instances describe [INSTANCE_NAME]
```