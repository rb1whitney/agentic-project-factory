# Feature Implementation Plan: Campaign 1 - CLI Foundation (baker-recon)

## 🔍 Analysis & Context
*   **Objective**: Build the `baker-recon` CLI (Python/Typer) to audit and flag "i18n smells" (hardcoded locales, date formats, currencies) in target codebases.
*   **Affected Files**:
    - `projects/project-baker/main.py` (New)
    - `projects/project-baker/requirements.txt` (New)
    - `projects/project-baker/tests/test_recon.py` (New)
*   **Key Dependencies**: `typer`, `rich`, `pytest`.
*   **Risks/Edge Cases**: 
    - False positives in regex-based string detection (e.g., logging statements, internal IDs).
    - Handling various file encodings and large directory structures efficiently.

## 📋 Micro-Step Checklist
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

## 📝 Step-by-Step Implementation Details

### Prerequisites
- Python 3.11+ environment.

#### Phase 1: Environment & Project Setup
1.  **Step 1.A (Requirements):** Define the base dependencies.
    *   *Target File:* `projects/project-baker/requirements.txt`
    *   *Content:* `typer`, `rich`, `pytest`.
2.  **Step 1.B (CLI Entry Point):** Create the base CLI structure.
    *   *Target File:* `projects/project-baker/main.py`
    *   *Exact Change:* Implement a Typer app with a `scan` command that accepts a path argument.

#### Phase 2: Core Recon Engine (Logic)
1.  **Step 2.A (The Unit Test Harness):** Define the verification requirement.
    *   *Target File:* `projects/project-baker/tests/test_recon.py`
    *   *Test Cases to Write:* 
        - `test_find_hardcoded_string`: Assert regex identifies `"Hello World"`.
        - `test_find_currency_symbol`: Assert regex identifies `$100.00`.
        - `test_ignore_internal_keys`: Assert regex ignores `KEY_HELLO_WORLD`.
2.  **Step 2.B (The Implementation):** Implement the scanning logic.
    *   *Target File:* `projects/project-baker/main.py`
    *   *Exact Change:* 
        - Add a `find_smells(file_path)` function.
        - Use regex to identify string literals and currency/date patterns.
        - Implement recursive directory traversal in the `scan` command.
3.  **Step 2.C (The Verification):** Verify the harness.
    *   *Action:* Run `pytest projects/project-baker/tests/`.
    *   *Success:* All tests pass.

#### Phase 3: Enhanced Reporting (UI)
1.  **Step 3.A (Rich Integration):** Colorize the output.
    *   *Target File:* `projects/project-baker/main.py`
    *   *Action:* Use `rich.table.Table` to display results (File, Line, Type, Content).
2.  **Step 3.B (JSON Output):** Add export functionality.
    *   *Action:* Add a `--json` flag to the `scan` command to output a parseable report.

### 🧪 Global Testing Strategy
*   **Unit Tests**: Focus on regex accuracy and file discovery logic.
*   **Integration Tests**: Run `python projects/project-baker/main.py scan projects/cloud-boot-app/` and verify the report matches expectations.

## 🎯 Success Criteria
- [ ] `baker-recon scan` identifies hardcoded strings in a sample Java file.
- [ ] Output is clearly formatted in a Rich table.
- [ ] Tool passes all unit tests in the `tests/` directory.

---
**🛑 STOP: HUMAN REVIEW GATE**
Please review this plan. Type 'approve' to proceed to execution.
