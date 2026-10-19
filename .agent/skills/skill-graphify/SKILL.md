---
name: skill-graphify
description: Lifecycle manager, knowledge graph generator, and topological dependency visualizer using Graphify (Graphify-Labs/graphify). Supports local AST extraction, LLM semantic inference, interactive D3/Mermaid callflows, and global multi-repo graph linking.
---
# Skill: Graphify Knowledge Graph Engine (`skill-graphify`)

Operational manual and lifecycle manager for **Graphify** ([Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)), integrated with `skill-code-map` for deterministic AST extraction, `ast-grep` rule overlays, and IaC-vs-live drift graphs.

## 0. Auto-Routing Protocol (MANDATORY)

Pick the mode from the request (live cluster/CRD -> Live K8s row; drift -> IaC-vs-Live; code topology -> Local AST; cross-modal docs -> Deep Semantic). Ask only if the target or scope is ambiguous. Every readout MUST state its **Evidence Boundary** (static AST, manifests only, or live cluster state):

| Mode / Engine | Use for | Entry points |
|---|---|---|
| **Local AST (`--code-only` / `graph_builder.py --format graphify`)** | Fast, zero-API-key symbol/call/import graph and God-node detection | `graphify extract <dir> --code-only`, `graph_builder.py <dir> --format graphify` |
| **Deep Semantic (`--mode deep`)** | Cross-modal inference across code, Markdown docs, PDFs, and SQL schemas via LLM | `graphify extract <dir> --mode deep` |
| **Live K8s + CRD + Code Bridge** | Dynamic cluster/CRD topology, secret-redacted graph, YAML `manifest-of` bridging, and `ast-grep` rule overlays | `k8s_graphify_extract.py`, `k8s_catalog.py --format graphify` |
| **IaC-vs-Live Drift Graph** | Visualizing `drifted`, `missing`, `unmanaged` K8s/Vault resources and `cross_check` bindings | `state_graph.py report ... --format graphify` |

### Safety & Runtime Caveats

- `k8s_graphify_extract.py` never lists `secrets`, `configmaps`, or `tokenreviews` during dynamic `api-resources` discovery, strips sensitive keys/env literals, and writes output atomically at `0600` via `write_graph_atomic` (raises `SecretLeakError` if any secret-shaped token survives).
- Any `kubectl` context matching `*prod*` is refused unless `--allow-prod-read` is passed. Use `--live-k8s <snapshot.json>` for air-gapped/offline extraction.
- `skill-code-map`'s `auto_context.py` and `semantic_query.py` natively accept Graphify `graph.json` and `unified-graph.json` files without conversion.

---

## 1. Engine Installation & Lifecycle

Graphify is packaged on PyPI as `graphifyy` and provides `graphify` and `graphify-mcp` binaries:

```bash
# Recommended installation via uv (isolated tool)
uv tool install graphifyy

# Verification
graphify --version

# Update to latest release
uv tool upgrade graphifyy

# Agent integration hooks (optional)
graphify antigravity install   # Writes Antigravity agent workflows
graphify gemini install        # Writes Gemini CLI hook
```

---

## 2. Core Workflows

### Workflow A: Local AST Extraction (Zero API Key / Fast Mode)
Indexes all code symbols, calls, and relationships using local tree-sitter without third-party LLM calls:

```bash
# Code-only extraction (writes <target>/graphify-out/graph.json)
graphify extract <target_directory> --code-only

# Or deterministic language-resolved AST extraction via skill-code-map
/usr/bin/python3 .agent/skills/skill-code-map/scripts/graph_builder.py <target_directory> \
  --format graphify --output <target_directory>/graphify-out/graph.json
```

### Workflow B: Full Semantic & Inferential Extraction (LLM-Augmented)
Performs deep inference across code, docs, schemas, and diagrams using an LLM backend (Gemini, Claude, OpenAI, Ollama):

```bash
# Uses GEMINI_API_KEY / default provider
graphify extract <target_directory> --mode deep

# Using local Ollama / vLLM
graphify extract <target_directory> --backend ollama --model qwen2.5-coder
```

### Workflow C: Visual & Topological Export
Generates interactive HTML diagrams and architectural reports:

```bash
# 1. Generate interactive D3 knowledge graph
graphify export html --graph <target>/graphify-out/graph.json

# 2. Generate Mermaid-based architecture call-flow HTML
graphify export callflow-html --graph <target>/graphify-out/graph.json

# 3. Generate D3 collapsible tree view
graphify tree --graph <target>/graphify-out/graph.json --output <target>/graphify-out/GRAPH_TREE.html
```

### Workflow D: Global Multi-Repo Knowledge Base
Combines disparate repositories into a centralized global knowledge graph (`~/.graphify/global-graph.json`):

```bash
# Add repository graph to global hub
graphify global add <target>/graphify-out/graph.json --as my-project

# List all indexed repositories in the global graph
graphify global list
```

---

### Workflow E: Live Kubernetes, CRD, Manifest & AST-Rule Unified Graph
Extracts live cluster state, dynamically discovers CRDs (Crossplane, Postgres Operator, ArgoCD, custom XRDs), bridges repo YAML manifests (`--manifests`), overlays `skill-code-map` `ast-grep` rule records (`--extract-rules`), and writes atomically at `0600` with zero secret leakage:

```bash
# 1. Extract live Kubernetes topology (or pass --live-k8s snapshot.json for offline mode)
/usr/bin/python3 .agent/skills/skill-graphify/scripts/k8s_graphify_extract.py \
  --namespace cloud-boot-app \
  --out projects/cloud-boot-app/graphify-out/k8s-graph.json

# 2. Merge live K8s topology with code AST graph, bridge YAML manifests, and enrich with ast-grep rules
/usr/bin/python3 .agent/skills/skill-graphify/scripts/k8s_graphify_extract.py \
  --namespace cloud-boot-app \
  --merge-with projects/cloud-boot-app/graphify-out/graph.json \
  --manifests projects/cloud-boot-app/k8s projects/cloud-boot-app/crossplane \
  --extract-rules projects/cloud-boot-app \
  --out projects/cloud-boot-app/graphify-out/unified-graph.json

# 3. Query cluster & code relationships with Graphify CLI or skill-code-map tools
graphify explain "k8s:apps/Deployment/cloud-boot-app/cloud-boot-app-workload" \
  --graph projects/cloud-boot-app/graphify-out/unified-graph.json --all

/usr/bin/python3 .agent/skills/skill-code-map/scripts/auto_context.py \
  "update DataController and Service routing" \
  --graph projects/cloud-boot-app/graphify-out/unified-graph.json
```

---

## 3. Comparison: `graphify` vs. `skill-code-map` (`ast-grep` + `tree-sitter`)

| Capability | `skill-graphify` | `skill-code-map` |
| :--- | :--- | :--- |
| **Primary Purpose** | **Macro Architecture, Visual D3/Mermaid Export & Multi-Repo Graph** | **Deterministic AST Symbol Mapping, `ast-grep` Rules, Task Lensing & IaC Drift** |
| **Granularity** | Graph-level: nodes, typed links, community clusters, God Nodes | Symbol & statement level: receiver-resolved calls, AST rules, declaration surgery |
| **Schema Interop** | Standard NetworkX `node_link_data` (`nodes` list, `links` list) | Emits/ingests both CodeMap and Graphify schemas (`--format graphify`) |
| **Mutation / Refactor** | Read-only graph extraction & HTML visualization | AST node replacement (`semantic_edit.py`) and `ast-grep --rewrite` |
| **Doc / Schema Ingestion** | Ingests Markdown, PDF, SQL, and database schemas (`--mode deep`) | Code ASTs, K8s/Crossplane/Helm YAML, Terraform HCL, Vault `api_paths` |

### Best-Practice Pairing
1. **Use `skill-graphify` + `graph_builder.py --format graphify`** to map high-level system & cluster topology, visualize drift communities, and identify God Nodes.
2. **Use `auto_context.py` + `semantic_query.py`** on the unified graph to rank task-relevant files and compute transitive blast radius.
3. **Use `local_extract.py` (`ast-grep`) + `semantic_edit.py`** to inspect method internals, enrich graph nodes with rule findings, and execute surgical code edits.

