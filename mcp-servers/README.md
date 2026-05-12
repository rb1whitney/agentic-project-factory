# Expert Intelligence Hub (MCP)

This directory contains the official **Model Context Protocol (MCP)** servers used to provide high-resolution, real-time intelligence for the expert sub-agents. These servers bridge the gap between AI reasoning and live infrastructure status, official documentation, and cloud registries.

##  Capability Assessment (Grading)

| Directory | Grade | Description | Prime Tool |
| :--- | :--- | :--- | :--- |
| **[mcp-terraform](mcp-terraform)** | **A+** | Registry, provider docs, workspace ops | `get_plan_json_output` |
| **[mcp-aws](mcp-aws)** | **A** | 30+ service-specific servers (docs, IaC, etc.) | `get_vpc_details` |
| **[mcp-github](mcp-github)** | **A-** | Issues, PRs, repos, code search, Actions | `get_issue_details` |
| **[mcp-gcloud](mcp-gcloud)** | **B+** | gcloud CLI bridge, observability, storage | `list_gcs_buckets` |
| **[mcp-gke](mcp-gke)** | **B** | GKE cluster management, node pools | `get_pod_logs` |
| **[mcp-kubernetes](mcp-kubernetes)** | **B** | K8s management, Helm, Tekton | `get_cluster_info` |
| **[mcp-marketplace](mcp-marketplace)** | **B-** | Crossplane XRDs, Compositions | `search_marketplace` |
| **[mcp-security](mcp-security)** | **B-** | Security Command Center, threat intel | `list_findings` |
| **[mcp-google](mcp-google)** | **C** | Index of remote GCP MCP servers | (Reference only) |

##  Management & Orchestration

Use the [**`manage_mcps.sh`**](manage_mcps.sh) orchestrator to build and audit servers.

### 1. Download/Sync
```bash
bash download_mcps.sh
```

### 2. Build Servers
```bash
./manage_mcps.sh build mcp-github
```

### 3. Tool Discovery
List all tools exposed by a specific server to our agents:
```bash
./manage_mcps.sh list-tools mcp-terraform
```

### 4. Health Audit
Verify a server is operationally valid and runnable:
```bash
./manage_mcps.sh health mcp-aws
```

##  Agent Binding

| Agent | Primary MCP | Secondary MCP |
| :--- | :--- | :--- |
| **terraform-expert** | mcp-terraform | -- |
| **aws-expert** | mcp-aws | -- |
| **gcp-expert** | mcp-gcloud | mcp-gke |
| **k8s-expert** | mcp-kubernetes | mcp-marketplace |
| **security-reviewer** | mcp-security | -- |
| **swarm-supervisor** | mcp-github | -- |