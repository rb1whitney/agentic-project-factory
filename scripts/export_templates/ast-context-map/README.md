# ast-context-map

Give a coding agent a structural map of a codebase (symbols, calls, dependencies) instead of raw files.

Tree-sitter AST extraction builds a relationship graph. You query the graph (definitions, usages, blast radius, lineage) and hand the agent the answer, not the files. The same graph format also covers Kubernetes, Crossplane, Terraform and Vault topology (Graphify format).

Background: [Stop Dumping Raw Code into LLMs](https://medium.com/@rb1whitney/stop-dumping-raw-code-into-llms-why-semantic-graphs-lead-to-scalable-ai-agents-707c9c3220b0).

## Quickstart

```bash
pip install -r requirements.txt

# 1. Map a directory (writes code_map.md and relationship_graph.json)
python3 scripts/code_mapper.py examples/payments-java --out-dir /tmp/map

# 2. Ask a structural question
python3 scripts/semantic_query.py --graph /tmp/map/relationship_graph.json impact PaymentRequest
```

Output of step 2:

```text
Impact of changing 'PaymentRequest':
- AuditLogger (depth 1, via PaymentRequest)
- PaymentGatewayClient (depth 1, via PaymentRequest)
- PaymentOrchestrator (depth 1, via PaymentRequest)
```

`semantic_query.py` subcommands: `find-definition`, `find-usages`, `trace-dependencies`, `impact`, `query`, `lineage`, `shortest-path`, `diff-impact`.

## Kubernetes and Vault (offline samples)

The same graph tooling checks infrastructure state. Everything below runs offline against synthetic data in `examples/`. No cluster, no Vault server, no tokens.

### Vault configuration lint

The Vault sample uses the `api_paths` YAML format (as used by [vault_controller](https://github.com/rb1whitney/vault_controller)): a top-level `api_paths` list, each item with `api_path`, an optional `api_action`, and an `api_payload`. An optional `_namespace` key scopes a file.

```bash
python3 scripts/state_graph.py lint --vault examples/vault-sample
```

The sample contains one deliberately bad item per rule and clean counterparts. Output (condensed from the JSON):

| Rule | Severity | File | Finding |
| :--- | :--- | :--- | :--- |
| `policy-read-write-mix` | repo-rule | `_acl_policies.yaml` | `payments-admin`: `secret/data/payments/*` mixes read and write |
| `mount-ttl-over-1h` | repo-rule | `_secret_engines.yaml` | `secret`: `default_lease_ttl` 7200s exceeds 1h |
| `plaintext-secret` | repo-rule | `kv/payments-api/credentials.yaml` | key `webhook_token` is not Transit-encrypted |
| `insecure-tls` | advisory | `_auth.yaml` | `auth/ldap/config`: `insecure_tls` true |
| `transit-key-exportable` | advisory | `_secret_engines.yaml` | `transit/keys/payments-key` is exportable |

The clean `payments-reader` policy and the Transit-encrypted `api_key` are not flagged. The test suite asserts this.

### Drift against a snapshot

```bash
python3 scripts/state_graph.py drift --k8s examples/k8s-sample/manifests --live-k8s examples/k8s-sample/live-k8s.json
python3 scripts/state_graph.py drift --vault examples/vault-sample --live-vault examples/vault-sample/live-vault.json
```

| Source | Missing | Drifted | Unmanaged |
| :--- | :--- | :--- | :--- |
| Kubernetes | `Ingress/payments/payments-api` | `Deployment/payments/payments-api`: `spec.replicas` 3 vs 2, image `1.4.0` vs `1.3.9` | `Deployment/payments/legacy-worker` |
| Vault | mount `transit` | policy `payments-admin`: live lacks `delete` | none |

### Topology graph from a snapshot

```bash
python3 scripts/k8s_graphify_extract.py --live-k8s examples/k8s-sample/live-k8s.json \
  --manifests examples/k8s-sample/manifests --out /tmp/k8s-graph.json
```

Prints `Generated Kubernetes knowledge graph: 3 nodes, 1 links.` The graph is Graphify `node_link` JSON.

## Safety rules

- Live Kubernetes extraction never lists `secrets`, `configmaps` or `tokenreviews`.
- A `Secret` object that arrives in an offline snapshot becomes a node (existence only). Its data and any `env` literals are stripped. A test asserts the values do not appear in the output.
- Output is written atomically at mode `0600`. The write is refused if a secret-shaped value survives (`SecretLeakError`).
- `*prod*` kubectl contexts are refused unless `--allow-prod-read` is passed.
- Vault lint and drift are read-only. With `--live-vault` the tool needs no Vault token. It never decrypts Transit ciphertext. Live Vault mode (no snapshot) calls the `vault` CLI with your own token for `list` and `read` only.

## What is in the box

| Path | Purpose |
| :--- | :--- |
| `scripts/code_mapper.py`, `graph_builder.py` | Tree-sitter extraction to `code_map.md` and a relationship graph |
| `scripts/semantic_query.py` | Graph queries: definition, usages, dependencies, impact, lineage, diff-impact |
| `scripts/auto_context.py` | Rank files for a task description within a token budget |
| `scripts/well_architected_audit.py`, `rules/`, `resources/` | ast-grep rule packs and a six-pillar structural audit |
| `scripts/state_graph.py` | Infrastructure-as-code vs live Kubernetes/Vault drift graph |
| `scripts/k8s_graphify_extract.py`, `k8s_catalog.py` | Secret-redacted Kubernetes/Crossplane/Terraform topology graph |
| `scripts/graph_registry.py` | Publish a graph per commit and query it without a checkout |
| `SKILL.md`, `skills/graphify/SKILL.md` | Agent Skill docs for the two entry points |

## Measured

Reproduce with `python3 benchmarks/token_compare.py`. The sample is a small synthetic Java service (5 classes) in `examples/payments-java`. "~tokens" is bytes / 4, a rough proxy, not a tokenizer.

| Scenario | Raw bytes | AST bytes | Saved |
| :--- | ---: | ---: | ---: |
| Whole repo: raw source vs `code_map.md` | 9668 | 3678 | 62.0% |
| Blast radius of `PaymentRequest`: files mentioning it vs `impact` query | 7914 | 186 | 97.6% |

Read this carefully: a whole-repo map saves a moderate amount on small, comment-light code. The large savings come from targeted queries that return only the answer. Results on a real repository depend on its size and density; measure on yours.

## Limitations

- Tree-sitter is syntactic. Call edges are resolved from names and declared types, not by a compiler. Reflection, dynamic dispatch and generated code are not captured.
- The rule-pack tests and `local_extract.py` need the `ast-grep` binary (installed by `requirements.txt` as `ast-grep-cli`).
- Dependencies are pinned to `tree-sitter==0.20.1` and `tree-sitter-languages==1.10.2`. CI runs Python 3.10 and 3.11.
- The benchmark is one small synthetic sample, not a statistical study.
- The Kubernetes and Vault extractors need cluster access. They are read-only, never list secrets or configmaps, strip sensitive values, and refuse `*prod*` contexts unless `--allow-prod-read` is set. Use a non-production context.

## Tests

```bash
python3 -m pytest -q
```

## Provenance

This repository is generated from [Agentic-Project-Factory](https://github.com/rb1whitney/Agentic-Project-Factory) by `scripts/export_ast_context_map.py`. File issues here; code changes land upstream and are re-exported.

License: Apache-2.0.
