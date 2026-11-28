---
name: skill-kubernetes
description: Deep-dive K8s operator for managing GKE/EKS clusters and troubleshooting containerized workloads.
---
# Skill: Kubernetes Cluster Operations & Workload Triage (`skill-kubernetes`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: k8s-workload-triage] parent=skill-kubernetes required_inputs=['namespace', 'pod_name']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
kubectl get pods -n {namespace} | bin/rtk
kubectl logs {pod_name} -n {namespace} --tail=100 | bin/rtk
kubectl describe pod {pod_name} -n {namespace} | bin/rtk
bash .agent/skills/skill-kubernetes/scripts/verify-cluster.sh 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_kubernetes_workflow(namespace, pod_name):
  1. PRE-CHECK: kubectl context verified; Reference runbooks indexed in .agent/skills/skill-kubernetes/references/
  2. result <- invoke(k8s-workload-triage, {namespace: "<namespace>", pod_name: "<pod_name>"})
  3. POST-CHECK: Failure isolated to image, crashloop, probe, resource limit, or network before mutation
  4. RETURN {Location, Problem, Fix, outputs: ['root_cause_category', 'evidence_log_span', 'remediation_cmd']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: k8s-workload-triage`**
  - `trigger`: Diagnose Kubernetes pod status, container logs, events, local k3s cluster state, and service mesh routing
  - `inputs`: required `['namespace', 'pod_name']`, optional `['container_name', 'kubeconfig']`
  - `outputs`: `['root_cause_category', 'evidence_log_span', 'remediation_cmd']`
  - `preconditions`: kubectl context verified; Reference runbooks indexed in .agent/skills/skill-kubernetes/references/
  - `postconditions`: Failure isolated to image, crashloop, probe, resource limit, or network before mutation
  - `side_effects`: filesystem=none, network=read-only K8s API GET/LIST
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Diagnose Kubernetes pod status, container logs, events, local k3s cluster state, and service mesh routing for `pod_name` and `container_name` in `namespace` (using `kubeconfig`) to isolate `root_cause_category`, extract `evidence_log_span`, and emit a verified `remediation_cmd`.

### 1. Read-Only Triage Sequence
- Inspect pod phase (`Pending`, `CrashLoopBackOff`, `Error`, `ImagePullBackOff`, `Evicted`), container logs, and scheduler/kubelet events before mutating any workload.
- For service discovery or Istio mesh failures, verify CoreDNS FQDN resolution (`<service>.<namespace>.svc.cluster.local`), `PeerAuthentication` mTLS mode, and `VirtualService` / `DestinationRule` subsets.
  ```bash
  kubectl get pods -n <namespace> -o wide | bin/rtk
  kubectl logs <pod_name> -n <namespace> --tail=100 | bin/rtk
  kubectl describe pod <pod_name> -n <namespace> | bin/rtk
  kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -n 25 | bin/rtk
  ```

### 2. Cluster Provisioning & Local k3s Lifecycle
- Use bundled scripts in `.agent/skills/skill-kubernetes/scripts/` for non-destructive cluster dumps (`cluster-dump.sh`), local k3s setup (`install_k3s.sh`, `k3s-orchestrator.sh`), and maintenance cleanup (`maintenance-cleanup.sh`).
- Never apply unverified manifests or run destructive deletions without explicit user confirmation.

## Reference & Script Routing Index

| Capability Domain | Trigger / Scope | Reference Runbooks & Scripts (`.agent/skills/skill-kubernetes/`) |
| :--- | :--- | :--- |
| **Pod & Workload Troubleshooting** | CrashLoopBackOff, ImagePullBackOff, OOMKilled, probe/resource failures | `references/workload-troubleshooting.md`, `scripts/cluster-dump.sh` |
| **Service Mesh & Networking** | Istio mTLS, Gateway API, VirtualService, CoreDNS & service routing | `references/istio-service-mesh.md` |
| **Interactive Cluster Triage (k9s)** | k9s navigation, resource inspection, log/shell shortcuts | `references/k9s-cli.md` |
| **Cluster Provisioning & Local k3s** | k3s installation, homelab GitOps (ArgoCD, GitLab, OpenBao/ESO, Kargo) | `references/operations-manual.md`, `references/cluster-provisioning.md`, `scripts/install_k3s.sh`, `scripts/k3s-orchestrator.sh`, `scripts/maintenance-cleanup.sh`, `scripts/projects/devops-homelab/README.md` |

## Error Recovery

| Failure / Symptom | Cause | Concrete Fix |
| :--- | :--- | :--- |
| `Operation not permitted: /etc/rancher/k3s/k3s.yaml` | `KUBECONFIG` points to root-owned local k3s file | Export isolated kubeconfig (`export KUBECONFIG=~/.kube/gke-dev.yaml`) before running `get-credentials` |
| Pod stuck in `Init:CrashLoopBackOff` (`127.0.0.6:15002`) | `istio-cni` missing or blocked by Autopilot Warden | Switch to managed Cloud Service Mesh (`istio.io/rev=asm-managed`) or verify `istio-cni-node` DaemonSet |
| `pvc-protection` hangs `kubectl delete pvc --wait=true` | StatefulSet pod still mounts PVC | Delete StatefulSet (`kubectl delete sts --all -n <ns>`) before deleting PVCs |
| Unexpected flag/script failure | Stale `kubectl`/`helm` flag or CRD version | File papercut: `python3 bin/log_papercut.py --skill skill-kubernetes --tried "<cmd>" --expected "<ok>" --actual "<err>" --fix "<fix>"` |
