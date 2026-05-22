#!/bin/bash
#  EXPERT INTELLIGENCE HUB: SECURE MCP WRAPPER (ZERO-TRUST)
# Dynamically hydrates the environment with secrets from a vault (gopass/rbw)
# or an out-of-repo configuration file (~/.mcp-servers/credentials).

# --- Configuration ---
EXTERNAL_CONFIG="$HOME/.mcp-servers/credentials"

# --- Function: Get Secret ---
# Attempts to pull a secret from gopass, rbw, or environment.
get_secret() {
    local key=$1
    local fallback=$2

    # 1. Try gopass
    if command -v gopass >/dev/null; then
        VAL=$(gopass show -c "mcp/$key" 2>/dev/null)
        if [ -n "$VAL" ]; then echo "$VAL"; return; fi
    fi

    # 2. Try rbw (Bitwarden)
    if command -v rbw >/dev/null; then
        VAL=$(rbw get "$key" 2>/dev/null)
        if [ -n "$VAL" ]; then echo "$VAL"; return; fi
    fi

    # 3. Fallback to Environment (populated by ~/.mcp-servers/credentials)
    echo "${!key:-$fallback}"
}

# --- Hydration Phase ---
# Only source the external config if it exists. NEVER source local .env.
if [ -f "$EXTERNAL_CONFIG" ]; then
    # shellcheck source=/dev/null
    source "$EXTERNAL_CONFIG"
fi

# Export critical tokens
GITHUB_TOKEN=$(get_secret "GITHUB_TOKEN" "")
export GITHUB_TOKEN
AWS_ACCESS_KEY_ID=$(get_secret "AWS_ACCESS_KEY_ID" "")
export AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$(get_secret "AWS_SECRET_ACCESS_KEY" "")
export AWS_SECRET_ACCESS_KEY
TERRAFORM_CLOUD_TOKEN=$(get_secret "TERRAFORM_CLOUD_TOKEN" "")
export TERRAFORM_CLOUD_TOKEN

# --- Execution Phase ---
# Hand off control to the actual MCP server binary
if [ -z "$1" ]; then
    echo "[ERROR] No MCP server binary specified."
    exit 1
fi

exec "$@"