# AWS Storage and Databases: Read the Signals

**Read when**: reviewing S3 buckets or RDS/Aurora instances for exposure, durability, or cost. Orient with the `aws-cloud-architecture-audit` contract probes (account public-access block, RDS summary); this page interprets results. All changes are propose-only.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| `get-public-access-block` fails with `NoSuchPublicAccessBlockConfiguration` | `aws s3control get-public-access-block --account-id <id>` | Account-level block is absent. Propose enabling all four settings after checking for intentionally public buckets. |
| A bucket has no bucket-level block | `aws s3api get-public-access-block --bucket <b>`; `aws s3api get-bucket-policy-status --bucket <b>` | `IsPublic` true: list who relies on it before proposing a block. |
| Bucket has no lifecycle rule and holds growing data | `aws s3api get-bucket-lifecycle-configuration --bucket <b>` | Check object size and age first, then propose transitions or expiry (see gotchas). |
| Versioning off on a bucket holding irreplaceable data | `aws s3api get-bucket-versioning --bucket <b>` | Propose versioning plus a noncurrent-version expiry rule so cost stays bounded. |
| RDS instance `MultiAZ` false in production | `aws rds describe-db-instances --db-instance-identifier <id>` | Propose Multi-AZ. Report the cost increase and that the change can cause a brief failover. |
| `BackupRetentionPeriod` is 0 | same probe | Automated backups and point-in-time recovery are off. Propose a retention period. |
| `StorageEncrypted` false | same probe | Encryption cannot be turned on in place. Propose snapshot, encrypted copy, restore, and cutover as a planned change. |
| `PubliclyAccessible` true | `aws ec2 describe-security-groups --group-ids <sg>` | Check the security group sources before proposing to make it private. |

## Gotchas
- Do not assume a default for bucket encryption or public access from memory; read the live configuration.
- MFA Delete can only be enabled by the bucket owner's root credentials through the CLI or API, so it is rarely practical. Versioning plus a restricted delete permission is the usual substitute.
- Infrequent-access and archive storage classes charge for small objects and minimum storage duration. Measure the object-size distribution before adding a transition rule, or it can cost more.
- A lifecycle rule applies prospectively and by prefix or tag filter. Confirm the filter on a copy of the rule before widening it.
- Reserved capacity and Savings Plans commit spend for a term. Use `aws ce get-reservation-purchase-recommendation` or Cost Explorer to propose, never to purchase.
