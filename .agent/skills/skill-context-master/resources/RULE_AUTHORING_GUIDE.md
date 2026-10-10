# AST-Grep Custom Rule Authoring Guide

## 1. Engine Installation
Before running structural queries or rules scans, ensure `ast-grep` is installed:
```bash
brew install ast-grep
# or via cargo
cargo install ast-grep --locked
```

## 2. Directory Layout
Place domain rules under `resources/rules/local/<domain>/`:
```text
resources/rules/local/
  ├── java/          # Spring Boot, Controllers, Service classes
  ├── kubernetes/    # API groups, Kinds, metadata
  ├── crossplane/    # XRDs, Compositions, Claims
  ├── terraform/     # HCL blocks, providers, attributes
  └── vault/         # Vault API paths, actions, ACL policies
```

## 3. Rule Structure Standard
Every rule requires an `id`, target `language`, structural `rule` pattern, and `metadata` for normalizer consumption:

```yaml
id: extract-<domain>-<name>
language: <java|yaml|hcl|python|go>
rule:
  pattern: |
    <code-pattern-with-$METAVARS-and-$$$>
metadata:
  record_type: <domain>_<entity>
  source_scope: <scope_layer>
  extract:
    field1: METAVAR1
    field2: METAVAR2
```

## 4. Normalization Execution
Run the embedded extractor script:
```bash
python3 scripts/local_extract.py <target-path>
```
All outputs adhere to the schema:
- `record_type`: domain tag (e.g. `k8s_resource`, `crossplane_composition`, `vault_api_path`)
- `record_id`: `<file>#<source_name>:<line>`
- `path`: target file path
- `source_name`: symbol/resource identifier
- `source_scope`: boundary classification
- `extracted_data`: pruned metavariables
