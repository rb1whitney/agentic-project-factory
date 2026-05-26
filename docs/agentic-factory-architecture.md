# Agentic Factory: Architecture, Hooks, and Memory System

**Version**: 2026 ACS v1.2 | **Standard**: Unified Agentic Hub

This document explains the full runtime architecture of the Agentic Project Factory — how lifecycle hooks fire, how skills are activated, how the memory layer persists context, and how every component connects.

---

## 1. High-Level Architecture

The factory is organized as a **Hub-and-Spoke** model. The `.agent/` directory is the physical source of truth. All vendor IDE configurations are symlink polyfills pointing back to this hub.

```mermaid
graph TD
    HUB[".agent/ Hub — Source of Truth"]

    HUB --> AGENTS[".agent/agents/ — Specialist Definitions"]
    HUB --> SKILLS[".agent/skills/ — Skill Modules"]
    HUB --> HOOKS[".agent/hooks/ — Lifecycle Automation"]
    HUB --> POLICIES[".agent/policies/ — Governance Rules"]
    HUB --> SETTINGS[".agent/settings.json — MCP Server Registry"]

    AGENTS --> MEMORY_AGENT["memory-agent.md"]
    AGENTS --> SWARM_SCOUT["swarm-scout.md"]
    AGENTS --> SWARM_ARCH["swarm-architect.md"]
    AGENTS --> SWARM_ENG["swarm-engineer.md"]
    AGENTS --> SWARM_AUD["swarm-auditor.md"]

    SKILLS --> SK_MEMORY["skill-always-on-memory"]
    SKILLS --> SK_SWARM["skill-swarm"]
    SKILLS --> SK_CONDUCTOR["skill-conductor"]
    SKILLS --> SK_CONTEXT["skill-context-master"]

    HOOKS --> H_START["session_start.json"]
    HOOKS --> H_PRE["pre_tool_use.json"]
    HOOKS --> H_POST["post_task.json"]
```

---

## 2. Lifecycle Hook Architecture

Hooks are deterministic JSON-defined event triggers. They fire at exact lifecycle boundaries and execute shell commands or send system notifications. No agent discretion involved — hooks always fire.

### Hook Events

| Hook File | Event | Fires When |
|---|---|---|
| `session_start.json` | `sessionStart` | A new agent session is opened |
| `pre_tool_use.json` | `preToolUse` | Before any tool or command is executed |
| `post_task.json` | `postTask` | After a complete task is marked done |

### Hook Execution Flow

```mermaid
sequenceDiagram
    participant IDE as IDE or CLI
    participant HOOK as Hook Engine
    participant AST as bin/ast-bridge/code_mapper.py
    participant MEM as bin/memory_agent.py
    participant DOCS as bin/update_docs.py

    IDE->>HOOK: Session opened
    HOOK->>AST: Regenerate symbol map
    AST-->>HOOK: code_map.md refreshed
    HOOK->>MEM: memory start default_session
    MEM-->>HOOK: Session marked ACTIVE in memory.db
    HOOK-->>IDE: ACS Hub Loaded notification

    Note over IDE,MEM: Agent executes task work here

    IDE->>HOOK: Task completed
    HOOK->>DOCS: Auto-update documentation
    DOCS-->>HOOK: Docs refreshed
    HOOK->>MEM: memory complete default_session
    MEM-->>HOOK: Session marked COMPLETED in memory.db
    HOOK-->>IDE: Task complete notification
```

### Current Hook Definitions

**session_start.json** — fires on every new session:
```json
{
  "event": "sessionStart",
  "actions": [
    { "execute": "python3 bin/ast-bridge/code_mapper.py ." },
    { "execute": "python3 bin/memory_agent.py start default_session" },
    { "message": "ACS Hub Loaded. Symbol Map Refreshed." }
  ]
}
```

**post_task.json** — fires at task completion:
```json
{
  "event": "postTask",
  "actions": [
    { "execute": "python3 bin/update_docs.py" },
    { "execute": "python3 bin/memory_agent.py complete default_session" },
    { "message": "Task complete. Documentation updated successfully." }
  ]
}
```

---

## 3. Skill Activation Architecture

Skills are self-contained capability modules inside `.agent/skills/`. Each skill has a `SKILL.md` defining its name, related skills, auto-triggers, and behavioral protocols.

### Tiered Discovery Protocol

Agents MUST follow two-tier loading as defined in `acs.yaml`:

- **Tier 1**: Read skill name and description only. Used for routing decisions.
- **Tier 2**: Load full `SKILL.md` content. Only when the task matches the skill domain.

This enforces the **60-98% token reduction** mandate from the Token Harvester standard.

### Skill Auto-Trigger Map

```mermaid
graph LR
    TASK["Incoming Task"]

    TASK -->|contains recall or remember| MEM_SK["skill-always-on-memory"]
    TASK -->|contains swarm or dispatch| SW_SK["skill-swarm"]
    TASK -->|contains track or conductor| CD_SK["skill-conductor"]
    TASK -->|contains aws or lambda| AWS_SK["skill-aws or skill-aws-serverless"]
    TASK -->|contains gcp or gke| GCP_SK["skill-gcp or skill-kubernetes"]
    TASK -->|contains terraform| TF_SK["skill-terraform"]
    TASK -->|contains incident or alert| SRE_SK["skill-sre-investigation"]
    TASK -->|contains pr or pull request| GH_SK["skill-github or skill-pr-creator"]

    MEM_SK --> MEM_AGENT["memory-agent.md"]
    SW_SK --> SWARM_CTRL["Swarm Nexus Controller"]
    CD_SK --> CONDUCTOR["Conductor CDD Lifecycle"]
```

### Skill Relationship Graph

```mermaid
graph TD
    MEM_A["memory-agent"]
    SK_MEM["skill-always-on-memory"]
    SK_COND["skill-conductor"]
    SK_SWARM["skill-swarm"]
    SK_RECON["skill-codebase-recon"]
    SK_CTX["skill-context-master"]
    SK_AST["bin/ast-bridge AST Engine"]

    MEM_A --> SK_MEM
    MEM_A --> SK_COND

    SK_SWARM --> SK_COND
    SK_SWARM --> SK_RECON
    SK_SWARM --> SK_CTX

    SK_RECON --> SK_AST
    SK_CTX --> SK_AST

    SK_MEM --> MEM_DB["memory.db — SQLite Store"]
    SK_AST --> AST_CACHE[".ast_cache/context_map.json"]
```

---

## 4. Always-On Memory System

The memory layer is based on the **Google ADK Always-On Memory Agent** architecture. It gives the swarm persistent, evolving cognitive state across all sessions.

### Three-Phase Cognitive Loop

```mermaid
sequenceDiagram
    participant AGENT as Active Swarm Agent
    participant MEM as memory-agent
    participant DB as memory.db

    Note over AGENT,DB: PHASE 1 — INGEST
    AGENT->>MEM: Task starts. Recall prior context.
    MEM->>DB: SELECT insights WHERE category LIKE task_domain
    DB-->>MEM: Matching prior insights returned
    MEM-->>AGENT: Report relevant history before work begins

    Note over AGENT,DB: PHASE 2 — CONSOLIDATE
    AGENT->>MEM: Architectural decision confirmed
    MEM->>DB: INSERT INTO insights VALUES category insight_text impact_score
    DB-->>MEM: Insight committed

    Note over AGENT,DB: PHASE 3 — QUERY
    AGENT->>MEM: Query for synthesis across all memory
    MEM->>DB: SELECT insights ORDER BY impact_score DESC
    DB-->>MEM: Top insights returned with session citations
    MEM-->>AGENT: Synthesized answer with source trail
```

### Memory Database Schema

```mermaid
erDiagram
    sessions {
        TEXT session_id PK
        TEXT start_time
        TEXT end_time
        TEXT status
    }
    interactions {
        INTEGER interaction_id PK
        TEXT session_id FK
        TEXT timestamp
        TEXT request
        TEXT response
        INTEGER tokens_used
    }
    insights {
        INTEGER insight_id PK
        TEXT session_id FK
        TEXT timestamp
        TEXT category
        TEXT insight_text
        REAL impact_score
    }

    sessions ||--o{ interactions : "has"
    sessions ||--o{ insights : "generates"
```

### Insight Category Taxonomy

| Category | Score Range | Usage |
|---|---|---|
| `architecture` | 3.0 - 5.0 | Structural design decisions, ADRs |
| `standards` | 4.0 - 5.0 | Protocol standards, frameworks, specs |
| `governance` | 4.0 - 5.0 | Branch policies, compliance, audit gates |
| `security` | 3.0 - 5.0 | Auth patterns, zero-trust, credential rules |
| `sre` | 3.0 - 4.5 | Operational runbooks, port configs, gotchas |
| `performance` | 2.0 - 4.0 | Token costs, bottlenecks, optimization wins |
| `debugging` | 1.0 - 3.5 | Known bugs, error patterns, resolution paths |

---

## 5. Token Harvester Integration

The factory enforces a **60-98% token reduction mandate** via five interlocking frameworks registered in `AGENTS.md Section 2.1`.

| Framework | Tool | Role |
|---|---|---|
| SkillOS Dialects | Internal | `strict-patch` edits, `caveman-prose` logs, `dom-nav` browser tokens |
| Context-Mode | MCP server | SQLite FTS5 gating. Return query matches, not raw dumps |
| Code-Review-Graph | MCP server | Tree-sitter blast radius. Load only touched symbol files |
| Caveman-Prose Ultra | Protocol | Strip articles, niceties, hedging from all agent outputs |
| Python Token Killer | `bin/rtk` | ANSI strip, loop collapse, hard truncation on terminal output |

### Token Filter Flow

```mermaid
graph LR
    CMD["Shell Command Output"]
    RTK["bin/rtk — Python Token Killer"]
    AGENT["Agent Context Window"]

    CMD -->|raw stdout| RTK
    RTK -->|strip ANSI| S1["Clean Text"]
    S1 -->|collapse repeating lines| S2["Deduplicated Lines"]
    S2 -->|truncate at 80 lines| S3["Anchor-Preserved Output"]
    S3 --> AGENT
```

---

## 6. Swarm Nexus Synchronization

`bin/nexus.py` is the factory compiler. It ensures the `.agent/` hub is the authoritative source and that all IDE polyfill spokes reflect the latest state.

**Run at any time to recompile**:
```bash
python3 bin/nexus.py
```

**What it does**:
1. Reads all agent and skill definitions from `.agent/`
2. Verifies each symlink polyfill target exists and is correctly linked
3. Warns on any raw files that are NOT symlinks — these represent governance drift
4. Prints a clean compile status on exit

---

## 7. Reference Index

| Resource | Link |
|---|---|
| Always-On Memory Agent Upstream | https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent |
| Plan-Commands Specification | https://github.com/jjdelorme/plan-commands |
| SkillOS Dialects | https://github.com/EvolvingAgentsLabs/skillos/blob/main/docs/dialects.md |
| Context-Mode | https://github.com/mksglu/context-mode |
| Code-Review-Graph | https://github.com/tirth8205/code-review-graph |
| Caveman-Prose | https://github.com/juliusbrussee/caveman |
| RTK Reference | https://github.com/rtk-ai/rtk |
