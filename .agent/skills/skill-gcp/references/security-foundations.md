# GCP Security: Read the Signals

**Read when**: reviewing IAM, firewall exposure, org policy, or Cloud Armor attachment for a project. Orient with the `gcp-cloud-ops-triage` contract probes (owner/editor bindings, open firewall rules, org policies); this page interprets results. All changes are propose-only.

Probe status: commands checked with `--help` only, because no GCP project was available. Treat output shapes as unverified until run once against a real project.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| A principal holds `roles/owner` or `roles/editor` | `gcloud recommender recommendations list --recommender=google.iam.policy.Recommender --project <p> --location=global` | Recommendations list unused permissions. Propose predefined roles in their place; never remove a role without the owner. |
| User-managed service account keys exist | `gcloud iam service-accounts keys list --iam-account <sa> --managed-by=user` | Name the consumer, then propose Workload Identity Federation or attached service accounts. |
| Key creation is not blocked | `gcloud org-policies describe constraints/iam.disableServiceAccountKeyCreation --project <p> --effective` | Not enforced: propose enforcing it after the key consumers are migrated. |
| Firewall rule allows `0.0.0.0/0` | `gcloud compute firewall-rules list --filter='sourceRanges:0.0.0.0/0' --format='table(name,network.basename(),direction,targetTags.list(),targetServiceAccounts.list())'` | Propose a narrower source. Note whether the rule targets network tags or service accounts; service accounts are harder to spoof. |
| Subnet without Private Google Access hosts private nodes | `gcloud compute networks subnets describe <s> --region <r> --format='value(privateIpGoogleAccess)'` | `False`: private workloads cannot reach Google APIs without a public IP. Propose enabling it. |
| No VPC Service Controls perimeter around sensitive APIs | `gcloud access-context-manager perimeters list --policy <policy-id>` | Report; perimeters can block legitimate traffic, so propose dry-run mode first. |
| Backend service has no Cloud Armor policy | `gcloud compute backend-services list --global --format='table(name,securityPolicy.basename())'` | Empty column: propose a policy in preview mode (below). |

## Cloud Armor rollout (propose-only)
1. Describe the policy: `gcloud compute security-policies describe <policy>` shows its rules. There is no `rules list` command.
2. Add or edit the rule with preview on: `gcloud compute security-policies rules update <priority> --security-policy <policy> --preview`.
3. Read what it would have blocked: `gcloud logging read 'resource.type="http_load_balancer" AND jsonPayload.previewSecurityPolicy.name="<policy>"' --limit 20 --format=json`.
4. Only after the preview shows no legitimate traffic matched, propose removing `--preview` through the repo's Terraform (`google_compute_security_policy`) so the change is reviewed.

## Gotchas
- Confirm the identity first: `gcloud auth list` and `gcloud config get-value project`. Reading the wrong project produces a confident wrong answer.
- Org policy can be set at organization, folder and project level. Use `--effective` to see what applies.
- Cloud Armor attaches to backend services behind a global or regional external load balancer, so check the load balancer type before proposing a policy.
