---
name: skill-always-on-memory
description: Always-On Memory Agent Skill. Queries the local memory database to understand insights, track session interactions, and retrieve historical context.
related_skills: ["@skill-conductor", "@skill-codebase-recon", "@skill-swarm"]
auto_triggers: ["memory_init", "record_interaction", "record_insight", "query_memory", "recall", "remember"]
---

# Always-On Memory: Cognitive Persistent Context

Most agents have amnesia. They process information when asked, then forget everything. This skill establishes a **persistent, local memory layer** for the agentic swarm — continuously processing, consolidating, and connecting information across sessions.

**No vector database. No embeddings. Just structured reads and writes from a local SQLite store.**

## 1. Upstream Standard Reference
*   **Primary Architecture**: [GoogleCloudPlatform/generative-ai — always-on-memory-agent](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent)
*   **Built With**: Google ADK (Agent Development Kit) + Gemini Flash-Lite + SQLite
*   **Local Implementation**: [bin/memory_agent.py](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/bin/memory_agent.py)
*   **Storage**: `memory.db` (local SQLite, git-ignored)

---

## 2. Architecture: Triple-Layer Hybrid Stack

This skill now orchestrates a 2026-standard hybrid memory stack, delegating specialized paging to `@skill-episodic-memory` and extraction to `@skill-graph-memory`.

### Layer 1 — CORE MEMORY (RAM)
The agent's immediate context block. Managed by Episodic Memory rules. Paged in at session start, paged out when context bloats.

### Layer 2 — RECALL MEMORY (Disk)
The traditional SQLite interaction and insight log. Handled via standard `bin/memory_agent.py` inserts and queries. Acts as fuzzy, semantic history.

### Layer 3 — GRAPH MEMORY (Relational)
Extracted entities and relationships. Triggered during the `CONSOLIDATE` phase (via `python3 bin/memory_agent.py complete <session_id>`). 

```
[User Workspace] -> migrated to -> [Antigravity CLI]
         │                                  │
      impacts                            requires
         ▼                                  ▼
[SRE Agent Config]                   [mcp_config.json]
```

---

## 3. Structural Topology (`memory.db`)

Five high-performance SQLite tables support the hybrid stack:

| Table | Purpose | Key Fields |
|---|---|---|
| `sessions` | Task/session boundaries | `session_id`, `start_time`, `status` |
| `interactions` | Recall: Logged user↔agent exchanges | `request`, `response`, `tokens_used` |
| `insights` | Recall: Distilled, high-impact lessons | `category`, `insight_text`, `impact_score` |
| `entities` | Graph: Extracted nodes | `entity_id`, `name`, `type` |
| `relationships`| Graph: Edges between nodes | `source_id`, `target_id`, `predicate`, `timestamp` |

**Indexes**: `idx_insights_category`, `idx_interactions_session`, `idx_graph_source`, `idx_graph_target` for high-speed routing.

---

## 4. Lifecycle Hook Integration

The memory database is automatically managed by the lifecycle hooks:

| Hook | Action |
|---|---|
| `session_start.json` | `python3 bin/memory_agent.py start default_session` |
| `post_task.json` | `python3 bin/memory_agent.py complete default_session` |

---

## 5. CLI Interface (Full Reference)

**Initialize database**:
```bash
python3 bin/memory_agent.py init
```

**Start a named session**:
```bash
python3 bin/memory_agent.py start <session_id>
```

**Query insights by keyword**:
```bash
python3 bin/memory_agent.py query "terraform"
python3 bin/memory_agent.py query "authentication"
```

**Add a high-impact insight**:
```bash
python3 bin/memory_agent.py add-insight <session_id> "<category>" "<insight_text>" <impact_score>

# Example:
python3 bin/memory_agent.py add-insight default_session "SRE" \
  "OIDC auth requires OTLP ports configured deterministically before service mesh init" 4.5
```

**Log an interaction**:
```bash
python3 bin/memory_agent.py add-interaction <session_id> "<request>" "<response>" <tokens>
```

**Show database summary**:
```bash
python3 bin/memory_agent.py summary
```

**Mark session complete & Trigger Consolidation (Hook integration)**:
```bash
python3 bin/memory_agent.py complete <session_id>
```
*Note: Executing `complete` automatically flushes ephemeral Core Memory to Disk and runs the Graph Extraction pipeline over the session's interactions. This ensures `post_task.json` hooks remain fully compatible with the new architecture.*

---

## 6. Insight Categories (Standardized)
Use consistent categories to enable precise recall:

| Category | Usage |
|---|---|
| `architecture` | Structural design decisions, ADRs |
| `standards` | Protocol standards, frameworks, specs |
| `sre` | Operational runbooks, gotchas, port configs |
| `security` | Auth patterns, credential rules, zero-trust |
| `performance` | Token costs, bottlenecks, optimization wins |
| `governance` | Compliance rules, branch policies, audit gates |
| `debugging` | Known bugs, error patterns, resolution paths |

---

## 7. Memory Agent Behavioral Mandate

Before starting **any** new track or complex task, the `@memory-agent` MUST:

1. **RECALL**: Run `python3 bin/memory_agent.py query "<task keyword>"` to check for prior art.
2. **REPORT**: Surface all matching insights with their `impact_score` before proceeding.
3. **PROCEED**: Only after confirming no conflicting decisions exist in memory.
4. **CAPTURE**: At task completion, write ≥1 distilled insight per significant architectural decision.
