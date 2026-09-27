#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

if [[ "$TARGET" != "claude" && "$TARGET" != "antigravity" && "$TARGET" != "codex" && "$TARGET" != "all" ]]; then
  echo "Error: Unknown target '$TARGET' (expected: claude | antigravity | codex | all)" >&2
  exit 1
fi

exec python3 "$SCRIPT_DIR/hydrate.py" "$TARGET"
