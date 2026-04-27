# GCP Reference: System Design & Resource Hierarchy

Following the Google Cloud Architecture Framework.

## 1. Resource Hierarchy Best Practices
- **Organization**: The root node for all resources. Ensures centralized billing and policy enforcement.
- **Folders**: Used to group projects by department, environment (dev/prod), or product.
- **Projects**: The trust boundary. Resources in different projects are isolated by default.

### Key Decisions
- **Project Per Environment**: Creates a hard security boundary between production and non-production workloads.
- **Shared VPC Project**: Centralizes networking in a dedicated project to reduce complexity and improve security.

## 2. Global vs. Regional Resources
- **Global**: IAM, VPCs, Firewalls, Cloud DNS, Global Load Balancing.
- **Regional**: Subnets, GCE Instances, GKE Clusters, Regional Load Balancing.
- **Zonal**: GCE Instances (within a region), Filestore.

## 3. High Availability (HA) Design
- **Multi-Zonal**: Deploying resources across at least 3 zones in a region.
- **Multi-Regional**: Using global load balancing to route traffic between regions for extreme resilience.

## 4. Resource Tagging & Labeling
- **Labels**: Used for billing and filtering. Example: `env=prod`, `team=data`.
- **Tags**: Used for networking and firewall rules.