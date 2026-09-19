# Migration Strategy: Cloud-Boot-App to Local K3s

## 1. Architectural Goal
Migrate `cloud-boot-app` from a public cloud (AWS) target to a local K3s development environment while maintaining GitOps (ArgoCD) parity.

## 2. Migration Phases
### Phase 1: Values Abstraction
Create `values-local.yaml` to override cloud-specific settings (e.g., LoadBalancer -> NodePort/Ingress, RDS -> local Postgres Operator).

### Phase 2: Manifest Porting
- Port Terraform modules (AWS) to Crossplane Compositions (Local K8s API).
- Configure Crossplane `ProviderConfig` to target `InCluster`.

### Phase 3: GitOps Integration
- Add `cloud-boot-app` to the `root-app` manifests in `scripts/yaml/`.

## 3. Work In Progress
- [ ] Create `values-local.yaml`
- [ ] Map Crossplane `Composition` for K8s-native resources
- [ ] Validate Gatekeeper policies against local deployment
