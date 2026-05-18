#  Agentic-Project-Factory

This repository is the **Master Factory** for building standalone code repositories. It provides the high-performance infrastructure, expert AI agents, and manufacturing workflows required to create and stabilize independent technical products.

###  Factory Remote
- **GitHub**: [https://github.com/rb1whitney/Agentic-Project-Factory](https://github.com/rb1whitney/Agentic-Project-Factory)
- **Status**: **Private**

###  Factory Floor (Root)
- **`agents/` & `skills/`**: The master tools used by factory workers (the AI swarm) to construct products.
- **`bin/`**: Factory maintenance scripts and setup engines.
- **`conductor/`**: The **Production Ledger**, tracking the manufacturing queue of each product.
- **`bin/nexus.py`**: The **Swarm Nexus** engine. Synchronizes agents and skills across Claude, Gemini, and Copilot.

###  Standalone Products (`projects/`)
The outputs of the factory. Each project in this directory is a **Standalone Product**.
- **Zero Factory Trace**: Finished products contain no dependencies on the root factory.
- **Self-Governing**: Each product carries its own internal agentic manuals, setup engines, and conductor tracks.
- **Independent Remote**: Projects (e.g., `nit-fabric`) maintain their own private GitHub repositories.
