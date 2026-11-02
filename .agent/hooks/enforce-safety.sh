#!/bin/bash
# PreToolUse hook (Claude Code). Reads the tool_name/tool_input JSON Claude Code
# sends on stdin (NOT via env vars) and asks for confirmation on destructive
# Bash commands or writes to critical paths, mirroring policies/safety.toml
# rule 6 and .agent/hooks/pre_tool_use.json's critical_paths list.
set -euo pipefail

INPUT="$(cat)"
TOOL_NAME="$(jq -r '.tool_name // empty' <<<"$INPUT")"

ask() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "ask",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

deny() {
  jq -n --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

case "$TOOL_NAME" in
  Bash)
    COMMAND="$(jq -r '.tool_input.command // empty' <<<"$INPUT")"
    # AGENTS.md Git protocol: agents never merge PRs.
    if [[ "$COMMAND" =~ gh[[:space:]]+pr[[:space:]]+merge ]]; then
      deny "gh pr merge is forbidden for agents (AGENTS.md Git & Push Protocol). A human merges."
    fi
    # AGENTS.md 2.4: approval-skipping flags need an explicit user decision.
    if [[ "$COMMAND" =~ (--?auto-approve|--no-verify|--dangerously) ]]; then
      ask "Command skips approval or verification (-auto-approve / --no-verify / --dangerously): confirm before running."
    fi
    if [[ "$COMMAND" =~ (rm[[:space:]]+-rf|git[[:space:]]+push[[:space:]]+--force|terraform[[:space:]]+destroy) ]]; then
      ask "Destructive command matched repo safety policy (rm -rf / git push --force / terraform destroy): confirm before running."
    fi
    ;;
  Write|Edit)
    FILE_PATH="$(jq -r '.tool_input.file_path // empty' <<<"$INPUT")"
    case "$FILE_PATH" in
      /etc/*|/usr/bin/*|*.git/config)
        ask "Write targets a critical path ($FILE_PATH): confirm before writing."
        ;;
    esac
    ;;
esac

exit 0
