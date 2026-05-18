#!/bin/bash
# Expert Intelligence Hub: MCP Server Downloader
# Fetches official MCP servers using a consistent mcp-<service> naming convention.
#
# Usage: ./download_mcps.sh

# --- Directory Awareness ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Format: "<git_url> <local_folder>"
# All folders follow the mcp-<service> pattern.
REPOS=(
    # --- Infrastructure & IaC ---
    "https://github.com/hashicorp/terraform-mcp-server.git mcp-terraform"

    # --- AWS ---
    "https://github.com/aws/agent-toolkit-for-aws.git mcp-aws-toolkit"
    "https://github.com/awslabs/mcp.git mcp-aws" # Legacy

    # --- Google Cloud ---
    "https://github.com/google/mcp.git mcp-google"
    "https://github.com/googleapis/gcloud-mcp.git mcp-gcloud"
    "https://github.com/GoogleCloudPlatform/gke-mcp.git mcp-gke"

    # --- Kubernetes & Crossplane ---
    "https://github.com/containers/kubernetes-mcp-server.git mcp-kubernetes"
    "https://github.com/upbound/marketplace-mcp-server.git mcp-marketplace"

    # --- Security ---
    "https://github.com/google/mcp-security.git mcp-security"

    # --- Developer Tools ---
    "https://github.com/github/github-mcp-server.git mcp-github"

    # --- Token Harvester Frameworks ---
    "https://github.com/mksglu/context-mode.git mcp-context-mode"
    "https://github.com/tirth8205/code-review-graph.git mcp-code-review-graph"
)

echo "--- Initializing Expert Intelligence Hub ---"
echo ""

CLONED=0
SKIPPED=0
FAILED=0

for entry in "${REPOS[@]}"; do
    url=$(echo "$entry" | awk '{print $1}')
    folder=$(echo "$entry" | awk '{print $2}')

    if [ -d "$folder" ]; then
        echo "[SKIP] $folder already exists."
        ((SKIPPED++))
    else
        echo "[CLONE] $url -> $folder"
        if git clone --depth 1 "$url" "$folder" 2>&1; then
            ((CLONED++))
        else
            echo "[FAIL] Could not clone $folder"
            ((FAILED++))
        fi
    fi
done

echo ""
echo "--- Download Complete ---"
echo "  Cloned: $CLONED | Skipped: $SKIPPED | Failed: $FAILED"
echo ""
echo "Inventory:"
for entry in "${REPOS[@]}"; do
    folder=$(echo "$entry" | awk '{print $2}')
    if [ -d "$folder" ]; then
        echo "  [OK]   $folder"
    else
        echo "  [MISS] $folder"
    fi
done