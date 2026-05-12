#!/bin/bash
# Expert Intelligence Hub: MCP Server Manager/Orchestrator
# Handles building, running, and health-checking MCP servers.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

COMMAND=$1
TARGET=$2

usage() {
    echo "Usage: ./manage_mcps.sh [build|build-all|list-tools|health] [mcp-service]"
    echo "Example: ./manage_mcps.sh list-tools mcp-github"
}

if [ -z "$COMMAND" ] || [ -z "$TARGET" ]; then
    usage
    exit 1
fi

if [ ! -d "$TARGET" ]; then
    echo "[ERROR] Directory $TARGET not found."
    exit 1
fi

case $COMMAND in
    "build")
        echo "[BUILD] Initializing build for $TARGET..."
        if [ -f "$TARGET/go.mod" ]; then
            cd "$TARGET" && go build ./... && cd ..
        elif [ -f "$TARGET/package.json" ]; then
            cd "$TARGET" && npm install && npm run build && cd ..
        elif [ -f "$TARGET/setup.py" ] || [ -f "$TARGET/pyproject.toml" ]; then
            cd "$TARGET" && uv venv && source .venv/bin/activate && uv pip install -e . && cd ..
        fi
        ;;
    "build-all")
        echo "[BUILD-ALL] Triggering global MCP build..."
        for dir in mcp-*; do
            if [ -d "$dir" ]; then
                "$0" build "$dir"
            fi
        done
        ;;
    "list-tools")
        echo "[DISCOVERY] Attempting to list tools for $TARGET..."
        # Note: This requires the server to support stdio mode
        # and for us to have a client that can send the 'listTools' request.
        # For now, we will perform a static analysis of the 'server.json' or source code.
        if [ -f "$TARGET/server.json" ]; then
            cat "$TARGET/server.json" | grep -A 20 "tools"
        elif [ -d "$TARGET/cmd" ]; then
            grep -r "Tool" "$TARGET/cmd" | head -n 10
        fi
        ;;
    "health")
        echo "[HEALTH] Checking if $TARGET is runnable..."
        # Minimal check for entry point
        if [ -f "$TARGET/Dockerfile" ] || [ -d "$TARGET/.git" ]; then
            echo "[OK] Static health check passed."
        fi
        ;;
    *)
        usage
        exit 1
        ;;
esac