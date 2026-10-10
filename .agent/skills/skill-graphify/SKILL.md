---
name: skill-graphify
description: Lifecycle manager, knowledge graph generator, and topological dependency visualizer using Graphify (Graphify-Labs/graphify). Supports local AST extraction, LLM semantic inference, interactive D3/Mermaid callflows, and global multi-repo graph linking.
---
# Skill: Graphify Knowledge Graph Engine (`skill-graphify`)

Operational manual and lifecycle manager for **Graphify** ([Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)).

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

# Code-only extraction to a specific output folder
graphify extract <target_directory> --code-only --out <target_directory>/graphify-out
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

## 3. Comparison: `graphify` vs. `ast-grep`

| Capability | `graphify` | `ast-grep` (`sg`) |
| :--- | :--- | :--- |
| **Primary Purpose** | **Macro Architecture & Knowledge Graph** | **Micro Pattern Search & Code Surgery** |
| **Granularity** | Graph-level: nodes (files, classes, modules), edges (calls, imports, inherits), community clusters | Node-level: exact syntax nodes inside a method, expressions, statements |
| **Queries** | "Which module is the most connected God Node?", "Show call path from API to DB" | "Find all methods annotated with `@Transactional` having unhandled exceptions" |
| **Mutation / Refactor** | Read-only graph extraction | In-place syntax rewrites (`--rewrite`) |
| **Cross-File Links** | Built-in NetworkX graph topology and community detection | Single-file syntax queries (requires external indexer for cross-file) |
| **Doc / Schema Ingestion** | Ingests Markdown, PDF, SQL, and database schemas | Code ASTs only |

### Best-Practice Pairing
1. **Use `graphify`** first to map the high-level system topology, find God Nodes, and pinpoint which file clusters to investigate.
2. **Use `ast-grep`** second to inspect method internals, check anti-patterns, and execute precise surgical code changes within those targeted files.
