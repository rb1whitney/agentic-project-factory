---
name: skill-code-map
description: Deterministic multi-language AST structural extractor, code mapper, and ast-grep rules engine across Java, Go, Python, Kubernetes, Crossplane, Terraform, and Vault, plus read-only IaC-vs-live drift for Kubernetes and Vault.
---
# Skill: Code Map (`skill-code-map`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: ast-blast-radius-gate] parent=skill-code-map required_inputs=['target_dir', 'task_query']
/usr/bin/python3 .agent/skills/skill-code-map/scripts/auto_context.py "{task_query}" --src {target_dir} --max-tokens 8000 | bin/rtk
/usr/bin/python3 .agent/skills/skill-code-map/scripts/semantic_query.py query --src {target_dir} | bin/rtk
git log --stat -n 20 -- {target_dir} | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_code_map_workflow(target_dir, task_query):
  1. PRE-CHECK: Run with /usr/bin/python3 (system python with tree_sitter); Scope target_dir to subsystem
  2. result <- invoke(ast-blast-radius-gate, {target_dir: "<target_dir>", task_query: "<task_query>"})
  3. POST-CHECK: Context window restricted to AST blast radius; Evidence Boundary stated
  4. RETURN {Location, Problem, Fix, outputs: ['ranked_context', 'relationship_graph', 'evidence_boundary']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: ast-blast-radius-gate`**
  - `trigger`: Extract AST symbol map, call/import graph, git forensics hotspots, and PPR blast-radius context for source code directory
  - `inputs`: required `['target_dir', 'task_query']`, optional `['max_tokens', 'format']`
  - `outputs`: `['ranked_context', 'relationship_graph', 'evidence_boundary']`
  - `preconditions`: Run with /usr/bin/python3 (system python with tree_sitter); Scope target_dir to subsystem
  - `postconditions`: Context window restricted to AST blast radius; Evidence Boundary stated
  - `side_effects`: filesystem=writes cache to ~/.cache/skill-code-map/, network=none
<!-- SAP_BUNDLE_END -->

## 0. Auto-Routing + Map-First Protocol (MANDATORY)

Extract AST symbol map, call/import graph (`relationship_graph`), git forensics hotspots, and PPR blast-radius context (`ranked_context`, `evidence_boundary`) for source code directory `target_dir` and `task_query` (`max_tokens`, `format`). Pick the engine from the request; ask only when `target_dir` or scope is ambiguous:

| Engine | Use for | Entry points |
| :--- | :--- | :--- |
| **Python code mapper** (`tree-sitter`) | Symbol inventory, `code_map.md`, package/module import graph, inheritance, PPR `auto_context` ranking | `code_mapper.py`, `graph_builder.py`, `auto_context.py`, `semantic_query.py` |
| **ast-grep** (rules & policies) | Structural patterns, 6-Pillar Well-Architected audits (`SEC`/`REL`/`OPS`/`PERF`/`COST`/`SUS`), Policy-as-Code hydration | `local_extract.py`, `well_architected_audit.py`, `hydrate_policies.py`, `ast-grep run -p ...` |
| **State graph** (IaC vs live) | Desired-vs-live drift, Vault posture lint, cluster health, environment diffs | `state_graph.py`, `k8s_catalog.py` |
| **Graphify bridge** (`skill-graphify`) | Interactive D3/Mermaid callflow HTML, community/God-node topology, unified code+K8s+Vault graph | `--format graphify` on `graph_builder.py` / `k8s_catalog.py` / `state_graph.py`, plus `k8s_graphify_extract.py` |

### Routing & Runtime Rules
- **Map First**: Build or reuse the graph (`~/.cache/skill-code-map/<repo-hash>/`), then query it; never read raw files to answer a dependency or blast-radius question.
- **Interpreter**: Always run Python AST scripts with `/usr/bin/python3` (system Python with `tree_sitter` bindings) and pipe shell output through `bin/rtk`.
- **Evidence Boundary**: Every readout MUST end with an **Evidence Boundary** line stating static AST vs manifests only vs live cluster state.
- **Language & Grammar Caveats**: Go graph tracks package-level imports, exported funcs/methods, and Cobra `AddCommand` edges (use `ast-grep` for general call sites); YAML Helm templates must be rendered before `state_graph.py`; `state_graph.py` refuses `*prod*` kubectl contexts unless `--allow-prod-read` is passed and strips all Secret/ConfigMap payloads.

## 1. Core Execution Workflows

### Workflow A: Blast Radius Lensing, Symbol Indexing & Semantic Queries
```bash
SC=.agent/skills/skill-code-map/scripts
/usr/bin/python3 $SC/code_mapper.py <target_dir> | bin/rtk
/usr/bin/python3 $SC/graph_builder.py <target_dir> --format graphify --output graph.json | bin/rtk
/usr/bin/python3 $SC/auto_context.py "<task_query>" --src <target_dir> --max-tokens 8000 | bin/rtk
/usr/bin/python3 $SC/semantic_query.py --graph graph.json query <symbol> | bin/rtk
/usr/bin/python3 $SC/semantic_query.py --graph graph.json lineage <Kind/name> --depth 2 --mermaid | bin/rtk
/usr/bin/python3 $SC/semantic_query.py --graph graph.json impact <symbol> | bin/rtk
/usr/bin/python3 $SC/semantic_edit.py <file> method <Class.method> '<replacement>' --dry-run | bin/rtk
```

### Workflow B: 6-Pillar Audit & Multi-Domain Structural Extraction (`ast-grep`)
```bash
SC=.agent/skills/skill-code-map/scripts
/usr/bin/python3 $SC/well_architected_audit.py <target_dir> --pillar ALL | bin/rtk
/usr/bin/python3 $SC/local_extract.py <target_dir> | bin/rtk
ast-grep run -l yaml -p 'kind: CompositeResourceDefinition' <target_dir> | bin/rtk
ast-grep run -l hcl --kind block <target_dir> | bin/rtk
```

### Workflow C: IaC vs Live State & Environment Drift (`state_graph.py`)
```bash
SG=.agent/skills/skill-code-map/scripts/state_graph.py
/usr/bin/python3 $SG lint --vault <vault_config_dir> | bin/rtk
/usr/bin/python3 $SG report --k8s <manifest_dirs> --vault <vault_config_dir> --no-live-vault --format graphify | bin/rtk
/usr/bin/python3 $SG env-diff dev prod --root <target_dir> | bin/rtk
```

## 2. Reference & Script Routing Index

| Capability / Need | Trigger / Scope | Reference Runbooks, Configs & Scripts (`.agent/skills/skill-code-map/`) |
| :--- | :--- | :--- |
| **PPR Context Lensing & Recon** | Blast radius ranking, git churn/hotspot forensics, token budgeting | `scripts/auto_context.py`, `references/codebase-recon.md`, `references/context-master.md` |
| **AST Symbol Map & Dependency Graph** | Tree-sitter symbol extraction (`code_map.md`) & import/call graphs | `scripts/code_mapper.py`, `scripts/graph_builder.py`, `scripts/search_map.py`, `scripts/read_code_map.py` |
| **Semantic Lineage, Impact & Surgery** | Cross-file symbol usage, Mermaid lineage, AST node replacement | `scripts/semantic_query.py`, `scripts/semantic_edit.py`, `scripts/codemap_graphify_mcp.py` |
| **6-Pillar Well-Architected & Policy Engine** | Static `SEC`/`REL`/`OPS`/`PERF`/`COST`/`SUS` audit & Kodus policy hydration | `scripts/well_architected_audit.py`, `scripts/local_extract.py`, `scripts/hydrate_policies.py`, `scripts/sgconfig.yml`, `scripts/rules/`, `resources/RULE_AUTHORING_GUIDE.md` |
| **IaC Drift, Vault Lint & K8s Catalog** | Desired-vs-live K8s/Vault drift, OpenAPI/CRD catalog, env-diff | `scripts/state_graph.py`, `scripts/k8s_catalog.py`, `scripts/k8s_graphify_extract.py` |
