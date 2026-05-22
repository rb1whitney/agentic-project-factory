# SPEC: nit-fabric Usability & Portability Hardening (v0.11.0)

## 1. Problem Statement
The current `nit-fabric` implementation is tightly coupled to the **Agentic Project Factory** directory structure and lacks operational robustness. Hardcoded paths in the CLI, silent discovery failures, and non-standard dependency management hinder its utility as a standalone "industrial" connectivity engine.

## Reference Sources
*   **Modern Python Packaging**: [PEP 517 – A build-backend API for source trees](https://peps.python.org/pep-0517/) and [PEP 518 – Specifying build system requirements](https://peps.python.org/pep-0518/)
*   **Routing & Connectivity Protocols**: [RFC 4271 - A Border Gateway Protocol 4 (BGP-4)](https://datatracker.ietf.org/doc/html/rfc4271) and Radix Trie standard algorithms.

## 2. Goals
- **Decoupling**: Remove all hardcoded path assumptions relative to the factory root.
- **Robustness**: Implement pre-flight checks for CLI dependencies and authentication.
- **Portability**: Standardize packaging using `pyproject.toml` and entry points.
- **Configurability**: Introduce a YAML-based configuration system for project defaults.
- **UX**: Unify artifact management and improve error visibility.

## 3. Success Criteria
- `nit-fabric` can be executed from any directory after installation.
- Failed CLI commands during discovery trigger explicit user alerts.
- A `nit-fabric.yaml` file successfully overrides default CLI flags.
- All tests pass with 100% coverage on the new path-agnostic logic.
