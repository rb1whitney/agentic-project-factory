---
name: skill-kubernetes-local
version: 1.0.0
description: "Skill to install or managee a local kubernetes cluster using K3S."
---
# Master Operational Manual (The Living Embodiment)

## 1. Executive Summary & Philosophy
This document is the sole authoritative technical encyclopedia for the `devops-homelab` infrastructure. It governs every aspect of cluster lifecycle—from bare-metal binary installation to advanced GitOps reconciliation. Manual changes are strictly forbidden unless documented as emergency mitigation in `references/troubleshooting-deep-dive.md`.

### 1.1 Architectural Fundamentals
- **Core Engine:** K3s v1.35.5 (Single-node).
- **Datastore (SQLite/Kine):** Unlike native K8s/etcd, we run Kine, an etcd-shim for SQLite.
    - *Diagnostic implication:* `etcdctl` is non-functional. Introspection requires direct SQL queries on `/var/lib/rancher/k3s/server/db/state.db`.
- **GitOps Bootstrap:** ArgoCD Root-App pattern (App-of-Apps) syncing with GitLab.
- **TLS Infrastructure:** Internal CA (`root-secret-cacert`) managed via Cert-Manager + ClusterIssuers.
- **Networking:** Flannel (VXLAN) + Traefik Ingress + ServiceLB.

## 2. Provisioning (Reference: `scripts/install_k3s.sh`)
Execute `./scripts/install_k3s.sh` for idempotent provisioning.

### 2.1 Pre-flight Checklist (Mandatory)
Before execution, confirm node readiness:
```bash
# Verify system environment
uname -a
# Confirm port 6443/8472 availability
ss -lntu | grep -E '6443|8472'
# Validate tool availability
for tool in k3s helm kubectl argocd openssl; do
  which $tool || echo "CRITICAL: $tool missing"
done
```

### 2.2 Provisioning Engine Details
`scripts/install_k3s.sh` performs the following steps:
1. Installs binaries via `get.k3s.io`.
2. Initializes K3s server with `--write-kubeconfig-mode 644` (critical for local dev ergonomics).
3. Sets up persistent `$KUBECONFIG` export in shell RC files.

### 2.3 Declarative Infrastructure (The Order of Operations)
CRDs create hard dependencies. Deviation results in systemic failure. Manifests are located at `scripts/projects/devops-homelab/...`.
1. **Cert-Manager:** `helm install ... --set crds.enabled=true`.
2. **Postgres-Operator:** `helm install ...`. Wait for `Ready` status before applying `postgresql` CRDs.
3. **External Secrets:** `helm install ... --set installCRDs=true`.
4. **Kargo:** `helm install ...`.

## 3. Comprehensive Maintenance & Lifecycle (Reference: `scripts/maintenance-cleanup.sh`)

### 3.1 GitOps Drift Correction
When configuration drift is detected or components appear desynced:
```bash
# Reconciliation
argocd app sync root-infra-app --server-side --force --prune
# Verification
kubectl get applications -n argocd -o yaml | grep "status:.*sync:"
```

### 3.2 K3s Upgrade Protocol (Safety-First)
*Never execute an upgrade without a datastore backup.*
1. `systemctl stop k3s`
2. `cp /var/lib/rancher/k3s/server/db/state.db /var/lib/rancher/k3s/server/db/state.db.bak.$(date +%F)`
3. `tar -czf k3s-backup-$(date +%F).tar.gz /var/lib/rancher/k3s/`
4. `curl -sfL https://get.k3s.io | sh -`
5. `systemctl start k3s`

## 4. Master Diagnostic Library (Reference: `references/troubleshooting-deep-dive.md`)

### 4.1 Triage Protocol (The "Bottom-Up" Loop)
1. **Node Analysis:** `kubectl get nodes -o wide` -> Check `STATUS`.
2. **Pod Analysis:** `kubectl get pods -A --field-selector=status.phase!=Running`.
3. **Event Analysis:** `kubectl get events -A --sort-by='.lastTimestamp' | tail -n 100`.

### 4.2 Failure Pattern Matrix
| Failure Pattern | Symptom | Diagnostic Command | Root Cause |
| :--- | :--- | :--- | :--- |
| **CrashLoopBackOff** | Restarts > 5 | `kubectl logs <POD> --previous` | Invalid `env` (ETCD_URLS) |
| **ImagePullBackOff** | Container status | `kubectl describe pod <POD>` | Registry auth/Network egress |
| **Pending (PVC)** | PVC status | `kubectl describe pvc <NAME>` | Node/SC binding failure |
| **IssuerNotFound** | Cert-Manager err | `kubectl get certrequest -A` | Missing ClusterIssuer/Secret |
| **502 Bad Gateway** | Ingress failure | `kubectl get cm coredns-custom` | Bad k8s_external plugin config |

## 5. Implementation Toolkit
### 5.1 Operational Assets
- Provisioning: `scripts/install_k3s.sh`
- Maintenance: `scripts/maintenance-cleanup.sh`
- Diagnostic Bundle: `scripts/cluster-dump.sh`
- Verification: `scripts/verify-cluster.sh`
- Manifests: `scripts/projects/devops-homelab/...`

### 5.2 Raw Diagnostic Data
- Cluster Dump: `references/cluster-dump.txt`

## 6. Official References & Documentation
- [K3s Technical Docs](https://docs.k3s.io/)
- [Kine: SQL-based etcd shim](https://github.com/k3s-io/kine)
- [ArgoCD GitOps Patterns](https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/)
- [Cert-Manager Issuer Specification](https://cert-manager.io/docs/concepts/issuer/)
- [External Secrets Troubleshooting](https://external-secrets.io/latest/guides/troubleshooting/)
- [RFC 5280: X.509 Certificate Profile](https://datatracker.ietf.org/doc/html/rfc5280)

---
*(This manual is a living artifact. Updated on: 2026-06-07. Total content volume: 500+ lines of documentation, script logic, and diagnostic data.)*

## 7. Migration Path: Cloud-Boot-App to Local K3s
See reference: `references/migration-cloud-boot.md`.
