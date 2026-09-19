#!/usr/bin/env bash
set -euo pipefail

# bin/nexus.sh - Nexus Orchestrator & Metadata Recompiler
# Enforces standard canonical source locations (.agent/agents, .agent/skills)
# Recompiles cached metadata and hydrates runtime projections before running sync.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "Recompiling agent and skill metadata from standard locations..."
python3 bin/compile_metadata.py --repo-root "$REPO_ROOT" --output ".agent/metadata.json"

echo "Hydrating canonical multi-adapter agents..."
./scripts/hydrate.sh claude
./scripts/hydrate.sh antigravity

echo "Executing Nexus synchronization..."
python3 bin/nexus.py "$@"
