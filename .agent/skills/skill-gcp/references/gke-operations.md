# GCP Reference: GKE Operations & Hardening

Following industry-standard GKE Best Practices (2026).

## 1. Cluster Configuration
- **Autopilot vs. Standard**: Use Autopilot for most workloads to delegate security hardening and node management to Google.
- **Private Clusters**: Nodes and control plane lack public IPs. Access is managed via Jump hosts, VPN, or IAP.
- **Release Channels**: Use "Regular" or "Stable" for production clusters.

## 2. Pod & Node Security
- **Workload Identity**: Map K8s service accounts to GCP service accounts. Disable the default compute service account.
- **Shielded GKE Nodes**: Provides verifiable node integrity and secure boot.
- **Network Policies**: Use the `GKE Network Policy` (based on Calico or GKE Dataplane V2) to implement pod-to-pod zero-trust security.

## 3. Storage & Persistence
- **GCE Persistent Disk CSI Driver**: Use for managing block storage volume lifecycle.
- **Filestore**: For multi-writer (ReadWriteMany) file shares.
- **Config Connector**: Use for managing GCP resources (Storage, DBs) via Kubernetes manifests.

## 4. Operational Excellence
- **Logging & Monitoring**: Enable GKE system logs and Kubernetes control plane logs in Cloud Operations.
- **Binary Authorization**: Ensures only trusted images are deployed to the cluster.
- **Config Sync**: GitOps tool for managing cluster configuration and policies at scale.