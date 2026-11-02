---
name: skill-graphify
description: Lifecycle manager, knowledge graph generator, and topological dependency visualizer using Graphify (Graphify-Labs/graphify). Supports local AST extraction, LLM semantic inference, interactive D3/Mermaid callflows, and global multi-repo graph linking.
---
# Skill: Graphify Knowledge Graph Engine (`skill-graphify`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: k8s-graphify-topology] parent=skill-graphify required_inputs=['target_dir', 'namespace']
/usr/bin/python3 .agent/skills/skill-graphify/scripts/k8s_graphify_extract.py -n {namespace} --manifests {target_dir} | bin/rtk
/usr/bin/python3 .agent/skills/skill-code-map/scripts/semantic_query.py lineage {namespace} --src {target_dir} --mermaid | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_graphify_workflow(target_dir, namespace):
  1. PRE-CHECK: Secret/ConfigMap redaction active (NEVER_LIST enforced); Non-prod context verified
  2. result <- invoke(k8s-graphify-topology, {target_dir: "<target_dir>", namespace: "<namespace>"})
  3. POST-CHECK: 0600 atomic leak-checked graph emitted
  4. RETURN {Location, Problem, Fix, outputs: ['graph_json', 'lineage_mermaid', 'evidence_boundary']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: k8s-graphify-topology`**
  - `trigger`: Extract Kubernetes, Crossplane XRD/Composition, and code topology into Graphify knowledge graph
  - `inputs`: required `['target_dir', 'namespace']`, optional `['manifests_dir']`
  - `outputs`: `['graph_json', 'lineage_mermaid', 'evidence_boundary']`
  - `preconditions`: Secret/ConfigMap redaction active (NEVER_LIST enforced); Non-prod context verified
  - `postconditions`: 0600 atomic leak-checked graph emitted
  - `side_effects`: filesystem=writes 0600 graph.json, network=read-only K8s API discovery
<!-- SAP_BUNDLE_END -->

## 0. Auto-Routing Protocol (MANDATORY)

Extract Kubernetes, Crossplane XRD/Composition, and code topology for `target_dir`, `manifests_dir`, and `namespace` into a leak-checked Graphify knowledge graph (`graph_json`, `lineage_mermaid`, `evidence_boundary`). Pick the extraction mode from the request and state the **Evidence Boundary** in every readout:

| Mode / Engine | Use for | Entry points |
| :--- | :--- | :--- |
| **Local AST (`--code-only` / `graph_builder.py --format graphify`)** | Fast, zero-API-key symbol/call/import graph, Tarjan SCC cycles, and God-node detection | `graphify extract <target_dir> --code-only`, `graph_builder.py <target_dir> --format graphify` |
| **Deep Semantic (`--mode deep`)** | Cross-modal inference across code, Markdown docs, ADRs, PDFs, and SQL schemas | `graphify extract <target_dir> --mode deep` |
| **Live K8s + CRD + Crossplane Bridge** | Dynamic cluster/CRD topology, secret-redacted `0600` graph, YAML `manifest-of` bridging, and `ast-grep` rule overlays | `k8s_graphify_extract.py`, `k8s_catalog.py --format graphify` |
| **IaC-vs-Live Drift Graph** | Visualizing `drifted`, `missing`, `unmanaged` K8s/Vault resources and `cross_check` bindings | `state_graph.py report ... --format graphify` |

### Safety & Redaction Guarantees
- `k8s_graphify_extract.py` enforces `NEVER_LIST` (`secrets`, `configmaps`, `tokenreviews`), strips sensitive keys/env literals, refuses `*prod*` kubectl contexts unless `--allow-prod-read` is set, and writes output atomically at `0600` via `write_graph_atomic` (raising `SecretLeakError` if any secret-shaped token survives).
- `skill-code-map`'s `auto_context.py` and `semantic_query.py` natively consume Graphify `graph.json` and `unified-graph.json` files without conversion.

## 1. Core Execution Workflows

### Workflow A: Local AST Graph Extraction & Interactive D3/Mermaid Export
```bash
/usr/bin/python3 .agent/skills/skill-graphify/scripts/graph_builder.py <target_dir> \
  --format graphify --output <target_dir>/graphify-out/graph.json | bin/rtk
graphify export html --graph <target_dir>/graphify-out/graph.json | bin/rtk
graphify export callflow-html --graph <target_dir>/graphify-out/graph.json | bin/rtk
```

### Workflow B: Unified Live K8s, Crossplane XRD/Composition & Code Topology
```bash
/usr/bin/python3 .agent/skills/skill-graphify/scripts/k8s_graphify_extract.py \
  --namespace <namespace> \
  --merge-with <target_dir>/graphify-out/graph.json \
  --manifests <target_dir> \
  --extract-rules <target_dir> \
  --out <target_dir>/graphify-out/unified-graph.json | bin/rtk

/usr/bin/python3 .agent/skills/skill-code-map/scripts/semantic_query.py \
  --graph <target_dir>/graphify-out/unified-graph.json lineage <Kind/name> --mermaid | bin/rtk
```

## 2. Reference & Script Routing Index

| Graph Capability | Trigger / Scope | Reference Runbooks & Scripts (`.agent/skills/skill-graphify/`) |
| :--- | :--- | :--- |
| **K8s, CRD & Manifest Graph Extractor** | Secret-redacted live/offline K8s + Crossplane + Terraform bridge (`provisions-k8s`, `manifest-of`) | `scripts/k8s_graphify_extract.py`, `scripts/k8s_catalog.py` |
| **Crossplane v2 & GitOps Control Planes** | XRD (`CompositeResourceDefinition`), Composition, ProviderConfig, and ArgoCD topology patterns | `references/crossplane.md`, `scripts/rules/crossplane/crossplane-xrd.yml`, `scripts/rules/crossplane/crossplane-composition.yml` |
| **AST Graph Builder & Context Lensing** | Multi-language NetworkX `node_link_data` graph generation & PPR context ranking | `scripts/graph_builder.py`, `scripts/auto_context.py`, `scripts/local_extract.py`, `scripts/codemap_graphify_mcp.py`, `scripts/rules/` |
