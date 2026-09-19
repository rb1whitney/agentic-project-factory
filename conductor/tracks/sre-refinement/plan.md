# SRE Refinement Tactical Plan

## 1. Victoria Metrics Node-Exporter WSL2 Patch
- **Location**: `projects/devops-homelab/argocd-apps/values/common/victoria-metrics-k8s-stack.yaml`
- **Problem**: Default node-exporter Helm values attempt to mount host rootfs, which fails or behaves incorrectly in WSL2 environments.
- **Fix**: Update Helm values to disable `hostRootfs` and adjust paths for WSL2 compatibility.
- **Proposed Change**:
  ```yaml
  prometheus-node-exporter:
    hostRootfs: false
  ```

## 2. DNS as Code (CoreDNS)
- **Location**: `projects/devops-homelab/argocd-apps/values/common/coredns.yaml`
- **Problem**: `gitlab.homelab.internal` resolution currently relies on manual `/etc/hosts` entries or ConfigMap patches, causing drift and management overhead.
- **Fix**: Define static host entries directly in the CoreDNS Helm values via the `hosts` plugin.
- **Proposed Change**:
  ```yaml
  servers:
    - zones:
        - zone: .
      plugins:
        - name: hosts
          inline: |
            192.168.193.1 gitlab.homelab.internal
            192.168.193.1 registry.gitlab.homelab.internal
          fallthrough: true
  ```

## 3. Distributed Tracing (Jaeger) & Traefik Mesh
- **Location**: `projects/devops-homelab/argocd-apps/values/common/traefik.yaml`
- **Problem**: Lack of visibility into request flows across the Traefik ingress/mesh.
- **Fix**: Deploy Jaeger and configure Traefik to export traces.
- **Proposed Change**:
  - Deploy Jaeger using Victoria Metrics stack integration or standalone Helm chart.
  - Update Traefik values:
    ```yaml
    tracing:
      jaeger:
        samplingServerURL: http://jaeger-query:5778/sampling
        localAgentHostPort: jaeger-agent:6831
    ```