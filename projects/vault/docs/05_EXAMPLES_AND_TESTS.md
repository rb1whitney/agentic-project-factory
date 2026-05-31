# Examples & Operations

## Pragmatic Migration Strategies

Transitioning a running enterprise cluster away from stateful HCL frameworks toward a stateless data-driven model requires careful execution. You cannot change mechanisms overnight without risking major disruptions.

### The Phased Migration Playbook

**Phase 1: Shadow Reconciliation (Read-Only Drift Auditing)**
Introduce the Python suite into your pipeline in audit-only mode. Have it fetch the live state and log the computed JSON diff without issuing PUT or POST mutations. Validate that your Python logic interprets the active setup correctly.

**Phase 2: Target Sub-path Decoupling**
Carve out specific paths (e.g., application namespaces under `kv-v2/teams/*`) and remove them from the primary Terraform configuration files. Use Terraform's `terraform state rm` command to detach those resources cleanly from the state file without triggering deletion calls on the active cluster nodes.

**Phase 3: Shift Ownership to Schemas**
Pass management of those decoupled namespaces over to the `vault_blueprint.json` structure, allowing developers to self-serve configuration requests quickly through validated schema updates.

```
+------------------------------------------------------------------------+
|                     Strategic Migration Matrix                         |
|                                                                        |
|  [Phase 1: Shadow Audit]  --> [Phase 2: State Carve-Out] --> [Phase 3] |
|    - Compare live vs JSON       - Run `state rm` on paths      - Full  |
|    - Zero mutation impact       - Unlink from HCL configs      - Delta |
+------------------------------------------------------------------------+
```

---

## Emergency Backups & Post-Mortem Strategy

Operating a decoupled, dynamically generated secret storage state requires high-frequency resilience mechanisms. If a cluster experiences structural failure, restoring the control plane correctly is critical.

### The Execution Strategy
Automated jobs should securely export and encrypt the underlying storage mechanism snapshots. From an infrastructure automation perspective, the automation scripts should never attempt to parse or mutate the raw cluster backup binary blob.

**Restoration Posture:**
During a post-mortem recovery event, standard JSON schema ingestion must be disabled until the foundational keyring and state backups have been forcibly pushed back into the newly provisioned instances.

```bash
# Emergency Restoration Scenario
# Assumes unsealed status and active root/administrative token presence

# 1. Halt regular declarative GitHub Action pipelines manually
# 2. Re-establish raw storage blob baseline using the dedicated API 
vault operator raft snapshot restore ./backup.snap

# 3. Once unsealed and active, resume the declarative pipeline to repair configuration drift
python3 bin/cluster_secret_data.py --name prod-us --path ./config/admin
```

> **Warning:** Do not attempt to run `cluster_secret_data.py` operations while a raft snapshot restore is executing. This creates split-brain contention within the API server.
