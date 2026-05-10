# Workspace Context Manager

This skill helps Gemini CLI correctly handle GitHub authentication and Python virtual environments for the `rb1whitney` workspace.

## 1. GitHub Repository Access

The user uses a **Fine-Grained Personal Access Token (PAT)** which has limitations for collaborator repositories.

### Access Rules:
- **Personal Repositories (`rb1whitney/*`):** Use the GitHub CLI (`gh`) and the PAT token.
- **Collaborator Private Repositories (e.g., `jamesoundb/*`):** Use SSH with the key `~/.ssh/id_ed25519_rb1whitney`.
- **Clone Example:** `GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_rb1whitney" git clone git@github.com:owner/repo.git`

## 2. Python Virtual Environment (venv)

This project uses a dedicated virtual environment located in the `./python-code-mapper` directory.

### Execution Rules:
- **All Python commands** MUST be executed using the absolute path to the virtual environment's interpreter.
- **Python Interpreter:** `./python-code-mapper/bin/python3`
- **Pip Commands:** `./python-code-mapper/bin/pip`
- **DO NOT** use the system-level `python3` or `pip` directly.
- **Activation:** While you can run commands directly via the binary path, ensure all dependencies (like `tree-sitter-languages`) are installed within this venv.

### Maintenance:
- If a dependency is missing, install it using: `./python-code-mapper/bin/pip install -r requirements-code-mapper.txt`

## 3. Troubleshooting

- **GitHub 404:** If `gh repo view` fails for a collaborator repo, switch to the SSH protocol.
- **Python ModuleNotFoundError:** Verify the command is using the `./python-code-mapper/bin/python3` interpreter. Check if the module is installed in the venv using `./python-code-mapper/bin/pip list`.

./Author: Richard Whitney*