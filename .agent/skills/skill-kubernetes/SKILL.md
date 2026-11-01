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
ls {SKILL_DIR}/references/ {SKILL_DIR}/scripts/ 2>/dev/null | bin/rtk
kubectl get pods -n {namespace} | bin/rtk
kubectl logs {pod_name} -n {namespace} --tail=100 | bin/rtk
kubectl describe pod {pod_name} -n {namespace} | bin/rtk
bash .agent/skills/skill-kubernetes/scripts/verify-cluster.sh 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_kubernetes_workflow(namespace, pod_name):
  1. PRE-CHECK: kubectl context verified; Reference runbooks indexed in {SKILL_DIR}/references/
  2. result <- invoke(k8s-workload-triage, {namespace: "<namespace>", pod_name: "<pod_name>"})
  3. POST-CHECK: Failure isolated to image, crashloop, probe, resource limit, or network before mutation
  4. RETURN {Location, Problem, Fix, outputs: ['root_cause_category', 'evidence_log_span', 'remediation_cmd']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: k8s-workload-triage`**
  - `trigger`: Diagnose Kubernetes pod status, container logs, events, local k3s cluster state, and service mesh routing
  - `inputs`: required `['namespace', 'pod_name']`, optional `['container_name', 'kubeconfig']`
  - `outputs`: `['root_cause_category', 'evidence_log_span', 'remediation_cmd']`
  - `preconditions`: kubectl context verified; Reference runbooks indexed in {SKILL_DIR}/references/
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
- Use bundled scripts in `{SKILL_DIR}/scripts/` for non-destructive cluster dumps (`cluster-dump.sh`), local k3s setup (`install_k3s.sh`, `k3s-orchestrator.sh`), and maintenance cleanup (`maintenance-cleanup.sh`).
- Never apply unverified manifests or run destructive deletions without explicit user confirmation.

## Reference & Script Routing Index

| Capability Domain | Trigger / Scope | Reference Runbooks & Scripts (`{SKILL_DIR}/`) |
| :--- | :--- | :--- |
| **Pod & Workload Troubleshooting** | CrashLoopBackOff, ImagePullBackOff, OOMKilled, probe/resource failures | `references/troubleshooting-deep-dive.md`, `scripts/cluster-dump.sh` |
| **Service Mesh & Networking** | Istio mTLS, Gateway API, VirtualService, CoreDNS & service routing | `references/istio-specialist.md`, `references/service-management.md` |
| **Interactive Cluster Triage (k9s)** | k9s navigation, resource inspection, log/shell shortcuts | `references/k9s-specialist.md` |
| **Cluster Provisioning & Local k3s** | k3s installation, homelab GitOps (ArgoCD, GitLab, OpenBao/ESO, Kargo) | `references/kubernetes-local.md`, `references/provisioning-guide.md`, `scripts/install_k3s.sh`, `scripts/k3s-orchestrator.sh`, `scripts/maintenance-cleanup.sh`, `scripts/projects/devops-homelab/README.md` |
| **Cloud Boot & Workload Migration** | Containerizing and migrating Spring/cloud apps to Kubernetes | `references/migration-cloud-boot.md` |
