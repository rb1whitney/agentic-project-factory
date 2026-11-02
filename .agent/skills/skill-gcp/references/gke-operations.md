# GKE: Read the Signals

**Read when**: reviewing a GKE cluster's configuration or hardening. Orient with the `gcp-cloud-ops-triage` contract probes (cluster summary as JSON); this page interprets results. All changes are propose-only.

Probe status: the gcloud commands here were checked for existence and flags with `--help` only. No GCP project was available, so output shapes are unverified. Probes return JSON and use `jq`, so a wrong field name yields `null` instead of an error. On `null`, run `gcloud container clusters describe <name> --location <loc> --format=json | jq 'keys'` and find the real field.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| `releaseChannel.channel` is null or `UNSPECIFIED` | `gcloud container get-server-config --location <loc> --format='yaml(channels)'` | Report the cluster is on a static version. Propose a channel and state the upgrade cadence trade-off. |
| `privateClusterConfig.enablePrivateNodes` false or null | `gcloud container clusters describe <name> --location <loc> --format=json \| jq '.masterAuthorizedNetworksConfig'` | Public nodes: propose private nodes. Check `masterAuthorizedNetworksConfig` before touching the control-plane endpoint. |
| `workloadIdentityConfig.workloadPool` null | same describe | Pods use the node service account. Propose Workload Identity and per-workload service accounts. |
| Node pool uses the default Compute Engine service account | `jq '.nodePools[].config.serviceAccount'` | Propose a dedicated least-privilege node service account. |
| No network policy enforcement | `jq '{np:.networkPolicy, dp:.networkConfig.datapathProvider}'` | Neither set: pod-to-pod traffic is open. Propose enabling the dataplane that enforces policy, then add policies in a test namespace. |
| `binaryAuthorization` unset | `jq '.binaryAuthorization'` | Report only; enforcement needs a policy and an attestation pipeline, which is a project of its own. |
| Pods failing after a change | `gcloud container operations list --filter='status!=DONE' --location <loc>` | Wait for running operations to finish before diagnosing. Then use the `k8s-workload-triage` contract. |

## Gotchas
- Autopilot manages nodes and applies hardening for you but restricts privileged workloads and some node-level settings. Check workload requirements before recommending it.
- A cluster's nodes and control plane are separate upgrade surfaces. Ask which one a version number refers to.
- Access to a private control plane goes through authorized networks, a bastion, VPN or IAP. Do not propose opening the public endpoint to fix a connectivity problem.
- Config Connector and Config Sync manage state from Git. If either is installed, change the repo, not the live object.
