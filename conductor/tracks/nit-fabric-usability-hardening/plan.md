# PLAN: nit-fabric Usability & Portability Hardening

## Phase 1: Structural Decoupling & Packaging
- [x] **Task 1**: Implement `pyproject.toml` to define the `nit-fabric` project and its dependencies.
- [x] **Task 2**: Refactor `bin/nit-fabric` to use `importlib.resources` or relative path discovery instead of hardcoded strings.
- [x] **Task 3**: Establish a `nit_fabric` python package structure (move logic from `bin/` to `nit_fabric/` if necessary).

## Phase 2: Operational Robustness
- [x] **Task 1**: Implement a `PreFlightChecker` to verify `aws` and `gcloud` CLIs and auth status.
- [x] **Task 2**: Update `discover.py` to raise explicit exceptions on CLI failures instead of swallowing them.
- [x] **Task 3**: Add `--mode live` as the default with a required `--mock` override for safety.

## Phase 3: Configuration & Artifact Management
- [x] **Task 1**: Implement `config.py` to load settings from `nit-fabric.yaml`.
- [x] **Task 2**: Standardize all outputs to an `out/` directory within the project root.
- [x] **Task 3**: Update `README.md` with the new standalone installation and usage instructions.

## Phase 4: Validation
- [x] **Task 1**: Update existing tests to reflect path-agnostic logic.
- [x] **Task 2**: Perform manual verification of standalone execution (`pip install -e .`).

