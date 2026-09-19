#!/usr/bin/env bash
set -euo pipefail

# bin/factory_clean.sh - Clean Ephemeral Projections and Dead Vendor Directories
# Removes generated projection artifacts while keeping .agent/ master files 100% intact.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== FACTORY CLEAN: Stripping Ephemeral Projections & Dead Directories ==="

# 1. Remove dead/decommissioned vendor directories
for dead_dir in .gemini .antigravitycli .copilot .opencode; do
  if [[ -d "$dead_dir" || -L "$dead_dir" ]]; then
    rm -rf "$dead_dir"
    echo "Removed dead directory: $dead_dir"
  fi
done

# 2. Clean projected Claude files (keep directory structure for session)
if [[ -d ".claude" ]]; then
  if [[ -L ".claude" ]]; then
    rm -f ".claude"
    mkdir -p .claude/agents .claude/skills
  else
    rm -rf .claude/agents/* 2>/dev/null || true
    # Remove broken symlinks in .claude
    find .claude -xtype l -delete 2>/dev/null || true
  fi
  echo "Cleaned ephemeral projections in: .claude/"
fi

# 3. Clean projected Antigravity files
if [[ -d ".agents" ]]; then
  rm -f .agents/*.json 2>/dev/null || true
  find .agents -xtype l -delete 2>/dev/null || true
  echo "Cleaned ephemeral projections in: .agents/"
fi

# 4. Clean broken symlinks in .github
if [[ -d ".github" ]]; then
  find .github -xtype l -delete 2>/dev/null || true
  echo "Cleaned broken symlinks in: .github/"
fi

echo "=== Factory Clean Complete. Master .agent/ remains pristine. ==="
