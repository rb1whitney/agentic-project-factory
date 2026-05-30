# Implementation Plan: Campaign 1 - CLI Foundation (baker-recon)

**Status**: [IN-PROGRESS] | **Strategic Goal**: CLI Foundation for Regionalization

## 1. Analysis & Context
*   **Objective**: Build the `baker-recon` CLI (Python/Typer) to audit and flag "i18n smells" in target codebases.
*   **Affected Files**:
    - `projects/project-baker/main.py`
    - `projects/project-baker/requirements.txt`
    - `projects/project-baker/tests/test_recon.py`
*   **Key Dependencies**: `typer`, `rich`, `pytest`.

## 2. Architecture Trade-Off Matrix

| Architectural Path | Chosen? | Trade-Off Accepted | Mitigation Strategy |
|---|---|---|---|
| **Python/Typer** | **Yes** | Performance overhead compared to Go/Rust. | Acceptable for audit-time CLI; prioritized developer velocity. |
| **Regex Detection** | **Yes** | Potential for false positives. | Characterize behavior with comprehensive unit test suite. |

## 3. Micro-Step Checklist
- [ ] Phase 1: Environment & Project Setup
  - [ ] Step 1.A: Define `requirements.txt` and project structure.
  - [ ] Step 1.B: Create a baseline `main.py` with Typer commands.
- [ ] Phase 2: Core Recon Engine (Logic)
  - [ ] Step 2.A: Implement `Characterize Behavior` (Unit Test Harness).
  - [ ] Step 2.B: Implement directory crawler and regex-based "i18n smell" detection.
  - [ ] Step 2.C: Verify against unit tests.
- [ ] Phase 3: Enhanced Reporting (UI)
  - [ ] Step 3.A: Integrate `Rich` for colorized, tabular console output.
  - [ ] Step 3.B: Implement JSON export for integration with Phase 2.

## 4. Production Readiness & Day-Two Operations
- **Observability**: Table-based reporting via `Rich`.
- **Validation**: Strict TDD loop with 100% coverage on core detection logic.
