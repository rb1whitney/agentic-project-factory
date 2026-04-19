# 00_MASTER_ROADMAP.md: Project Baker (AI-Native Globalizer)

## 1. Project Vision
Project Baker is an AI-native transition engine that automates the migration of U.S.-focused microservices to a global, multi-region architecture. It focuses on identifying "i18n smells" and scaffolding regional-parity infrastructure.

## 2. Core Protocol: @conductor-expert CDD
All development follows the **Context-Driven Development (CDD)** protocol defined in `conductor/workflow.md`.
- **Strategic Discovery**: Map architecture and generate a Global Research Report. (Completed: `plans/research/global_research_report.md`)
- **Tactical Planning**: Create detailed track-level plans (`plans/PHASE_X_PLAN.md`) before implementation.
- **Execution Loop**: TDD-first implementation, auditor verification, and human-gated git commits.

## 3. Campaigns

### 🎯 Campaign 1: CLI Foundation (`baker-recon`)
- **Status**: **Active**
- **Objective**: Build the `baker-recon` CLI (Python/Typer) to audit and flag "i18n smells" (hardcoded locales, date formats, currencies).
- **Target**: `projects/project-baker/`
- **Key Milestones**:
    - CLI environment setup and dependency management.
    - Implementation of file crawlers for hardcoded string detection.
    - Integration with `Rich` for enhanced console reporting.

### 🎯 Campaign 2: AI Refactoring Engine
- **Status**: **Pending**
- **Objective**: Implement agentic generation of `messages.properties` and automated string replacement using Gemini Pro 1.5.
- **Target**: `projects/cloud-boot-app/`
- **Key Milestones**:
    - Prompt engineering for i18n extraction.
    - AST-based string replacement in Java/Kotlin.
    - Validation suite for refactored localized keys.

### 🎯 Campaign 3: Infrastructure Scaffolding (Regional Parity)
- **Status**: **Pending**
- **Objective**: Standardize multi-region infrastructure with Terraform modules for `us-east-1` and `eu-west-1` parity.
- **Target**: `projects/managed-cloud-infra/`
- **Key Milestones**:
    - Base VPC and RDS/Aurora Global Database modules.
    - Regional compliance divergence (e.g., EU-specific data residency rules).
    - Multi-region deployment workflow in CI/CD.

## 4. Current State
- **Active Campaign**: Campaign 1 (CLI Foundation)
- **Last Updated**: 2024-05-24
- **Next Step**: `@swarm-architect` to create detailed tasks for Campaign 1 in `plans/PHASE_1_CLI_FOUNDATION_PLAN.md`.

---
**Protocol Guardian**: @swarm-supervisor
**Strategic Designer**: @swarm-architect
