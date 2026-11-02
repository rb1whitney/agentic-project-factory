---
name: skill-always-on-memory
description: Persistent SQLite-based cognitive layer for cross-session interaction logging and insight distillation.
---
# Skill: Always-On Cognitive Memory (`skill-always-on-memory`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: cognitive-memory-archivist] parent=skill-always-on-memory required_inputs=['memory_action', 'query_topic']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
python3 bin/memory_agent.py {memory_action} --query "{query_topic}" 2>/dev/null | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_always_on_memory_workflow(memory_action, query_topic):
  1. PRE-CHECK: SQLite memory store initialized via bin/memory_agent.py
  2. result <- invoke(cognitive-memory-archivist, {memory_action: "<memory_action>", query_topic: "<query_topic>"})
  3. POST-CHECK: Session insights persisted and deduplicated without context bloat
  4. RETURN {Location, Problem, Fix, outputs: ['recalled_insights', 'memory_db_state']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: cognitive-memory-archivist`**
  - `trigger`: Ingest, consolidate, page, and query persistent SQLite session memory, episodic context, and relational knowledge graph triples
  - `inputs`: required `['memory_action', 'query_topic']`, optional `['session_id']`
  - `outputs`: `['recalled_insights', 'memory_db_state']`
  - `preconditions`: SQLite memory store initialized via bin/memory_agent.py
  - `postconditions`: Session insights persisted and deduplicated without context bloat
  - `side_effects`: filesystem=updates local SQLite memory db, network=none
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Ingest, consolidate, page, and query persistent SQLite session memory (`memory.db`), episodic context, and relational knowledge graph triples via `bin/memory_agent.py` using `memory_action`, `query_topic`, and `session_id` to produce `recalled_insights` and `memory_db_state`.

### 1. Triple-Layer Hybrid Memory Architecture
- **Layer 1 — Core / Episodic Memory (RAM)**: Active session context window managed via `references/episodic-memory.md` paging rules.
- **Layer 2 — Recall Memory (SQLite Disk)**: `sessions`, `interactions`, and `insights` tables indexed by category (`architecture`, `standards`, `sre`, `security`, `performance`, `governance`, `debugging`) and `impact_score`.
- **Layer 3 — Graph Memory (Relational Triples)**: `entities` and `relationships` (`source_id`, `predicate`, `target_id`) extracted during session consolidation (`references/graph-memory.md`).

### 2. Memory CLI Operations (`bin/memory_agent.py`)
Execute all memory operations piped through `bin/rtk`:
```bash
python3 bin/memory_agent.py init | bin/rtk
python3 bin/memory_agent.py start <session_id> | bin/rtk
python3 bin/memory_agent.py query "<query_topic>" | bin/rtk
python3 bin/memory_agent.py add-insight <session_id> "<category>" "<insight_text>" <impact_score> | bin/rtk
python3 bin/memory_agent.py summary | bin/rtk
python3 bin/memory_agent.py complete <session_id> | bin/rtk
```

### 3. Pre-Task Recall & Post-Task Capture Mandate
1. **RECALL**: Query `bin/memory_agent.py query "<query_topic>" | bin/rtk` before starting a new architectural track to surface prior decisions and prevent amnesia.
2. **CAPTURE**: Record distilled architectural lessons (`add-insight`) and complete the session (`complete <session_id>`) to flush graph triples.

## Reference & Script Routing Index

| Memory Capability | Trigger / Scope | Reference Runbooks & Scripts |
| :--- | :--- | :--- |
| **SQLite Recall & Insight Engine** | Session init, keyword query, insight scoring, lifecycle hook integration (`session_start.json`, `post_task.json`) | `bin/memory_agent.py` |
| **Episodic Context Paging** | Context window budgeting, paging out stale turns, summarizing long trajectories | `.agent/skills/skill-always-on-memory/references/episodic-memory.md` |
| **Relational Graph Memory** | Entity/relationship triple extraction, conflict detection, cross-session lineage | `.agent/skills/skill-always-on-memory/references/graph-memory.md` |
