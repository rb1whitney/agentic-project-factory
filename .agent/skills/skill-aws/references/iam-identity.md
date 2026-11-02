# AWS Identity: Read the Signals

**Read when**: reviewing who can do what in an AWS account, or before any change to roles, access keys, or SCPs. Run the Orient probes from the `aws-cloud-architecture-audit` contract first (identity, account summary, analyzers); this page interprets what they return. All actions below are propose-only.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| `RootKeys` = 1 or `RootMFA` = 0 in the account summary | `aws iam get-account-summary` again after the owner confirms | Report as a finding. Do not delete a root key without the account owner. |
| An IAM user has `password_enabled` true in the credential report | `aws sso-admin list-instances` | Instance exists: propose moving the person to Identity Center. None: report SSO is not configured and stop. |
| Access key is old and `last_used_date` is recent | `aws iam get-access-key-last-used --access-key-id <id>` (service and region) | Name the workload from service and region, then propose a role to replace the key. |
| Access key never used | same probe returns no `LastUsedDate` | Propose `aws iam update-access-key --status Inactive`. Deactivation is reversible; deletion is not. |
| No analyzer of type `ACCOUNT_UNUSED_ACCESS` | `aws accessanalyzer list-analyzers` | Report that nobody is watching for unused permissions. List findings only if an analyzer exists. |
| `aws organizations` call is denied | `aws sts get-caller-identity` (which account am I in?) | Member account: SCPs are inherited and not visible here. Ask for the management-account view. |
| Role trusts `"Principal": "*"` or another account without conditions | `aws iam get-role --role-name <r> --query 'Role.AssumeRolePolicyDocument'` | Propose an `sts:ExternalId` or `aws:PrincipalOrgID` condition. |
| Access is denied although the identity policy allows it | `aws iam simulate-principal-policy --policy-source-arn <arn> --action-names <a> --resource-arns <r>` | `implicitDeny`: add the permission. `explicitDeny`: find the deny (see gotchas). |

## Gotchas
- `generate-credential-report` returns before the report exists. Retry `get-credential-report` until it succeeds. A report younger than four hours is reused, so a fresh change may not show yet.
- An explicit deny anywhere beats every allow: SCP, permissions boundary, session policy, or resource policy. The simulator does not model every one of these; the CloudTrail error message usually names the policy type that denied.
- A cross-account request needs an allow on both sides: the caller's identity policy and the resource's policy.
- Look up action and condition-key names in the [Service Authorization Reference](https://docs.aws.amazon.com/service-authorization/latest/reference/reference.html) before writing a policy. Do not recall them.
