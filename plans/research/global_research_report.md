# Global Research Report: Project Baker (AI-Native Globalizer)

## 1. Executive Summary
Project Baker is an AI-Native transition engine designed to automate the migration of U.S.-focused microservices to a global architecture. It focuses on identifying and refactoring "i18n smells" (hardcoded locales, date formats, currencies) and scaffolding multi-region infrastructure with Terraform.

## 2. Current Codebase State
- **Location**: `projects/project-baker/`
- **Files Found**: `README.md`, `ARCHITECTURE.md`, `IMPLEMENTATION.md`.
- **Status**: Planning & Specification phase. No functional Python CLI or Terraform modules yet.
- **Target Application**: `projects/cloud-boot-app/` (designated test case).

## 3. Architectural Mapping
- **Philosophy**: **Regional Parity** for the Application layer (standardized instances) vs. **Compliance Divergence** for the Infrastructure layer (e.g., EU-specific data residency).
- **Core Components**:
    - **GraphQL Federation**: To coordinate regional data fetchers.
    - **Centralized Messaging**: via Project Crumbs for cross-region synchronization.
- **Expert Consultations**:
    - **Architecture**: Use GraphQL Federation.
    - **SRE**: Canary-based refactoring (start with 10% of locale keys).
    - **Security**: Move PII to region-specific DB clusters; audit KMS key rotations.

## 4. Implementation Strategy
- **Phase 1 (Audit & Recon)**: Build `baker-recon` CLI (Python/Typer) to flag i18n smells.
- **Phase 2 (Autonomous Refactoring)**: Agentic generation of `messages.properties` and string replacement using Gemini Pro 1.5.
- **Phase 3 (Infrastructure)**: Terraform modules for `us-east-1` and `eu-west-1` parity.

## 5. Identified i18n Smells
- Hardcoded date formats.
- Currency symbols (specifically `$`).
- U.S.-specific static strings.

## 6. Technical Stack
- **CLI**: Python (Typer / Rich).
- **AI**: Gemini Pro 1.5 (Vertex AI).
- **IaC**: Terraform 1.6+.
- **Monitoring**: Datadog (regional tagging).
