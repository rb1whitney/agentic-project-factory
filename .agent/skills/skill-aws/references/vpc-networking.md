# AWS Networking: Read the Signals

**Read when**: judging VPC exposure, tracing why a connection fails, or checking hybrid and cross-cloud connectivity. Orient with the `aws-cloud-architecture-audit` contract probes (flow logs, open security groups); this page interprets results. All changes are propose-only.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| A database or app subnet shares a route table with an `igw-` route | `aws ec2 describe-route-tables --query "RouteTables[?Routes[?starts_with(GatewayId,'igw-')]].[RouteTableId,Associations[].SubnetId]"` | The subnet is public regardless of its name. Propose a private route table and a NAT or endpoint path. |
| Security group allows `0.0.0.0/0` on a port other than 80/443 | `aws ec2 describe-security-groups --filters Name=ip-permission.cidr,Values=0.0.0.0/0` | Propose a source security group or narrower CIDR. Name what depends on it first (`describe-network-interfaces` filtered by group). |
| No flow logs on a VPC | `aws ec2 describe-flow-logs` | Propose enabling them to S3 or CloudWatch. Report the log cost as a trade-off. |
| High NAT traffic to S3 or DynamoDB | `aws ec2 describe-vpc-endpoints`, `aws ec2 describe-nat-gateways` | No gateway endpoint: propose one. Gateway endpoints for S3 and DynamoDB are not charged. |
| ALB target unhealthy | `aws elbv2 describe-target-health --target-group-arn <arn>` | Read `Reason`: `Target.Timeout` (security group or port), `Target.ResponseCodeMismatch` (health-check path or matcher), `Target.FailedHealthChecks` (app not ready). |
| VPN tunnel not `UP` | `aws ec2 describe-vpn-connections --query 'VpnConnections[].[VpnConnectionId,VgwTelemetry[].Status]'` | Down: check the customer gateway side and BGP before touching AWS config. |
| Transit Gateway traffic dropped | `aws ec2 describe-transit-gateway-attachments`, `aws ec2 search-transit-gateway-routes --transit-gateway-route-table-id <id> --filters Name=state,Values=active` | Missing route or attachment not associated to the route table: propose the association or route. |
| PrivateLink or private-zone name does not resolve | `dig +short <name>` from a host in the VPC; `aws ec2 describe-vpc-endpoints --query 'VpcEndpoints[].[VpcEndpointId,PrivateDnsEnabled]'` | See the DNS gotchas below before changing anything. |

## Gotchas
- A subnet is public because its route table has an internet-gateway route, not because of its name or `MapPublicIpOnLaunch`.
- Security groups are stateful. Network ACLs are stateless and need explicit return-traffic (ephemeral port) rules.
- Private DNS for an interface endpoint resolves only where the VPC has both DNS support and DNS hostnames enabled.
- Cross-cloud (GCP to AWS PrivateLink): the Google private DNS zone must list the peered network under `private_visibility_config`, or names resolve only on the VPN-attached network. Confirm with `dig` from a VM in each network.
- Reachability Analyzer (`aws ec2 create-network-insights-path`, `start-network-insights-analysis`) creates resources and costs per analysis. Propose it; do not run it unasked.
- Whitelisting requests: record why, the exact CIDR, and the review ticket before changing a security group or firewall rule.
