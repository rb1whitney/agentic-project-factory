# Memory Agent Architecture (2026 Standards)

The Agentic Project Factory utilizes a state-of-the-art **Triple-Layer Hybrid Stack** for its `@memory-agent`. This replaces legacy flat-RAG systems with a highly token-efficient, context-aware memory runtime inspired by Letta (OS-style paging) and Mem0 (Graph entity extraction).

## 1. The Triple-Layer Stack

The memory system is divided into three functional tiers managed locally via SQLite (`memory.db`) and orchestrated by `bin/memory_agent.py`.

### Layer 1: Core Memory (RAM)
*   **Concept:** The immediate context block that lives inside the LLM's active prompt.
*   **Function:** Holds the agent persona, current constraints, and active `conductor` track state.
*   **Management:** Handled via `@skill-episodic-memory`. The agent autonomously decides when to page dense information out to save tokens, and when to page relevant history back in.

### Layer 2: Recall Memory (Disk)
*   **Concept:** Traditional fuzzy semantic history and interaction logs.
*   **Function:** A highly indexed ledger of all agent-user interactions and atomic insights.
*   **Management:** Handled via `@skill-always-on-memory`. Searched via simple keywords to quickly retrieve past architectural decisions before making new ones.

### Layer 3: Graph Memory (Relational)
*   **Concept:** Temporal Knowledge Graph.
*   **Function:** Extracts relationships from conversations rather than just text chunks. Enables multi-hop reasoning (e.g., `<Authentication> requires <OTLP Port Determinism>`).
*   **Management:** Handled via `@skill-graph-memory`. Automatically populated during the consolidation phase.

---

## 2. The Cognitive Loop

The Memory Agent operates on a strict three-phase loop: **INGEST → PAGE & LOG → CONSOLIDATE**.

### Phase A: INGEST (Session Start)
Triggered by the `session_start.json` lifecycle hook (`python3 bin/memory_agent.py start <session_id>`).
1. Core Memory is loaded into the prompt.
2. The agent queries Recall Memory for any immediate prior context relevant to the task domain.

### Phase B: PAGE & LOG (Task Execution)
During the active session:
1. Every interaction is tracked (`add-interaction`).
2. If the context window gets bloated, the agent invokes Episodic Memory rules to page out dense text and retain only summaries.

### Phase C: CONSOLIDATE (Session End)
Triggered by the `post_task.json` lifecycle hook (`python3 bin/memory_agent.py complete <session_id>`).
1. Ephemeral Core Memory is flushed and persisted to Disk.
2. Graph extraction runs: the system parses the interaction logs and extracts new atomic triples (Entity → Relationship → Entity).
3. The session is closed safely.

---

## 3. Structural Topology (`memory.db`)

The SQLite store is optimized for the Triple-Layer stack with five primary tables:

| Table | Layer | Purpose |
|---|---|---|
| `sessions` | System | Task/session boundaries |
| `interactions` | Recall | Exact user-agent dialogue strings |
| `insights` | Recall | High-signal, distilled architectural lessons |
| `entities` | Graph | Extracted knowledge nodes |
| `relationships`| Graph | The relational edges connecting nodes |

This architecture ensures zero amnesia while mathematically minimizing LLM token consumption across long-horizon multi-agent workflows.
