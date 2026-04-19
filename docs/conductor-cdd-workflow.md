# Conductor: CONTEXT-DRIVEN DEVELOPMENT (CDD)

This document visualizes the strict **Spec-Plan-Implement** lifecycle used to ensure zero information loss and autonomous project management.

## 🔄 The Conductor Loop

Every track follows a deterministic state-machine cycle led by the [**swarm-supervisor**](file://../../agents/swarm-supervisor/SYSTEM.md).

```mermaid
stateDiagram-v2
    [*] --> Discovery: Strategic Inquiry
    Discovery --> Spec: Define 'What' & 'Why'
    Spec --> Plan: Define 'How' (Tasks)
    Plan --> UserGate: Human Approval Required
    UserGate --> Implement: /conductor:implement
    Implement --> TDD: Write Test -> Fail -> Pass
    TDD --> Implement
    Implement --> Verification: Phase Audit
    Verification --> Sync: Update Context (product.md)
    Sync --> [*]
```

## 📂 The CDD Folder Structure

Tracks are organized into nested folders to maintain isolation and history.

```mermaid
graph LR
    Tracks[conductor/tracks/]
    Tracks --> ProjectA[project-alpha/]
    ProjectA --> SpecA[spec.md]
    ProjectA --> PlanA[plan.md]
    ProjectA --> Artifacts[artifacts/]

    Tracks --> ProjectB[project-beta/]
    ProjectB --> SpecB[spec.md]
    ProjectB --> PlanB[plan.md]
```

---
*Maintained by the Swarm Supervisor — Status: HARDENED.*
