#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
CANONICAL_DIR=".agent/agents"

if [[ -z "$TARGET" ]]; then
  echo "Error: Target harness required (claude | antigravity)" >&2
  exit 1
fi

if [[ ! -d "$CANONICAL_DIR" ]]; then
  echo "Error: Canonical source directory '$CANONICAL_DIR' not found." >&2
  exit 1
fi

shopt -s nullglob
files=("$CANONICAL_DIR"/*.yaml)
shopt -u nullglob

if [[ ${#files[@]} -eq 0 ]]; then
  echo "Error: No canonical agent definition files found in '$CANONICAL_DIR'" >&2
  exit 1
fi

validate_field() {
  local yaml_snippet="$1"
  local field_expr="$2"
  local field_name="$3"
  local file="$4"
  if ! echo "$yaml_snippet" | yq -e "${field_expr}" >/dev/null 2>&1; then
    echo "Configuration Error: File '$file' failed pre-flight validation. Required field '$field_name' is missing, empty, or null." >&2
    exit 1
  fi
}

case "$TARGET" in
  claude)
    mkdir -p .claude/agents
    for file in "${files[@]}"; do
      base=$(basename "$file" .yaml)

      if ! grep -q "^---" "$file"; then
        echo "Configuration Error: Missing markdown instruction boundary '---' in '$file'" >&2
        exit 1
      fi

      header=$(sed -n '1,/^---/p' "$file" | sed '$d')

      validate_field "$header" 'has("name") and .name != ""' "name" "$file"
      validate_field "$header" 'has("description") and .description != ""' "description" "$file"
      validate_field "$header" '.adapter.claude != null' "adapter.claude" "$file"
      validate_field "$header" '.adapter.claude.model != null and .adapter.claude.model != ""' "adapter.claude.model" "$file"
      validate_field "$header" '.adapter.claude.tools != null and (.adapter.claude.tools | length > 0)' "adapter.claude.tools" "$file"

      out_file=".claude/agents/${base}.md"
      tmp_file="${out_file}.tmp"
      {
        echo "---"
        echo "$header" | yq '{"name": .name, "description": .description} * .adapter.claude'
        echo "---"
        sed -n '/^---/,$p' "$file" | sed '1d'
      } > "$tmp_file"
      mv "$tmp_file" "$out_file"
      echo "Hydrated Claude agent: $out_file"
    done
    ;;
  antigravity)
    mkdir -p .agents
    for file in "${files[@]}"; do
      base=$(basename "$file" .yaml)

      header=$(sed -n '1,/^---/p' "$file" | sed '$d')
      if [[ -z "$header" ]]; then
        header=$(cat "$file")
      fi

      validate_field "$header" 'has("name") and .name != ""' "name" "$file"
      validate_field "$header" 'has("description") and .description != ""' "description" "$file"
      validate_field "$header" '.adapter.antigravity != null' "adapter.antigravity" "$file"
      validate_field "$header" '.adapter.antigravity.model != null and .adapter.antigravity.model != ""' "adapter.antigravity.model" "$file"
      validate_field "$header" '.adapter.antigravity.tools != null and (.adapter.antigravity.tools | length > 0)' "adapter.antigravity.tools" "$file"

      out_file=".agents/${base}.json"
      tmp_file="${out_file}.tmp"
      echo "$header" | yq -o=json '{"name": .name, "description": .description} * .adapter.antigravity' > "$tmp_file"
      mv "$tmp_file" "$out_file"
      echo "Hydrated Antigravity agent: $out_file"
    done
    ;;
  *)
    echo "Error: Unknown target '$TARGET' (expected: claude | antigravity)" >&2
    exit 1
    ;;
esac
