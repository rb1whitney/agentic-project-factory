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


---

## 5. Well-Architected Policy-as-Code Hydration Playbook (`hydrate_policies.py`)

To scale rules across **Python, Java, and Go** mapped to the **6 AWS Well-Architected Pillars** (`SEC`, `REL`, `OPS`, `PERF`, `COST`, `SUS`), use [`scripts/hydrate_policies.py`](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/.agent/skills/skill-code-map/scripts/hydrate_policies.py).

### 5.1 Multi-Rule Kodus Markdown Policy Pack Schema (`resources/policies/<lang>/<lang>-<pillar>.md`)
Each Markdown policy pack uses YAML frontmatter with a `rules:` list and a Markdown summary table:

```markdown
---
pack_id: wa-pack-python-sec
language: python
pillar: SEC
rule_count: 12
rules:
  - id: wa-py-sec-eval
    pillar: SEC
    severity: CRITICAL
    language: python
    problem: "Dynamic code execution via eval() enables arbitrary code injection."
    fix: "Use ast.literal_eval() or explicit parsers."
    rule:
      pattern: eval($$$ARGS)
---
# Well-Architected Policy Pack: PYTHON — SEC
```

### 5.2 Semgrep-to-`ast-grep` Structural Transpilation Rules
When importing community `semgrep/semgrep-rules` or `opengrep/opengrep-rules` YAML via `hydrate_policies.py --from-semgrep-dir <dir>` or `--fetch-upstream`:
- `pattern: foo(...)` -> `rule: { pattern: "foo($$$ARGS)" }`
- `pattern-either: [...]` -> `rule: { any: [...] }`
- `pattern-inside: ...` -> `rule: { inside: { pattern: "...", stopBy: "end" } }`
- `pattern-not: ...` -> `rule: { not: { pattern: "..." } }`
- `$...VARS` -> `$$$VARS`
- Unsupported non-structural Semgrep features (`mode: taint`, `pattern-regex`, `metavariable-regex`, `metavariable-comparison`) are automatically skipped.

### 5.3 The 4-Gate "Well-Hydrated" Certification Standard (`--verify`)
A policy vault is certified **`CERTIFIED_WELL_HYDRATED`** only when `hydrate_policies.py --verify` passes all 4 deterministic gates:
1. **Language Quota Gate**: `>= 50` active rules per target language (`python`, `java`, `go`).
2. **3x6 Language x Pillar Matrix Gate**: All 18 `(language, pillar)` cells across `{python, java, go} x {SEC, REL, PERF, OPS, COST, SUS}` are populated.
3. **Zero-Quarantine Syntax Gate**: `0` rules fail `ast-grep scan` compilation.
4. **Behavioral Canary Gate (Positive + Negative Fixtures)**:
   - Positive canary fixtures (`bad.py`, `Bad.java`, `bad.go`) trigger findings across all 3 languages and all 6 pillars.
   - Negative canary fixtures (`clean.py`, `Clean.java`, `clean.go`) produce `0` false positives.

```bash
# Hydrate curated 150 + upstream Semgrep/ast-grep rules (230+ rules)
/usr/bin/python3 .agent/skills/skill-code-map/scripts/hydrate_policies.py --fetch-upstream

# Certify that the policy vault is Well-Hydrated (4-Gate check)
/usr/bin/python3 .agent/skills/skill-code-map/scripts/hydrate_policies.py --verify
```
