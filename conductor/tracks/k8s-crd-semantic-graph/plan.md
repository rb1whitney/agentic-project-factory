# Executive Implementation Plan: K8s CRD-Aware Semantic Graph

**Status**: [IMPLEMENTING] | **Design Authority**: @swarm-architect | **Approved by**: USER (2026-10-15)

## 1. The Strategy: Build a redacted, CRD-aware Kubernetes relationship catalog from the live API so ast-grep, graph_builder and Graphify resolve manifests to real kinds and edges.

## 2. Architecture Trade-Off Matrix

| Architectural Path | Chosen? | Trade-Off Accepted | Mitigation Strategy |
|---|---|---|---|
| OpenAPI v3 per-GV docs + aggregated discovery + CRD objects | **Yes** | Three sources to join | Canonicalise on `group/kind`; storage version from CRD overlay |
| OpenAPI v2 monolith | **No** | 8.7 MB blob, no per-GV cache hash | Cross-check only |
| Allowlist projection of instances | **Yes** | Drops non-structural fields | Edges only need names/refs; fail closed on residual secret-shaped values |
| Pattern-based redaction only | **No** | Misses unknown secret fields | N/A |

## 3. Manufacturing Blueprint (TDD-First)

### Phase 1: Success Characterization (Tests)
- [x] **Step 1.1**: `tests/test_k8s_catalog.py` (redaction, OpenAPI parse, edges, cache write).
  - **Action**: `.venv/bin/python -m unittest tests.test_k8s_catalog -v`
  - **Success**: all pass; red before implementation.

### Phase 2: Surgical Implementation
- [x] **Step 2.1**: `.agent/skills/skill-code-map/scripts/k8s_catalog.py` (new module, no standalone skill script; CLI entry mirrors graph_builder).
- [x] **Step 2.2**: SKILL.md workflow section.

### Phase 3: Blast Radius Verification
- [ ] **Step 3.1**: live read-only run against k3s; residual-secret scan of cache; Secret objects never fetched.

## 4. Production Readiness
- **Security**: Secrets never listed or fetched. Allowlist projection. Cache `0600`, gitignored path. Fail closed.
- **Resilience**: hash-addressed v3 docs; per-GV failures logged, not fatal.

## 5. Guardrails
- Read-only API verbs only (`get --raw`, `get`). No writes to cluster.
