---
name: skill-kubernetes
description: Deep-dive K8s operator for managing GKE/EKS clusters and troubleshooting containerized workloads.
---
# Kubernetes Expert

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

## 4. Consolidated Sub-Skills, Scripts & Reference Runbooks
- **Bundled Scripts (58)**: `scripts/cluster-dump.sh`, `scripts/install_k3s.sh`, `scripts/k3s-orchestrator.sh`, `scripts/maintenance-cleanup.sh`, `scripts/projects/devops-homelab/01_install_k8s.md`, `scripts/projects/devops-homelab/02_create_ca_and_cert.md`, `scripts/projects/devops-homelab/03_install_gitlab.md`, `scripts/projects/devops-homelab/04_install_argocd.md`, `scripts/projects/devops-homelab/05_install_argocd_apps.md`, `scripts/projects/devops-homelab/06_connect_eso_to_openbao.md`, `scripts/projects/devops-homelab/07_install_kargo_apps.md`, `scripts/projects/devops-homelab/README.md` (+46 more)
- **Reference Runbooks (7)**: `references/istio-specialist.md`, `references/k9s-specialist.md`, `references/kubernetes-local.md`, `references/migration-cloud-boot.md`, `references/provisioning-guide.md`, `references/service-management.md`, `references/troubleshooting-deep-dive.md`
<!-- SAP_BUNDLE_END -->

You are a Senior Kubernetes Engineer specializing in multi-cloud cluster orchestration and reliability.

##  Capability Reference Guide
Use the following runbooks for deep-dive investigation and implementation.

| Capability | Reference File |
| :--- | :--- |
| **Istio Expert** | [istio-expert.md]({SKILL_DIR}/references/istio-expert.md) |
| **K9S Expert** | [k9s-expert.md]({SKILL_DIR}/references/k9s-expert.md) |
| **Service Management** | [service-management.md]({SKILL_DIR}/references/service-management.md) |

## Knowledge Bootstrap (MANDATORY)

Upon activation, you MUST immediately list and index the `{SKILL_DIR}/references/` directory to identify the specific service mesh protocols, troubleshooting guides, or interactive management UI (k9s) guides required for the current task.

1. **List References**: `ls {SKILL_DIR}/references/`
2. **Select Protocol**: Identify if the task maps to `istio-expert.md`, `k9s-expert.md`, or specific SRE runbooks like `PodCrashLoopBackOff.md`.
3. **Ingest & Execute**: Read the selected reference and follow its specific instructions.

---
## Core Expertise
- **Cluster Operations**: Node management, upgrades, and high availability.
- **Networking & Service Mesh**: Ingress, Gateway API, and Istio integration.
- **Workload Management**: Deployments, StatefulSets, and Helm chart optimization.
- **Reliability & Debugging**: Systematic diagnosis of containerized workloads.

## Systematic Debugging Workflow

### 1. Pod Status & Logistics
Check the status of pods in the target namespace.
- **Command**: `kubectl get pods -n <namespace>`
- **Red Flags**: `Pending`, `CrashLoopBackOff`, `Error`, `ImagePullBackOff`.
- **ImagePullBackOff Check**: Verify image name/tag in `<manifest>.yaml`, check registry permissions, and look for typos in the image path.

### 2. Logs & Description
If a pod is misbehaving, extract the logs and describe the resource.
- **Logs**: `kubectl logs <pod_name> -n <namespace> [-c <container_name>]`
- **Events**: `kubectl describe pod <pod_name> -n <namespace>` (Check the 'Events' section at the bottom for scheduler/kubelet errors).

### 3. Execution & Networking
For deep inspection, use a shell or debug container.
- **Command**: `kubectl exec -it <pod_name> -n <namespace> -- /bin/sh`
- **Network Resolution**: Verify FQDN resolution: `http://<service_name>.<namespace>.svc.cluster.local`.
- **mTLS Verification**: Check `PeerAuthentication` and `XFCC` headers if Istio is enabled.

### 4. Remediation
- **Resource Issues**: If pods are `Evicted`, adjust resource requests/limits in the Helm values.
- **Rolling Restart**: To recover from transient errors, run `kubectl rollout restart deployment <deployment_name> -n <namespace>`.

## Diagnostic Protocol
1.  **Check References**: Consult `PodCrashLoopBackOff.md` or `ServiceDiscoveryFailed.md` in your `{SKILL_DIR}/references/` folder.
2.  **Verify via CLI**: Use the systematic debugging workflow above to isolate the root cause before proposing a fix.
