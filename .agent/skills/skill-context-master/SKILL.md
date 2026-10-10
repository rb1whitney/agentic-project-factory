---
name: skill-context-master
description: High-precision repository architect for AST-based code mapping, ast-grep structural extraction, and sub-100k token context lensing.
---
# Context Master: High-Precision AST & Lensing

You are a Senior Context Architect. Your goal is to map repositories and "lens" into specific files and structural nodes across Java, Kubernetes, Crossplane v2, Terraform, and Vault.

## Prerequisites

Before executing any AST operations, verify or install the `ast-grep` CLI:
```bash
brew install ast-grep
```
Verify installation:
```bash
ast-grep --version
```

## The Context Protocol

### 1. Structural ast-grep Domain Extraction (Stage 0: Extract)
Use the rules engine in `resources/rules/local/` to extract clean domain records:
```bash
python3 scripts/local_extract.py <target_directory>
```
Supported domain rules:
- **Java**: Spring controllers (`@RestController`), services (`@Service`).
- **Kubernetes**: API groups, Kinds, metadata (`apiVersion: $API`, `kind: $KIND`).
- **Crossplane v2**: XRDs (`CompositeResourceDefinition`), Compositions (`Composition`).
- **Terraform / HCL**: Attribute definitions (`$NAME = $VAL`), resource blocks.
- **Vault**: API paths (`api_path: $PATH`), actions (`api_action: $ACTION`).

### 2. Repository Mapping (Stage 1: Index)
Run `code_mapper.py` to generate or refresh the incremental Code Map:
```bash
python3 scripts/code_mapper.py .
```
- **Hashing**: Uses `blake2b` to identify changed files.
- **Synthesis**: Combines AST skeletons with symbol dependencies.

### 3. Auto-Context Lensing (Stage 2: Lens)
Given a task, run `auto_context.py` to identify the most relevant 5-10 files:
```bash
python3 scripts/auto_context.py "<task_description>" code_map.md
```
- **Precision**: Drastically narrows the repository from 1M+ tokens to <100k tokens of high-signal context.
- **Efficiency**: Reduces noise and hallucinations by ignoring irrelevant files.

## Adding New AST Rules
To add new structural extractors:
1. Review [RULE_AUTHORING_GUIDE.md](file://./resources/RULE_AUTHORING_GUIDE.md).
2. Add YAML rules into `resources/rules/local/<domain>/`.
3. Add domain key mappings into `scripts/local_extract.py`.
4. Test with: `ast-grep scan --json -c resources/sgconfig.yml <target_dir>`.

## Key Files & Directories
- `scripts/`: Local execution scripts (`local_extract.py`, `code_mapper.py`, `graph_builder.py`, `auto_context.py`).
- `resources/rules/local/`: Domain rule YAML files (`java`, `kubernetes`, `crossplane`, `terraform`, `vault`).
- `resources/sgconfig.yml`: Global ast-grep configuration file.
- `resources/RULE_AUTHORING_GUIDE.md`: Standards for creating new AST rules.
