# Agent Hub Standard: The Sovereign Architecture (2026)

## Executive Summary
The **Agent Hub Standard (ACS-2026)** defines the high-precision architectural framework for the `.agent/` sovereignty layer. This specification ensures a **Single Source of Truth** for AI orchestration, mitigating systemic risk and configuration drift across heterogeneous platform ecosystems (Google Antigravity, Claude Code, GitHub Copilot).

## 1. The Unified Manifest (v1.8.0): Deterministic Identity
The `.agent/manifest.json` serves as the **Master Identity Controller**. It defines the runtime boundary, capability surface area, and provider-specific permission tiers.

- **`schema_version`**: v1.8.0 Compliance.
- **`standard`**: ACS-2026 Multi-Platform Orchestration.
- **`permissions`**: Granular opt-in/opt-out schemas for privileged operations.

## 2. Tiered Context Loading: Blast Radius & Cost Containment
To maintain sub-second cognitive response times and minimize token-level operational expenditure, the hub enforces a **Three-Tier Gating Strategy** (v1.2.0).

| Tier | Strategic Intent | Ingestion Protocol |
| :--- | :--- | :--- |
| **Tier-1: Discovery** | Role & Skill Identification | Metadata-Only (Zero Bloat) |
| **Tier-2: Logic** | Functional Prompt Ingestion | Intent-Matched (On-Demand) |
| **Tier-3: Reference** | Historical & Spec Context | Read-Only (Deferred) |

## 3. Physical Sovereignty: Immutable Truth
The **April 2026 Shift** established the `.agent/` directory as the **Physical Sovereignty Layer**.
- **Governance Isolation**: Core logic resides outside the agent's destructive boundary, preventing "Self-Sabotage" feedback loops.
- **Polyfill Portability**: IDE-native configuration endpoints (e.g., `.cursorrules`, `.gemini/`) are implemented as symlink polyfills pointing back to the sovereign hub.

## 4. The Risk Management Shield (Lethal Trifecta)
Systemic risk is managed via deterministic policies located in `.agent/policies/`:
1. **`safety.toml`**: Governs network egress and restricts destructive system calls to a manual-approval workflow.
2. **`privacy.toml`**: Implements **Data Sovereignty** by redacting PII and sensitive credentials from the context window.
3. **`governance.toml`**: Manages resource-intensive operations and cross-agent concurrency.

## 5. Industrial Performance Tuning (2026)
Optimized for high-concurrency production environments:
- **Google Antigravity**: Primary engine utilizes Gemini 3.1 Pro with native **Thinking Blocks** and low-latency API endpoints.
- **Anthropic Ecosystem**: Leverages Claude 4.6 via **Deterministic Event Channels** for complex reasoning tasks.
- **Edge Resilience**: Localized triage using **Nano Banana Pro 2** for offline file parsing and preliminary data reduction.

## 6. Deterministic Lifecycle Hooks
Precision orchestration is achieved through JSON-defined hooks in `.agent/hooks/`, ensuring that critical tasks (Symbol Map generation, Policy Verification, Documentation Updates) are automated and non-negotiable.

---
*Last Updated: April 2026*
