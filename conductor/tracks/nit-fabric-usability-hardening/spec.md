# SPEC: nit-fabric Usability & Portability Hardening (v0.11.0)

## 1. Problem Statement
The current `nit-fabric` implementation is tightly coupled to the **Agentic Project Factory** directory structure and lacks operational robustness. Hardcoded paths in the CLI, silent discovery failures, and non-standard dependency management hinder its utility as a standalone "industrial" connectivity engine.

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
