# Specification: Project Baker (Globalizer Hub)

**Status**: [MODERNIZING] | **Strategic Intent**: Multi-Region Infrastructure Sovereignty

## 1. Executive Summary
Project Baker is an AI-native transition engine that automates the migration of U.S.-focused microservices to a global, multi-region architecture. It focuses on identifying "i18n smells" and scaffolding regional-parity infrastructure.

## 2. Core Protocol: Conductor CDD
All development follows the **Context-Driven Development (CDD)** protocol defined in `conductor/workflow.md`.
- **Strategic Discovery**: Map architecture and generate a Global Research Report.
- **Tactical Planning**: Create detailed track-level plans before implementation.
- **Execution Loop**: TDD-first implementation, auditor verification, and human-gated git commits.

## 3. Campaigns

### Campaign 1: CLI Foundation (baker-recon)
- **Status**: [ACTIVE]
- **Strategic Goal**: Build the `baker-recon` CLI to audit and flag "i18n smells" (hardcoded locales, date formats, currencies).
- **Target**: `projects/project-baker/`

### Campaign 2: AI Refactoring Engine
- **Status**: [PENDING]
- **Strategic Goal**: Implement agentic generation of `messages.properties` and automated string replacement using Gemini Pro.
- **Target**: `projects/cloud-boot-app/`

### Campaign 3: Infrastructure Scaffolding (Regional Parity)
- **Status**: [PENDING]
- **Strategic Goal**: Standardize multi-region infrastructure with Terraform modules for `us-east-1` and `eu-west-1` parity.
- **Target**: `projects/managed-cloud-infra/`
