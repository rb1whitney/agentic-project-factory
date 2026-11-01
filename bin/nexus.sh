#!/usr/bin/env bash
set -euo pipefail

# bin/nexus.sh - Nexus Orchestrator & Metadata Recompiler
# Enforces standard canonical source locations (.agent/agents, .agent/skills)
# Recompiles cached metadata and hydrates runtime projections before running sync.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

PY=python3
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
  PY="$REPO_ROOT/.venv/bin/python"
fi

echo "Recompiling agent and skill metadata from standard locations..."
"$PY" bin/compile_metadata.py --repo-root "$REPO_ROOT" --output ".agent/metadata.json"

echo "Hydrating canonical multi-adapter agents (claude, antigravity, codex)..."
./scripts/hydrate.sh all

echo "Executing Nexus synchronization (local + global harness spokes)..."
"$PY" bin/nexus.py --global-sync "$@"
