---
name: skill-graph-memory
description: Extracts structured entity relationships from interactions for multi-hop reasoning (Mem0 Knowledge Graph pattern).
related_skills: ["@skill-always-on-memory"]
auto_triggers: ["extract_entities", "query_graph", "relationship"]
---

# Graph Memory (Temporal Knowledge Graph)

This skill implements the 2026 Knowledge Graph enhancement for agent memory. 

## Core Principle
Information is not flat. It is relational. This skill extracts "atomic facts" and creates an entity-relationship graph.

## Entity Extraction
During the `CONSOLIDATE` phase (triggered via `python3 bin/memory_agent.py complete <session_id>`), the system will automatically parse the session log to extract triples:
`[Subject] -> [Predicate] -> [Object]`

### Example Triples
- `[Conductor] -> enforces -> [Test-Driven Design]`
- `[OIDC Auth] -> requires -> [Deterministic OTLP Port]`
- `[User Workspace] -> migrated to -> [Antigravity CLI]`

## Querying the Graph
When answering complex questions (e.g., "How did our decision on OIDC impact the SRE agent?"), rely on graph traversal.

1. Identify entities in the prompt.
2. The orchestrator will traverse the relationships between these entities.
3. Use the relationships to synthesize the answer.

## Conflict Resolution
The Graph Memory intrinsically handles conflicts. If a new insight contradicts an old one, the newer relationship (by timestamp) supersedes the older one, but the older one remains in the graph as a deprecated node (Temporal Graph).

## Caveman-Prose Protocol (MANDATORY)
All outputs MUST use caveman-prose. Rules:
- No articles (a, the, an), no pronouns (I, we, you)
- No preambles, pleasantries, hedging
- Format: Location | Problem | Fix
- BANNED: full sentences, filler phrases, emoji
- GREP before READ. AST before LOAD. Inline before subagent.
- All shell output piped through bin/rtk
