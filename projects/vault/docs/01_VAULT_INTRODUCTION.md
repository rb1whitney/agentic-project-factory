# Vault Introduction

## The Catalyst

**What's New**
Platform teams are shifting from stateful Infrastructure as Code (IaC) like Terraform to stateless, data-driven schema definitions for Day-2 HashiCorp Vault management.

**Why It Matters**
Traditional stateful HCL models create operational bottlenecks at scale. Teams face a tough choice: accept state-locking gridlock and a massive blast radius by giving developers direct access, or turn the platform team into a human ticketing queue for basic pull requests.

---

## The Chronological Failure of Stateful Secret Management

### The Evolution of Vault Ops

**Phase 1: Manual/CLI**
Raw curl and CLI commands. Highly dynamic but prone to human error, untracked drift, and outages.

**Phase 2: Terraform State**
Introduces order for Day-1 bootstrapping, but hits a wall on Day-2 operations. Result: state-locking gridlock, overly privileged CI runners, and slow plan/apply refresh times.

**Phase 3: Custom Wrappers**
Teams write complex scripts to template HCL. This creates debugging hell and breaks the single-responsibility principle.

**Phase 4: Stateless Automation**
Embraces data-driven JSON/YAML definitions executed via idempotent engines. The cluster is the state, queried in real time.

---

## Architectural Blueprint & Trade-Off Matrix

**The Big Picture**
The automation engine sits between Git and the Vault REST API. Configurations are declared as schema-validated JSON/YAML. On a pull request, a stateless Python engine fetches live state, calculates the delta in-memory, and executes targeted HTTP mutations.

### The Core Trade-offs

- **State Dependencies**: Terraform requires remote backends (S3/Consul) and locking; Python automation is zero-state (Vault is the source of truth).
- **Blast Radius**: Terraform puts the entire cluster or state graph at risk; Python scales down to isolated, path-specific execution.
- **Execution Speed**: Terraform is slow due to full-graph evaluation; Python is fast, processing only the specific file changes.
- **Ecosystem Support**: Terraform updates are vendor-maintained; Python requires manual schema updates for new upstream API parameters.

---

## Ecosystem Evaluation Matrix

| Tooling Variant | Core Limitations | Operational Complexity | Performance | Best Suited For |
| :--- | :--- | :--- | :--- | :--- |
| **Official Terraform Provider** | Upstream version locking; HCL templating limitations; state bloat. | High day-2 overhead; prone to runner state locks. | Slow due to sequential API status checking. | Day-1 infrastructure bootstrapping; small, static environments. |
| **Custom Python Engine** | Manual schema updates required for brand-new upstream API parameters. | Low operational footprint; native modules only. | Fast; targeted in-memory deltas and API calls. | Multi-tenant platforms; rapid developer self-service. |
| **Vault Operator (K8s Native)** | Restricted to K8s; introduces custom resource definition overhead. | Medium; dependent on operator controller loops. | Bound by Kubernetes API machinery loops. | Workloads operating exclusively inside Kubernetes. |

### Summary & Next Steps

For static environments with under 50 mount points run by a small operations team, standard stateful IaC remains sufficient.

For large, dynamic, multi-tenant clusters experiencing pipeline gridlock and demanding self-service access, moving to stateless data automation offers faster loops, lowered maintenance, and tighter blast radiuses.

**Navigation References**
- **Platform Operators**: Review `02_ADMIN_GUIDE.md` to learn how to manage access control boundaries and integrate this suite into active GitHub Actions pipelines.
- **Application Teams**: Review `03_USER_WORKFLOWS.md` for concrete patterns on requesting new KV paths or Transit keys via declarative JSON files.
- **Automation Engineers**: Review `04_DEVELOPER_GUIDE.md` for step-by-step instructions on extending schemas to support database roles and dynamic certificate engines.
