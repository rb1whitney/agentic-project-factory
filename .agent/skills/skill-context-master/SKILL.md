---
name: skill-context-master
description: High-precision repository architect for AST-based code mapping, ast-grep structural extraction, and sub-100k token context lensing.
---
# Context Master: High-Precision AST & Lensing

Scripts and rules live in `skill-code-map`; this skill defines the lensing protocol only.

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
Use the rules engine in `.agent/skills/skill-code-map/resources/rules/local/` to extract clean domain records:
```bash
python3 .agent/skills/skill-code-map/scripts/local_extract.py <target_directory>
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
python3 .agent/skills/skill-code-map/scripts/code_mapper.py .
```
- **Hashing**: Uses `blake2b` to identify changed files.
- **Synthesis**: Combines AST skeletons with symbol dependencies.

### 3. Auto-Context Lensing (Stage 2: Lens)
Given a task, run `auto_context.py` to rank the files that matter. It matches symbols named in the task
to the semantic graph, then adds dependents (break if the seed changes) and dependencies (the seed relies on):
```bash
python3 .agent/skills/skill-code-map/scripts/auto_context.py "add a field to DataDTO" --src projects/cloud-boot-app/src
python3 .agent/skills/skill-code-map/scripts/auto_context.py "fix DataService.createData" --graph relationship_graph.json --top 5 --json
```
- **Deterministic**: No LLM call. Name classes, `Class.method`, or `@Annotation` in the task; prose words alone do not anchor.
- **Exit codes**: `0` ranked files, `1` bad path, `2` no symbol matched the task.
- **Honest limit**: Matching is lexical over graph symbols; a task that names nothing concrete returns no files rather than a guess.

## Adding New AST Rules
To add new structural extractors:
1. Review [RULE_AUTHORING_GUIDE.md](file://../skill-code-map/resources/RULE_AUTHORING_GUIDE.md).
2. Add YAML rules into `.agent/skills/skill-code-map/resources/rules/local/<domain>/`.
3. Add domain key mappings into `.agent/skills/skill-code-map/scripts/local_extract.py`.
4. Test with: `ast-grep scan --json -c .agent/skills/skill-code-map/resources/sgconfig.yml <target_dir>`.

## Key Files & Directories
- `.agent/skills/skill-code-map/scripts/`: Local execution scripts (`local_extract.py`, `code_mapper.py`, `graph_builder.py`, `auto_context.py`).
- `.agent/skills/skill-code-map/resources/rules/local/`: Domain rule YAML files (`java`, `kubernetes`, `crossplane`, `terraform`, `vault`).
- `.agent/skills/skill-code-map/resources/sgconfig.yml`: Global ast-grep configuration file.
- `.agent/skills/skill-code-map/resources/RULE_AUTHORING_GUIDE.md`: Standards for creating new AST rules.
