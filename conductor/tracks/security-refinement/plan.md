# Tactical Implementation Plan: Security Refinement

## 1. OpenBao Auto-Unseal
- **Location**: `projects/devops-homelab/argocd-apps/values/vmkube-1/openbao.yaml`
- **Problem**: OpenBao pods require manual unseal after restart, increasing downtime risk.
- **Fix**: Implement Transit Unseal mechanism. Configure `server.standalone.config` or `server.ha.raft.config` in Helm values to include `seal "transit"` block. Point to a trusted OpenBao instance (or KMS provider) with the transit key.

## 2. Traefik Mesh Default Deny ACLs
- **Location**: `projects/devops-homelab/argocd-apps/values/common/traefik-mesh.yaml`
- **Problem**: Current Istio service mesh lacks Traefik-native zero-trust ACL integration.
- **Fix**: Transition to Traefik Mesh with `acl: true` enabled in controller. Define `MeshSecret` for mTLS enforcement. Implement `HTTPRoute` resources with explicit `parentRefs` to the mesh gateway and `backendRefs` for authorized service communication.

## 3. Crossplane ProviderConfig + ESO Integration
- **Location**: `projects/devops-homelab/argocd-apps/yamls/common/crossplane-eso.yaml`
- **Problem**: Crossplane provider credentials are managed as static Kubernetes secrets, increasing exposure.
- **Fix**: Integrate External Secrets Operator (ESO) with Crossplane. Configure `ExternalSecret` resources to fetch provider credentials from OpenBao `kv-v2` engine. Update `ProviderConfig` objects to use `spec.credentials.secretRef` pointing to the ESO-managed Kubernetes Secret. Ensure `ClusterSecretStore` is authenticated via the `openbao-auth-delegator` service account.