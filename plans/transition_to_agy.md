# Transition to Antigravity 2.0 (agy) Standards

This implementation plan details the updates to configuration, policy, and synchronization scripts to support the migration from Gemini CLI and Code Assist to the Antigravity 2.0 CLI (agy).

## Proposed Changes

### Core Configuration and Policies

#### [MODIFY] [manifest.json](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/.agent/manifest.json)
- Add `"antigravity-*"` to the list of supported engines.

#### [MODIFY] [safety.toml](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/.agent/policies/safety.toml)
- Update comments to refer to "Antigravity CLI" instead of "Gemini CLI".

### Synchronization Engine

#### [MODIFY] [nexus.py](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/bin/nexus.py)
- Expand `LOCAL_AGENT_SPOKES` and `LOCAL_SKILL_SPOKES` to include `.antigravitycli/` and `.agents/` subdirectories.
- Expand `GLOBAL_SPOKES` to include `~/.gemini/antigravity-cli` and `~/.antigravitycli`.
- Strip emojis from all logging print statements to prevent violation of output safety guardrails.

### Repository Bootstrapper

#### [MODIFY] [setup.sh](file:///mnt/d/OneDrive/Email_attachments/Programming-Work/bin/setup.sh)
- Update step 5 from "Gemini CLI" to "Antigravity CLI". Check for the presence of the `agy` binary and output instructions to install it from `https://antigravity.google`.
- Update the policy audit check to verify the existence of `$REPO_ROOT/.agent/policies/governance.toml` instead of the legacy non-existent path `$REPO_ROOT/.gemini/policies/swarm_policy.toml`.
- Update authentication setup instructions at the end to reference `agy` instead of `gemini`.

## Verification Plan

### Automated Tests
- Execute `python3 bin/nexus.py` to confirm the symlink mappings execute successfully without generating any warnings or errors.
- Run `bash bin/setup.sh` (or check its syntax via `bash -n`) to ensure the updated script is syntactically sound and reports correctly.

### Manual Verification
- Verify that standard files (like `AGENTS.md` and skills) are linked to the new local and global spokes.
