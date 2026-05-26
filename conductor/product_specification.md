#Product Specification: The Standalone Standard

This document defines the **Product Integrity Mandate** for every standalone entity manufactured by **TheProduct Factory**.

##  Mandatory Integrity Pillars

### 1. Absolute Standalone Autonomy (Zero-Zero Decoupling)
- **Standard**: A product must contain **Zero** relative parent-directory escapes (`../../`).
- **Standard**: A product must have **Zero** dependency on root-level factory scripts (`bin/nexus.py`, `skills/`).
- **Standard**: The product must remain 100% operational if moved to a completely isolated filesystem.

### 2. Internalized Cognition (Agentic Native)
- **Standard**: The product must carry its own physical agentic platform folders (`.gemini/`, `.claude/`, etc.).
- **Standard**: The product must contain a local [**`AGENT.md`**](file://./AGENT.md) for immediate specialist discovery.

### 3. High-resolution Infrastructure
- **Standard**: Minimal **90% Unit Test Coverage** enforced by internal verification skills.
- **Standard**: Codified environment management using **`uv`**.
- **Standard**: Standalone bootstrap engine in [**`bin/setup.sh`**](file://./bin/setup.sh).

### 4. Self-Governing Orchestration
- **Standard**: The product must manage its own internal [**`conductor/tracks.md`**](file://./conductor/tracks.md), tracking its evolution independently of the factory floor.

##  Quality Assurance
Any product failing these standards is restricted within the **Manufacturing** or **Testing** phases and cannot be certified as **Shipped**.

./Specification: FACTORY-STANDARD-V1 | Quality Control: ENFORCED*