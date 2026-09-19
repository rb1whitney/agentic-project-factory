# Reference: Troubleshooting Encyclopedia (`references/troubleshooting-deep-dive.md`)

## 1. Executive Diagnostic Philosophy: The "Bottom-Up" Protocol
When the cluster fails, do not guess. Follow this sequence:
1. **Host Constraints:** Node resources, Port (6443) availability, Datastore (SQLite/state.db) status.
2. **K8s Object State:** `kubectl` state verification (Pods, PVCs, CRDs).
3. **API Layer:** Kine/SQLite integration point logs.
4. **Application/Operator:** Component logs (`--previous`).

## 2. Failure Pattern Library (Deep Dive)

### 2.1 CrashLoopBackOff (The Pod Lifecycle Killer)
*Symptoms:* Pods failing repeatedly.
*Diagnostic Procedure:*
1. `kubectl get pods -A --field-selector=status.phase!=Running`
2. `kubectl logs <POD> -n <NAMESPACE> --previous`
*Root Causes:*
- **Erroneous Backends:** K3s defaults to SQLite/Kine. If a Helm chart is configured to expect a remote `etcd` (e.g., `ETCD_URLS=http://etcd:2379`), the pod will panic.
- **Secret Missing:** External Secrets operator cannot mount the Vault auth secret.
- **Resource Constraints:** Pod OOM-Killed (check `kubectl describe pod <POD>`).

### 2.2 PVC Pending (Storage Lifecycle)
*Symptoms:* PVC stuck in `Pending`.
*Diagnostic Procedure:*
1. `kubectl describe pvc <NAME> -n <NAMESPACE>`
*Root Causes:*
- **StorageClass Mismatch:** Default `local-path` provisioner only binds when a pod is scheduled to a node. If the pod is not scheduled, the PVC remains Pending.
- **Insufficient Node Resources:** PVC request exceeds node capacity.

### 2.3 Cert-Manager Issuance Failure
*Symptoms:* Ingress certificates show "WaitingForApproval" or "IssuerNotFound".
*Diagnostic Procedure:*
1. `kubectl get certificaterequest -A`
2. `kubectl describe certificaterequest <NAME>`
*Root Causes:*
- **Missing ClusterIssuer:** The Helm chart expects `my-ca-issuer`, but it is not created.
- **CA Secret Missing:** The `root-secret-cacert` is missing in the target namespace.
*Resolution:*
```bash
# Verify issuer
kubectl get clusterissuer my-ca-issuer
# If missing, apply issuer manifest
kubectl apply -f scripts/yaml/cluster-issuer.yaml
```

### 2.4 External Secret Store Failure (OpenBao)
*Symptoms:* `ClusterSecretStore` reports `InvalidProviderConfig`.
*Root Causes:*
- **Auth Misconfiguration:** ServiceAccount mapping to Vault Role is incorrect.
- **Secret Reference:** The `root-secret-cacert` is not in the `external-secrets` namespace.
*Diagnostic:* `kubectl describe clustersecretstore openbao-store`.

### 2.5 CoreDNS/k8s_external Failure
*Symptoms:* 502 Bad Gateway / DNS resolution failures (`host <service>.<ns>.homelab.internal`).
*Resolution:*
1. Inspect CoreDNS ConfigMap: `kubectl get cm coredns-custom -n kube-system -o yaml`.
2. Ensure the `k8s_external` plugin is configured correctly for the `homelab.internal` domain.

## 3. Diagnostic Command Library

### Comprehensive Dump (Support Bundle)
Use `./scripts/cluster-dump.sh` to generate a timestamped support bundle. It executes:
- `kubectl get all -A` (Full Resource dump)
- `kubectl get events -A --sort-by='.lastTimestamp'` (Recent cluster state triggers)
- `kubectl logs ...` (Systematic log extraction from ALL critical operators).

### Interactive Debugging
If a pod cannot be inspected via logs alone, enter its container:
```bash
kubectl exec -it <POD> -n <NAMESPACE> -- /bin/sh
```
*Note:* If the container image lacks `/bin/sh`, use `kubectl debug` with an ephemeral container.

## 4. Root Cause Framework (RCA)
1. **Component Analysis:**
   - Are operators installed? (`helm list -A`).
   - Are CRDs present? (`kubectl api-resources`).
2. **Connectivity Mapping:**
   - Pod-to-Pod traffic: `kubectl run debug --rm -it --image=busybox -- sh`.
   - DNS Resolution: `nslookup github.com` or internal service.
3. **Database Trace (SQLite/Kine):**
   - K3s stores data in `state.db`. If corruption is suspected, analyze via SQLite3 directly (use read-only mode to prevent further damage).
