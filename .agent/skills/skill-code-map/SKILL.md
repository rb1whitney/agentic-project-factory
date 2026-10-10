---
name: skill-code-map
description: Deterministic multi-language AST structural extractor, code mapper, and ast-grep rules engine across Java, Kubernetes, Crossplane, Terraform, and Vault.
---
# Skill: Code Map (`skill-code-map`)

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
│   └── sgconfig.yml
└── scripts/
    ├── local_extract.py       # Core normalization & token-pruning engine
    ├── code_mapper.py         # Full repo AST symbol & structural mapper
    ├── graph_builder.py       # Inter-file call & import dependency graph
    ├── auto_context.py        # Task-driven context lensing (<100k tokens)
    ├── semantic_query.py      # Targeted usage / symbol cross-file queries
    ├── sgconfig.yml           # Self-contained ast-grep engine config
    └── rules/                 # Structural AST rule definitions
        ├── java/              # Spring controllers, services, repositories
        ├── kubernetes/        # K8s manifests, API groups, Kinds
        ├── crossplane/        # XRDs (CompositeResourceDefinition), Compositions
        ├── terraform/         # Providers, modules, resource attributes
        └── vault/             # API paths, actions, secret mounts, ACL policies
```

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

### Workflow C: Repository Symbol Indexing & Lensing

```bash
# 1. Generate / refresh incremental repository code map
python3 .agent/skills/skill-code-map/scripts/code_mapper.py .

# 2. Extract AST dependency graph
python3 .agent/skills/skill-code-map/scripts/graph_builder.py

# 3. Lens into 5-10 relevant files for a specific prompt/task
python3 .agent/skills/skill-code-map/scripts/auto_context.py "<task_objective>" code_map.md
```

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
3. Add mapping entry to `scope_map` in `.agent/skills/skill-code-map/scripts/local_extract.py`.
4. Test with: `python3 .agent/skills/skill-code-map/scripts/local_extract.py <test-path>`.
