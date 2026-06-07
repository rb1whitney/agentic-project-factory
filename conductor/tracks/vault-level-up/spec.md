# Specification: Vault Level Up (OpenBao / OSS)

## What
Modernize and migrate HashiCorp Vault management scripts and documentation from the legacy `old/` directory to a new, standalone project structure at `projects/vault/`. This must strictly target Vault Open Source (OpenBao) capabilities. All Vault Enterprise features (such as DR and performance replication) MUST be omitted.

## Why
The current `old/` directory is a monolith lacking testing and modularity. Migrating to `projects/vault/` aligns with the Zero-Zero Decoupling mandate. Focusing strictly on OpenBao ensures the project is not tied to paid enterprise licensing and can run in OSS environments.
