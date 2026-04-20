#  The Product Factory

This repository is a **Factory** repo to build standalone code repositories. It provides the high-performance infrastructure, master expert agents, and construction workflows required to build and stabilize standalone technical products.

###  Factory Floor (Root)
- **`agents/` & `skills/`**: The master tools used by factory workers (the AI swarm) to construct products.
- **`bin/`**: Factory maintenance scripts and setup engines.
- **`conductor/`**: The **Production Ledger**, tracking the manufacturing queue of each product.

###  Standalone Products (`projects/`)
The outputs of the factory. Each project in this directory should be a **Standalone Product**.
- **Zero Factory Trace**: Finished products contain no dependencies on the root factory.
- **Self-Governing**: Each product carries its own internal agentic manuals, setup engines, and conductor tracks.
