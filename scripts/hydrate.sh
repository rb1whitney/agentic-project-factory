#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ "$TARGET" != "claude" && "$TARGET" != "antigravity" && "$TARGET" != "codex" && "$TARGET" != "all" && "$TARGET" != "models" ]]; then
  echo "Error: Unknown target '$TARGET' (expected: claude | antigravity | codex | all | models)" >&2
  exit 1
fi

# The first python3 on PATH (e.g. Homebrew) may lack the modules hydrate.py imports,
# so pick an interpreter by what it can import rather than by name.
PY=""
for candidate in "$REPO_ROOT/.venv/bin/python" python3 /usr/bin/python3; do
  if "$candidate" -c 'import yaml, jsonschema' >/dev/null 2>&1; then PY="$candidate"; break; fi
done
if [[ -z "$PY" ]]; then
  echo "Error: no Python with 'yaml' and 'jsonschema' found (tried .venv, python3, /usr/bin/python3)" >&2
  exit 1
fi
exec "$PY" "$SCRIPT_DIR/hydrate.py" "$TARGET" "${@:2}"
