---
name: skill-code-map
description: Deterministic multi-language AST structural extractor, code mapper, and ast-grep rules engine across Java, Go, Python, Kubernetes, Crossplane, Terraform, and Vault, plus read-only IaC-vs-live drift for Kubernetes and Vault.
---
# Skill: Code Map (`skill-code-map`)

## 0. Engine Selection Protocol (MANDATORY)

Before running any mapping, query, or extraction, **ask the user which engine to use** (AskUserQuestion) unless the request names one:

| Engine | Use for | Entry points |
|---|---|---|
| **Python code mapper** (tree-sitter) | Symbol inventory, `code_map.md`, package/module import graph, inheritance, auto_context ranking | `code_mapper.py`, `graph_builder.py`, `auto_context.py`, `semantic_query.py` |
| **ast-grep** (rules & policies) | Structural patterns, 6-Pillar Well-Architected audits (`SEC`/`REL`/`OPS`/`PERF`/`COST`/`SUS`), Kodus Markdown Policy-as-Code hydration (227+ rules across Python/Java/Go) | `local_extract.py`, `well_architected_audit.py`, `hydrate_policies.py`, `ast-grep run -p ...` |
| **State graph** (IaC vs live) | Desired-vs-live drift, Vault posture lint, cluster health | `state_graph.py`, `k8s_catalog.py` |
| **Graphify bridge** (`skill-graphify`) | Interactive D3/Mermaid callflow HTML, community/God-node topology, unified code+K8s+Vault graph, multi-repo global graph | `--format graphify` on `graph_builder.py` / `k8s_catalog.py` / `state_graph.py`, plus `k8s_graphify_extract.py` |

Do not default silently. Offer the engine that fits the question and say why. Never spawn a subagent for this.

### Caveats (state these when relevant)

- Run Python tooling with `/usr/bin/python3`. The linuxbrew `python3` has no `tree_sitter`.
- Always scope `code_mapper.py <dir>` and `graph_builder.py <dir>` to the target project/subsystem directory after asking the user; `code_mapper.py` persists both `code_map.md` and `relationship_graph.json` and short-circuits on a warm cache (`0 files changed`), unless `--force` is passed.
- The Go graph is package-level imports only. It has no call graph. Use ast-grep for call sites.
- Bundled tree-sitter Go grammar predates Go 1.26 `new(expr)`. Affected files (159 in kubernetes) keep most symbols but are reported as syntax errors.
- YAML syntax errors are not reported (helm templates and negative fixtures fail by design). Helm and kustomize output must be rendered before `state_graph.py` can see it.
- ast-grep quirks: `$$$B` after a keyword argument matches nothing (use `any:` with both forms); `$X.Method()` does not match a nested Go selector receiver (write `$A.$B.Method()`).
- `go_feature_gate_check` can over-match (`$A.Enabled($PKG.$GATE)`); treat counts as an upper bound.
- Mapping writes `code_map.md` and `.ast_cache` into the target directory.
- Live reads (`state_graph.py`) were verified only against fixtures and recorded JSON. No cluster or Vault was reachable when the module was written. Verify against a lower environment before trusting live output.

Unified operational manual and deterministic CLI workflow for structural code extraction, symbol mapping, and AST rules engine using `ast-grep` and `tree-sitter`.

## 1. Prerequisites & Engine Installation

The rule engine relies on `ast-grep` (`sg`). Verify or install before running queries:

```bash
# macOS / Linux (Homebrew)
brew install ast-grep

# Cargo (Alternative)
cargo install ast-grep --locked

# Verification
ast-grep --version
```

---

## 2. Directory Architecture

All scripts, configs, and rule definitions are self-contained within this skill:

```text
.agent/skills/skill-code-map/
├── SKILL.md
├── resources/
│   ├── RULE_AUTHORING_GUIDE.md
│   ├── sgconfig.yml
│   └── policies/              # Kodus-style Markdown Policy-as-Code packs (python/, java/, go/)
└── scripts/
    ├── local_extract.py       # Core normalization & token-pruning engine
    ├── code_mapper.py         # Full repo AST symbol & structural mapper
    ├── graph_builder.py       # Inter-file call & import dependency graph (--format codemap|graphify)
    ├── k8s_catalog.py         # OpenAPI v3 + CRD redacted relationship catalog (--format catalog|graphify)
    ├── auto_context.py        # Ranks task-relevant files from CodeMap or Graphify graph
    ├── semantic_query.py      # Targeted usage / symbol cross-file queries (CodeMap or Graphify graph)
    ├── state_graph.py         # IaC-vs-live drift, Vault posture lint, cluster health (--format json|graphify)
    ├── well_architected_audit.py # 6-Pillar Well-Architected Code Auditor (--diff, --policies)
    ├── hydrate_policies.py    # Semgrep/ast-grep -> Markdown Policy-as-Code transpiler & canary validator
    ├── sgconfig.yml           # Self-contained ast-grep engine config
    └── rules/                 # Structural AST rule definitions
        ├── java/              # Spring controllers, services, repositories
        ├── kubernetes/        # K8s manifests, API groups, Kinds
        ├── crossplane/        # XRDs (CompositeResourceDefinition), Compositions
        ├── terraform/         # Providers, modules, resource attributes
        ├── vault/             # API paths, actions, ACL policies, hvac clients, auth strategies
        ├── go/                # Informer factories, controller ctors, cobra commands, feature gates, exec, routes
        └── python/            # Typer commands, env reads, subprocess shell=True, TLS verify=False
```

### Language coverage (code_mapper.py + graph_builder.py)

| Language | Symbols (code_map.md) | Graph (`graph_builder.py`) |
|---|---|---|
| Go | types, funcs, receiver-qualified methods (`Pod.Run`) | `go-package` nodes, in-repo `imports` edges; nested `go.mod` modules resolved |
| Python | classes, funcs | `py-module` nodes, `imports` (absolute, relative, foreign-prefix by suffix) and `inherits` edges |
| Java | classes, interfaces, methods | class/method nodes; injects, calls, throws, routes |
| HCL / YAML / Rust | blocks, k8s/ansible declarations / items | HCL usage edges |

Hardening: schema-versioned cache (stale entries re-indexed), deleted files pruned, atomic cache write, files over 5 MB skipped, `vendor/` skipped, syntax-error and missing-grammar files reported (YAML excluded; helm templates fail by design). Known limit: the bundled Go grammar predates `new(expr)` (Go 1.26); affected files parse with local errors and keep most symbols.

Run tests with `/usr/bin/python3` (the linuxbrew `python3` has no `tree_sitter`): `tests/test_code_mapper.py`, `test_go_graph.py`, `test_ast_grep_rules.py`.

---

## 3. Deterministic Execution Workflows

### Workflow A: Multi-Domain Structural Scan (Normalized JSON)
Run `local_extract.py` across target application or infrastructure directories. It prunes raw tokens, cleans character offsets, and produces deterministic structured records:

```bash
# Target single or multiple project directories
python3 .agent/skills/skill-code-map/scripts/local_extract.py projects/cloud-boot-app projects/vault_controller
```

#### Pipeline Examples & Record Aggregation
```bash
# Get summary count by record_type
python3 .agent/skills/skill-code-map/scripts/local_extract.py projects/cloud-boot-app projects/vault_controller | \
  jq '[.records[].record_type] | group_by(.) | map({type: .[0], count: length})'

# Filter specifically for Spring RestControllers
python3 .agent/skills/skill-code-map/scripts/local_extract.py projects/cloud-boot-app | \
  jq '.records[] | select(.record_type == "controller_declaration")'

# Filter specifically for Vault API endpoints & actions
python3 .agent/skills/skill-code-map/scripts/local_extract.py projects/vault_controller | \
  jq '.records[] | select(.record_type == "vault_api_path")'

# Filter Crossplane XRDs & Compositions
python3 .agent/skills/skill-code-map/scripts/local_extract.py projects/cloud-boot-app/crossplane | \
  jq '.records[] | select(.record_type | startswith("crossplane_"))'
```

---

### Workflow B: Ad-Hoc `ast-grep` Terminal Queries

When querying specific files, symbols, or functions directly without running the full pipeline:

#### 1. Java / Spring Boot Patterns
```bash
# Find all classes annotated with @RestController or @Controller
ast-grep run -l java -p '@$ANNOTATION class $CLASS { $$$ }' projects/cloud-boot-app

# Find specific method calls with wildcard arguments (e.g. checkResourceFound or ntms)
ast-grep run -l java -p 'checkResourceFound($$$ARGS)' projects/cloud-boot-app
ast-grep run -l java -p 'ntms($$$ARGS)' <target_folder>

# Find method invocations on a variable or object instance
ast-grep run -l java -p '$OBJ.ntms($$$)' <target_folder>
ast-grep run -l java -p 'ntms.$METHOD($$$)' <target_folder>

# Find all HTTP endpoint route mappings
ast-grep run -l java -p '@$MAP(value = $PATH, $$$) public $$$' projects/cloud-boot-app

# Audit field injection anti-pattern (@Autowired fields)
ast-grep run -l java -p '@Autowired $TYPE $FIELD;' projects/cloud-boot-app
```

#### 2. Kubernetes & Crossplane Patterns
```bash
# Match any Kubernetes resource by apiVersion and kind
ast-grep run -l yaml -p 'apiVersion: $API' projects/cloud-boot-app

# Match Crossplane CompositeResourceDefinitions (XRDs)
ast-grep run -l yaml -p 'kind: CompositeResourceDefinition' projects/cloud-boot-app

# Match Crossplane Compositions
ast-grep run -l yaml -p 'kind: Composition' projects/cloud-boot-app
```

#### 3. Terraform (HCL) Patterns
```bash
# Match top-level blocks (resource, module, provider, terraform)
ast-grep run -l hcl --kind block projects/cloud-boot-app/terraform

# Match specific attribute assignments
ast-grep run -l hcl -p '$ATTR = $VAL' projects/cloud-boot-app/terraform
```

#### 4. Live Kubernetes Cluster Introspection
To pull live CRD instances across served API versions (`v1`, `v2`, `v3`) on a running cluster:
```bash
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
python3 bin/pull_cluster_crd_state.py
```

---

### Workflow C: Repository Symbol Indexing, Lensing & Graphify Export

```bash
# 1. Generate / refresh incremental repository code map
/usr/bin/python3 .agent/skills/skill-code-map/scripts/code_mapper.py .

# 2. Extract AST dependency graph (native codemap or Graphify node_link_data format)
/usr/bin/python3 .agent/skills/skill-code-map/scripts/graph_builder.py <dir> --output relationship_graph.json
/usr/bin/python3 .agent/skills/skill-code-map/scripts/graph_builder.py <dir> --format graphify --output graph.json

# 3. Rank the files relevant to a task (accepts either relationship_graph.json or Graphify graph.json)
/usr/bin/python3 .agent/skills/skill-code-map/scripts/auto_context.py "<task_objective>" --src <dir>
#    or reuse any CodeMap / Graphify unified graph:  --graph unified-graph.json [--top 5] [--json]

# 4. Query definitions, usages, dependencies, and transitive impact across CodeMap or Graphify graphs
/usr/bin/python3 .agent/skills/skill-code-map/scripts/semantic_query.py --graph unified-graph.json impact <symbol>

# 5. Show only the code_map.md blocks that mention a symbol
/usr/bin/python3 .agent/skills/skill-code-map/scripts/search_map.py <symbol> code_map.md

# 6. Replace one declaration by AST node (refuses ambiguous/missing names and unparseable results)
/usr/bin/python3 .agent/skills/skill-code-map/scripts/semantic_edit.py <file> method DataService.getData '<full replacement incl. annotations>' --dry-run
```

---

### Workflow D: IaC vs Live State (Kubernetes + Vault)

`state_graph.py` compares desired state (rendered manifests, `vault_controller` `api_paths:` YAML) with live state and applies the vault_controller security opinions. Read-only: `kubectl get`, `vault read|list`. Supports `--format graphify` to export drift communities (`in-sync`, `drifted`, `missing`, `unmanaged`, `vault_lint`) and cross-system links (`uses-vault-role`, `binds-serviceaccount`, `grants-policy`) for Graphify visualization.

```bash
SG=.agent/skills/skill-code-map/scripts/state_graph.py
# Static posture lint of a vault_controller config tree (no network)
/usr/bin/python3 $SG lint --vault projects/vault_controller/config/example_vault
# Kubernetes drift + cluster health + Vault drift + cross-system checks
/usr/bin/python3 $SG report --k8s <rendered-manifest-dirs> --vault <vault-config-dir> [--vault-namespace NS] [--context CTX]
# Offline (recorded snapshots, air-gapped)
/usr/bin/python3 $SG report --k8s <dirs> --live-k8s live_k8s.json --vault <dir> --live-vault live_vault.json
# Export IaC-vs-live drift and cross-system links directly into Graphify format
/usr/bin/python3 $SG report --k8s <dirs> --live-k8s live_k8s.json --vault <dir> --no-live-vault --format graphify > state-graphify.json
```

| Output key | Meaning |
|---|---|
| `vault_lint` | `repo-rule` = enforced by vault_controller `ValidationManager` (root namespace, namespace-dir parity, read/write mix, mount TTL over 1h, plaintext secret without `vault:v1:`, forbidden actions under `kv/`, path traversal). `advisory` = added hardening (insecure_tls, exportable transit keys, audit log in /tmp, wildcard k8s role bindings, remote http Vault, `key_encrypt: false`). |
| `k8s_drift` | `missing` (in repo, not in cluster), `drifted` (desired fields that differ; extra live fields ignored), `unmanaged` (in cluster, not in repo; generated objects excluded). |
| `vault_drift` | Same three buckets for policies, mounts, auth methods, audit devices, kubernetes auth roles. TTLs compared in seconds, list order ignored. KV data is never compared. |
| `cluster_health` | Unready pods, CrashLoop/ImagePull, under-replicated workloads, NotReady nodes, Pending PVCs, Services whose selector matches no pod. |
| `cross_check` | Vault kubernetes-auth roles binding ServiceAccounts that do not exist; workloads annotating `vault.hashicorp.com/role` for roles not defined in Vault config. |

Safety: Secret `data`/`stringData` are stripped at fetch and at load, values under sensitive keys are redacted in every diff, Vault tokens come from the environment only, and a kubectl context containing `prod` is refused unless `--allow-prod-read`. Ask the user to run any cloud or Vault login; never request credentials.

---

## 4. Record Output Schema Standard

Every record returned by `local_extract.py` conforms to this contract:

```json
{
  "record_type": "controller_declaration | k8s_resource | crossplane_xrd | crossplane_composition | terraform_attribute | vault_api_path",
  "record_id": "<file_path>#<source_name>:<line_number>",
  "path": "<file_path>",
  "source_name": "<identifier>",
  "source_scope": "web_layer | service_layer | k8s_infrastructure | crossplane_v2 | cloud_infra | vault_security",
  "line": 42,
  "extracted_data": {
    "<metavariable_key>": "<metavariable_value>"
  }
}
```

---

## 5. Adding New Rules

1. Define a YAML rule inside `.agent/skills/skill-code-map/scripts/rules/<domain>/<rule-name>.yml`:
   ```yaml
   id: extract-<domain>-<name>
   language: <java|yaml|hcl|python|go>
   rule:
     pattern: |
       <pattern_with_$VARS_and_$$$>
   metadata:
     record_type: <domain_entity>
     source_scope: <scope_boundary>
     extract:
       field_name: VAR
   ```
2. Ensure directory is registered in `.agent/skills/skill-code-map/scripts/sgconfig.yml`.
3. `record_type` / `source_scope` are read from the rule's `metadata` automatically (the `scope_map` in `local_extract.py` is only a legacy fallback). `source_name` is the first of `path, class, name, kind, gate, use, route, key, cmd, fn` that the rule extracts.
4. Quirks: `$$$B` after a keyword argument matches nothing, so write `any:` with `f($$$A, kw=V)` and `f(kw=V, $$$B)`; `$X.Method()` does not match a nested selector receiver in Go, so spell out `$A.$B.Method()`.
5. Test with: `python3 .agent/skills/skill-code-map/scripts/local_extract.py <test-path>`.
