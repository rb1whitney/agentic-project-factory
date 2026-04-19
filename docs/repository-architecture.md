# Repository Architecture: THE ELITE SWARM

This document defines the high-precision, "Flat Expert" structure of the Programming-Work unified AI hub.

## 🏛️ The Infrastructure Layer Cake

The repository is organized into four core architectural pillars, each representing a specific layer of the swarm's cognitive and operational capabilities.

```mermaid
graph TD
    Root[Repository Root]
    Root --> Agents[agents/]
    Root --> Skills[skills/]
    Root --> MCP[mcp-servers/]
    Root --> Bin[bin/]

    subgraph "Cognitive Layer"
        Agents --- Manuals[Specialist Personas]
    end

    subgraph "Capabilities Layer"
        Skills --- ExpertFunctions[80+ Atomic Skills]
    end

    subgraph "Intelligence Layer"
        MCP --- GroundTruth[Real-Time Sensors]
    end

    subgraph "Operations Hub"
        Bin --- AST[ast-bridge/]
        Bin --- Setup[setup.sh]
        Bin --- Wrapper[mcp_wrapper.sh]
    end
```

## 🛡️ Zero-Trust Credential Flow

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

---
*Maintained by the Swarm Supervisor — Status: HARDENED.*
