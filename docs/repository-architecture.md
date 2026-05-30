# Repository Architecture: Strategic System Design (2026)

## Executive Summary: The Hub-and-Spoke Governance Model
This repository implements a **Physical Sovereignty Hub** grounded in the **ACS-2026 Agentic Collaboration Standard**. By centralizing all cognitive logic, operational skills, and governance policies within the `.agent/` directory, we eliminate "Configuration Fragmentation" and ensure 100% deterministic behavior across heterogeneous IDE environments (Claude, Gemini, Copilot).

## 1. The Infrastructure Layer Cake

The system is architected to isolate systemic risk while maximizing capability reuse.

```mermaid
graph TD
    Root[Repository Root]
    Root --> Hub[".agent/ Hub — Unified Governance"]
    Root --> Docs["docs/ — Architectural Library"]
    Root --> MCP["mcp-servers/ — Service Mesh"]
    Root --> Bin["bin/ — Core Engine Primitives"]

    Hub --> Agents["agents/ — Specialist Swarm Personas"]
    Hub --> Skills["skills/ — Atomic Industrial Modules"]
    Hub --> Policies["policies/ — Risk Management Shield"]
    Hub --> Manifest["manifest.json — Orchestration Registry"]

    subgraph "Cognitive Tier"
        Agents --- Manuals["Specialist Operational Manuals"]
    end

    subgraph "Capabilities Tier"
        Skills --- ExpertFunctions["High-Precision Task Modules"]
    end

    subgraph "Governance Tier"
        Policies --- LethalTrifecta["Safety | Privacy | Governance Shield"]
    end
```

## 2. Tiered Context Gating (Blast Radius Management)

To maintain sub-50ms context retrieval and minimize token expenditure (SLO: 90% reduction), context is ingested via a three-tier "On-Demand" protocol.

```mermaid
flowchart LR
    Tier1["Tier-1: Discovery (Names/Metadata)"] --> |Domain Match| Tier2["Tier-2: Logic (Full Manifests)"]
    Tier2 --> |Execution Match| Tier3["Tier-3: Deep Reference (Docs/Logs)"]

    subgraph "Tier-1 (Discovery Gating)"
        T1A[".agent/agents/"]
        T1B[".agent/skills/"]
    end

    subgraph "Tier-2 (Operational Gating)"
        T2A["SYSTEM.md"]
        T2B["SKILL.md"]
    end

    subgraph "Tier-3 (Historical Gating)"
        T3A["Technical Specifications"]
        T3B["Archival Lifecycle Logs"]
    end
```

## 3. Zero-Trust Security & Identity Injection

Identity and credentials are never persisted within the repository. We leverage a **Secure Proxy Injection** pattern using localized Vault drivers (`gopass`, `rbw`) and the MCP service mesh.

```mermaid
sequenceDiagram
    participant Agent as Active Specialist Swarm
    participant Proxy as bin/rtk & mcp_wrapper.sh
    participant Vault as Local Sovereignty Vault
    participant Cloud as Cloud Provider (GCP/AWS)

    Agent->>Proxy: Initiates Privileged Tool Call
    Proxy->>Vault: Dynamic Identity Lookup
    Vault-->>Proxy: Ephemeral Token Injection
    Proxy->>Cloud: Authenticated Operational Execution
    Cloud-->>Proxy: Results Returned
    Proxy-->>Agent: Token-Optimized Response
```