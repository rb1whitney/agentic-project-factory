# User Workflows

## Threat Modeling & Security Analysis

When shifting automation from a vendor-backed binary framework to standard Python code running in a CI pipeline, platform engineers must build a rigorous threat model targeting the new execution pathway.

### Architectural Vulnerability Matrices

```
               [ Attack Vector: CI Runner Compromise ]
                                 │
         ┌───────────────────────┴───────────────────────┐
         ▼                                               ▼
[ Blast Radius: Monolithic IaC ]              [ Blast Radius: Custom Python Engine ]
  - Global privileged root token                - Locally scoped, path-constrained token
  - Can unmount auth/root engines               - System core paths explicitly blacklisted
  - Complete cluster takeover risk              - Blast radius restricted to app namespace
```

### 1. Attack Vector: Compromised Automation Tokens (Confused Deputy Vulnerability)
**The Risk**: The automation system requires an active token to query and mutate endpoints. If an attacker gains control of the CI/CD pipeline executing this script, they could modify the script's code to extract secrets or elevate privileges across the entire system.

**Mitigation Strategy**: Do not use root tokens in production workflows. Instead, configure the automation engine to authenticate via an engineered AppRole or JWT/OIDC pipeline linked directly to the repository's identity.

**Token Policy Boundary**: The automation runner should map to a dedicated policy that restricts changes to explicit, non-root paths. Below is the minimum policy required for day-2 runner orchestration:

```hcl
# Restrict backend modifications to non-system paths
path "sys/mounts/*" {
  capabilities = ["create", "read", "update", "list"]
}

# Deny direct access to modify system core backend operations
path "sys/mounts/auth" {
  capabilities = ["deny"]
}

# Allow full ACL policy management for designated paths
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
```

### 2. Attack Vector: Parameter Injection and Structural Policy Bypass
**The Risk**: A user adds unsafe parameters or malicious rules into a policy schema (e.g., creating a wild-card policy block `path "kv-v2/*" { capabilities = ["sudo"] }`). If the automation engine updates Vault without filtering this input, it creates an escalation pathway.

**Mitigation Strategy**: Implement strict schema validation inside `lib/validator_helper.py`. Use regex pattern verification on policy strings to block administrative capabilities like `sudo` or root-level pathways (`sys/auth`, `sys/crypto`) before they are passed to the VaultClient.

---

## Defensive Error Handling & Fault Isolation

**The Blast Radius Principle**
A failed deployment script must fail closed and fail explicitly. Silent errors in an orchestration script lead to "zombie" infrastructure—a configuration assumed to be live, but missing in production.

**Strict HTTP Timeouts**
If Vault enters an election cycle or TCP exhaustion, the `urllib` engine can block a CI runner indefinitely. The integration enforces strict `timeout=10` boundaries on all HTTP transit paths, instantly terminating the pipeline and triggering alarms rather than silently hanging.

**Payload Interception**
Catching structural issues *before* they are sent to the network layer prevents partial state corruption. By loading payloads strictly via `json.load()` and trapping `json.JSONDecodeError`, malformed schema changes immediately raise structural faults. The cluster is never touched with broken input.
