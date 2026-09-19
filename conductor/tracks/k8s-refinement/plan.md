# Tactical Plan: K8s Refinement

## Track 1: Traefik Mesh Shadow Services
- **Location**: Traefik Mesh Config / Helm Values
- **Problem**: Shadow service names >63 chars. K8s validation failure.
- **Fix**: Modify `serviceNameTemplate` in Mesh configuration. Use truncated names or hash suffixes. Ensure total length <63.

## Track 2: ArgoCD Cluster Registration
- **Location**: projects/devops-homelab/argocd-apps/
- **Problem**: vmkube-2 registration manual.
- **Fix**: Implement `ApplicationSet` with `cluster` generator. Target clusters via labels. Automate app deployment to vmkube-2 on registration.

## Track 3: cloud-boot-app ImagePullSecrets
- **Location**: projects/cloud-boot-app/helm/cloud-boot-app/values.yaml
- **Problem**: imagePullSecrets empty. Missing automation.
- **Fix**: Deploy `ExternalSecret` targeting `openbao-store`. Sync registry credentials. Update `values.yaml` to reference `regcred` secret.