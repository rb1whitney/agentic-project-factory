---
name: skill-platform-admin
description: Workspace specialist for SSH/PAT management, Python venvs, and platform-level onboarding.
---
# Skill: Runtime Tooling & Platform Administration (`skill-platform-admin`)

<!-- SAP_BUNDLE_START -->
> **SaP Substituted Bundle**: `invoke(...)` is structural pseudocode notation in this skill document, not an executable shell binary. Emit the concrete CLI/script commands in **Action Templates** first.

## 1. Action Templates (Concrete How — Read First)
```bash
# [κ: runtime-tooling-platform-ops] parent=skill-platform-admin required_inputs=['expert_name']
# Route: select runbook from the Reference & Script Routing Index in SKILL.md; read only the matched file
python3 -m unittest discover -s tests -p 'test_*.py' | bin/rtk
```

## 2. Procedural Skeleton (Where Calls Fit)
```text
PROCEDURE run_skill_platform_admin_workflow(expert_name):
  1. PRE-CHECK: Secrets sourced from gopass or ~/.mcp-servers/credentials; Sandbox execution verified
  2. result <- invoke(runtime-tooling-platform-ops, {expert_name: "<expert_name>"})
  3. POST-CHECK: Tooling endpoint or build artifact verified non-destructively
  4. RETURN {Location, Problem, Fix, outputs: ['skill_description', 'expert_capability']}
```

## 3. Inlined Child Contracts (Abstract Guarantees)
- **`κ: runtime-tooling-platform-ops`**
  - `trigger`: Expert skill name and description capability for runtime platform, MCP servers, OpenCode, Gemini CLI, MSBuild, and Frontend
  - `inputs`: required `['expert_name']`, optional `[]`
  - `outputs`: `['skill_description', 'expert_capability']`
  - `preconditions`: Secrets sourced from gopass or ~/.mcp-servers/credentials; Sandbox execution verified
  - `postconditions`: Tooling endpoint or build artifact verified non-destructively
  - `side_effects`: filesystem=local build/venv artifacts, network=local model/MCP healthcheck
<!-- SAP_BUNDLE_END -->

## Operating Protocol & Domain Guardrails

Execute expert skill name and description capability workflows for `expert_name` across runtime platform administration, MCP servers, OpenCode, Gemini CLI, and SDK tooling to produce `skill_description` and `expert_capability`.

### 1. Zero-Trust Credential & Environment Rules
- Source all credentials and PATs exclusively from `gopass`, `rbw`, or `~/.mcp-servers/credentials`; never hardcode secrets or prompt for plaintext passwords.
- Prefer repo `.venv/bin/python` for Python package/YAML tooling and `/usr/bin/python3` for `tree_sitter` AST scripts.
- Maintain symlink integrity across `.claude/`, `.agents/`, and `.codex/` via `bash bin/nexus.sh | bin/rtk`; never overwrite unmanaged raw files without warning the user.

### 2. Tooling & SDK Verification
- Verify CLI and SDK versions non-destructively before modifying workspace configurations:
  ```bash
  .venv/bin/python --version | bin/rtk
  /usr/bin/python3 -c "import tree_sitter; print('tree_sitter OK')" | bin/rtk
  bash bin/nexus.sh | bin/rtk
  ```

## Reference & Script Routing Index

| Platform Capability | Trigger / Scope | Reference Runbooks & Configs (`.agent/skills/skill-platform-admin/`) |
| :--- | :--- | :--- |
| **Workspace & Symlink Architecture** | Onboarding, venv setup, `AGENTS.md` & spoke symlink configuration | `references/workspace-context-manager.md`, `references/platform-onboarding.md`, `references/symlink-config.md`, `scripts/security.yaml` |
| **Cloud SDK & CLI Discovery** | Managing `gcloud`, `aws`, `kubectl`, `helm`, `gh`, and dynamic CLI schema discovery | `references/sdk-manager.md`, `references/cli-discovery.md`, `references/gemini-cli-abilities-summary.md` |
| **MCP Server Lifecycle** | Configuring, testing, and troubleshooting Model Context Protocol servers | `references/mcp-manager.md` |
| **AI Harnesses (OpenCode & Gemini CLI)** | Local model orchestration, provider routing, Gemini CLI & Antigravity setup | `references/opencode-manager.md`, `references/gemini-cli-expert.md` |
