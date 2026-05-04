# Contributing to nit-fabric

We welcome contributions! Here’s how to get started:

## PR Requirements
1. **Tests**: All bug fixes and new features must include a test case in the `tests/` directory.
2. **Docs**: Update the relevant markdown files if you change core logic or add new policies.
3. **Linting**: Ensure your code follows standard Python PEP8 guidelines.

## Adding New Policies
You can add new security checks by:
1. Updating `bin/policies.yaml` with the rule definition.
2. If the logic is unique, adding a new class in `bin/policies.py`.
3. Adding a Jinja2 template in `bin/templates/` for remediation patches.