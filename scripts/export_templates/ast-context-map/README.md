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
