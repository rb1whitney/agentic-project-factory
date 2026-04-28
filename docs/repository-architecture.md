# Repository Architecture: THE Agent Swarm (2026)

This document defines the high-precision, "Unified Hub" structure of the repository, grounded in the **April 2026 Agentic Collaboration Standard (ACS)**.

## The Infrastructure Layer Cake

The repository is organized around the `.agent/` hub, which consolidates cognitive, operational, and governance layers into a single Physical Sovereignty point.

```mermaid
graph TD
    Root[Repository Root]
    Root --> Hub[.agent/]
    Root --> Docs[docs/]
    Root --> MCP[mcp-servers/]
    Root --> Bin[bin/]

    Hub --> Agents[agents/]
    Hub --> Skills[skills/]
    Hub --> Policies[policies/]
    Hub --> Manifest[manifest.json]

    subgraph "Cognitive Layer"
        Agents --- Manuals[Specialist Personas]
    end

    subgraph "Capabilities Layer"
        Skills --- ExpertFunctions[Atomic Skills]
    end

    subgraph "Governance Layer"
        Policies --- LethalTrifecta[Safety/Privacy/Resource]
    end
```

## Tiered Context Loading (ACS v1.2.0)

To maintain performance and security, context is ingested in three distinct tiers as defined in `acs.yaml`.

```mermaid
flowchart LR
    Tier1[Tier-1: Discovery] --> |Intent Match| Tier2[Tier-2: Logic]
    Tier2 --> |Specific Request| Tier3[Tier-3: Deep Context]

    subgraph "Tier-1 (Names Only)"
        T1A[.agent/agents/]
        T1B[.agent/skills/]
    end

    subgraph "Tier-2 (On-Demand)"
        T2A[SYSTEM.md]
        T2B[SKILL.md]
    end

    subgraph "Tier-3 (Reference Only)"
        T3A[Technical Specs]
        T3B[Historical Logs]
    end
```

##  Zero-Trust Credential Flow

Secrets never touch the repository. They are dynamically injected at runtime via the secure MCP wrapper.

```mermaid
sequenceDiagram
    participant Agent as Specialist Agent
    participant Wrapper as mcp_wrapper.sh
    participant Vault as Vault (gopass/rbw)
    participant Server as MCP Server

    Agent->>Wrapper: Executes Server via Wrapper
    Wrapper->>Vault: Query Secret (GITHUB_TOKEN)
    Vault-->>Wrapper: Encrypted Token
    Wrapper->>Server: exec(Server, ENV={TOKEN})
    Server->>Cloud: Authenticated API Request
```