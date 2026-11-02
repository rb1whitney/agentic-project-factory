# GCP Layout and Hierarchy: Read the Signals

**Read when**: asking where a resource sits in the organization, how environments are separated, or whether a design survives a zone or region failure. Orient with `gcloud projects get-ancestors` from the `gcp-cloud-ops-triage` contract. For the authoritative design guidance, use `architecture-docs.md` in this folder.

Probe status: commands checked with `--help` only; no GCP project was available.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| Project sits directly under the organization with no folder | `gcloud projects get-ancestors <project>` | Report the hierarchy. Propose folders only when policy or IAM needs to differ by group. |
| Dev and prod resources share one project | `gcloud projects list --format='table(projectId,labels)'` | A project is the trust boundary. Propose separate projects for production before any other hardening. |
| Networking lives in each service project | `gcloud compute shared-vpc get-host-project <project>` | Empty: no Shared VPC. Propose a host project only if multiple projects need one network. |
| Service projects attached to a host | `gcloud compute shared-vpc list-associated-resources <host-project>` | Confirm who administers the host network before any firewall change. |
| All instances of a tier in one zone | `gcloud compute instances list --format='table(name,zone.basename(),status)'` | Zonal outage takes the tier down. Propose spreading across zones with a regional managed instance group. |
| Firewall rules reference tags | `gcloud compute firewall-rules list --format='table(name,targetTags.list(),targetServiceAccounts.list())'` | See the tag gotcha below before proposing a change. |

## Gotchas
- Three different things are called tags or labels. Labels are key/value metadata for billing and filtering. Network tags are plain strings on VMs that firewall rules can match. Resource Manager tags are key/value resources that organization policy and IAM conditions can use. Do not substitute one for another.
- Resource scope differs: IAM, VPC networks, firewall rules and global load balancing are global or project-wide; subnets and regional load balancers are regional; instances are zonal.
- Multi-zone inside a region protects against a zone outage only. A regional outage needs a second region and a traffic-steering layer.
