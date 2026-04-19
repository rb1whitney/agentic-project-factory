# Implementation Plan: MCP Expert Intelligence Hub

## Phase 1: Download and Inventory (COMPLETE)
- [x] **Task 1: Standardize naming** - Rename all directories to `mcp-<service>` convention.
- [x] **Task 2: Fix upstream URLs** - Remove bogus repos, add verified ones.
- [x] **Task 3: Download all servers** - Clone 9 MCP server repositories.
- [x] **Task 4: Create README** - Document inventory, agent coverage matrix.

## Phase 2: Runtime Prerequisites (COMPLETE)
- [x] **Task 5: Install uv/uvx** - uv 0.11.6 installed at `~/.local/bin`.
- [x] **Task 6: Install Go** - Go 1.24.2 installed at `/usr/local/go`.
- [x] **Task 7: Verify Terraform binary** - Pre-built binary responds to `initialize` JSON-RPC.
- [x] **Task 8: Verify Node.js** - Node 20.19.5 available for gcloud MCP.

## Phase 3: Build Servers (COMPLETE)
- [x] **Task 9: mcp-terraform** - Pre-built binary, verified working.
- [x] **Task 10: mcp-gcloud** - npm-based, no build needed (npx runtime).
- [x] **Task 11: mcp-aws** - uvx-based, no build needed.
- [x] **Task 12: mcp-github** - Downloaded pre-built v0.33.1 from GitHub Releases. Needs GITHUB_TOKEN.
- [x] **Task 13: mcp-gke** - BLOCKED. Needs Go 1.26+, no pre-built release exists.
- [x] **Task 14: mcp-kubernetes** - Downloaded pre-built v0.0.60 from GitHub Releases. Needs kubeconfig.
- [x] **Task 15: mcp-marketplace** - Built from source with Go 1.24.2. Health: OK.
- [x] **Task 16: mcp-security** - Python-based, verify deps at runtime.

## Phase 4: Configuration (COMPLETE)
- [x] **Task 17: Create .gemini/settings.json** - 11 MCP server entries (4 binary, 3 npx, 4 uvx).
- [x] **Task 18: Create .vscode/mcp.json** - Matching VS Code configuration.
- [ ] **Task 19: Wire agent SYSTEM.md files** - Annotate each agent with its MCP tool inventory.

## Phase 5: Orchestration Script (COMPLETE)
- [x] **Task 20: Create manage_mcps.sh** - Lifecycle manager with:
  - `status` - Shows all 14 server entries with build/ready status
  - `build` - Downloads pre-built binaries or builds from source
  - `health` - JSON-RPC initialize check for binary servers
  - `config` - Regenerates .gemini/settings.json and .vscode/mcp.json
  - `download` - Clones missing repos via download_mcps.sh

## Phase 6: Verification and Finalization (COMPLETE)
- [x] **Task 21: Smoke-test all servers** - terraform: OK, marketplace: OK, github/k8s: need env vars.
- [x] **Task 22: Integration test** - Health check shows 2 OK, 2 expected-fail, 7 runtime, 1 blocked, 1 ref.
- [x] **Task 23: Register track** - Registered in conductor tracks.md.

## Build Status Matrix

| Server | Method | Binary | Health |
|:---|:---|:---|:---|
| mcp-terraform | Pre-built in repo | `terraform-mcp-server` | **OK** |
| mcp-marketplace | Built from source (Go 1.24) | `marketplace-mcp-server` | **OK** |
| mcp-github | GitHub Release v0.33.1 | `github-mcp-server` | Needs GITHUB_TOKEN |
| mcp-kubernetes | GitHub Release v0.0.60 | `kubernetes-mcp-server` | Needs kubeconfig |
| mcp-gcloud | npx runtime | N/A | Runtime |
| mcp-gcloud-obs | npx runtime | N/A | Runtime |
| mcp-gcloud-storage | npx runtime | N/A | Runtime |
| mcp-aws (4 servers) | uvx runtime | N/A | Runtime |
| mcp-security | Python runtime | N/A | Runtime |
| mcp-google | Reference only | N/A | N/A |
| mcp-gke | BLOCKED | None | Needs Go 1.26 |

## Remaining Work
- [ ] Wire MCP tool annotations into agent SYSTEM.md files (Phase 4, Task 19)
- [ ] Resolve mcp-gke build (wait for pre-built release or install Go 1.26)
