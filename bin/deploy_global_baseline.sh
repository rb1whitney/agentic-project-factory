#!/usr/bin/env bash
set -euo pipefail

# bin/deploy_global_baseline.sh - Deploy templates/GLOBAL_AGENT_BASELINE.md to
# each harness's global instructions path. Backs up an existing target that
# differs before overwriting it; skips targets that already match.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SOURCE="$REPO_ROOT/templates/GLOBAL_AGENT_BASELINE.md"

declare -A TARGETS=(
  ["Claude Code"]="$HOME/.claude/CLAUDE.md"
  ["Antigravity"]="$HOME/.gemini/AGENTS.md"
  ["Codex CLI"]="$HOME/.codex/AGENTS.md"
)

if [ ! -f "$SOURCE" ]; then
  echo "Error: source template not found at $SOURCE" >&2
  exit 1
fi

for name in "${!TARGETS[@]}"; do
  target="${TARGETS[$name]}"
  mkdir -p "$(dirname "$target")"

  if [ -f "$target" ] && cmp -s "$SOURCE" "$target"; then
    echo "[$name] up to date: $target"
    continue
  fi

  if [ -f "$target" ]; then
    backup="${target}.bak.$(date +%Y%m%d%H%M%S)"
    cp "$target" "$backup"
    echo "[$name] existing file differs, backed up to $backup"
  fi

  cp "$SOURCE" "$target"
  echo "[$name] deployed: $target"
done
