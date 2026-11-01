# Reference: Provisioning Guide (`references/provisioning-guide.md`)

# K3s, Helm, and ArgoCD Setup Guide for Devops-Homelab

## 1. Prerequisites Installation
First, we installed the necessary CLI tools to manage the cluster and deployments.

### K3s (Kubernetes Distribution)
We used the standard K3s installation script.
```bash
curl -sfL https://get.k3s.io | sh -
```
**Architectural Rationale:** K3s is a lightweight, fully compliant Kubernetes distribution, designed to minimize control-plane overhead by replacing etcd with a Kine shim for SQLite. It is the ideal backbone for resource-constrained homelabs or single-server development environments where etcd's distributed consensus overhead is unjustified.

### Helm (Package Manager)
We used the Helm installation script to install Helm 3.
```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```
**Architectural Rationale:** Helm acts as the primary orchestrator for complex infrastructure applications. By utilizing Helm charts, we ensure that operators (like Cert-Manager and Postgres-Operator) are deployed in a predictable, versioned, and templated manner.

### ArgoCD CLI
We downloaded the latest stable release of the ArgoCD CLI.
```bash
curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x /usr/local/bin/argocd
```
**Architectural Rationale:** The ArgoCD CLI is required for managing GitOps configuration—specifically for cluster registration, repository credentials management, and triggering manual syncs when GitOps reconciliation fails.

## 2. Cluster Initialization (WSL2 Context)
In this environment (WSL2 without systemd as init), the K3s service cannot be started automatically via systemd. We initialize it manually.

```bash
mkdir -p /etc/rancher/k3s
k3s server --write-kubeconfig-mode 644 --data-dir /var/lib/rancher/k3s &
```

**Architectural Rationale:**
- `--write-kubeconfig-mode 644`: This security tradeoff is deliberate for development environments. It allows standard user access to the API server without root privileges, enabling local CI/CD scripts and CLI tools to interact with the cluster without escalating privileges.
- `&`: The process is backgrounded to maintain shell control.
- `/etc/rancher/k3s/k3s.yaml`: The default location for the generated kubeconfig.

## 3. ArgoCD Deployment & Project Values
We deployed ArgoCD following the `devops-homelab` requirements.

### Installation
```bash
helm repo add argo https://argoproj.github.io/argo-helm
helm repo update
helm upgrade --install argo argo/argo-cd \
  --namespace argocd \
  --create-namespace \
  --values projects/devops-homelab/argocd-apps/values/vmkube-1/argocd.yaml \
  --wait
```
**Architectural Rationale:**
- `server.insecure: true`: Since SSL termination is handled at the Ingress controller level, we explicitly disable server-side SSL within the ArgoCD pod to avoid certificate complexity in the transit between Ingress and App.
- `server.ingress.enabled: true`: Ensures that Traefik can route external traffic directly to the UI.

## 4. Operator Dependency Chain
The project manifests depend on several CRDs. Failure to apply these in order will lead to "No match for Kind" errors.

1. **Cert-Manager:** `helm install cert-manager jetstack/cert-manager --set crds.enabled=true`.
2. **Postgres-Operator:** `helm install postgres-operator zalando/postgres-operator`.
3. **External Secrets:** `helm install external-secrets external-secrets/external-secrets --set installCRDs=true`.
4. **Kargo:** `helm install kargo ...`.

## 5. Security & mTLS (Internal CA)
We generated a custom CA to manage internal certificates.

### Generation
```bash
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes \
  -key ca.key -days 3650 -out ca.crt \
  -subj "/CN=My Homelab CA" \
  -addext "basicConstraints=critical,CA:TRUE"
```

### Distribution
The CA must exist as a `Secret` in each namespace that relies on Vault or TLS issuance.
```bash
for ns in kargo external-secrets victoria-metrics-k8s-stack gitlab-runner; do
  kubectl create ns $ns || true
  kubectl -n $ns create secret generic root-secret-cacert --from-file=ca.crt
done
```
