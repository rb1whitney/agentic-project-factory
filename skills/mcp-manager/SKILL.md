---
name: mcp-manager
description: Manage MCP (Model Context Protocol) server lifecycle. Use to "turn on", build, and configure MCP servers for the workspace.
auto_triggers:
  - mcp
  - mcp_server
  - setup_mcp
  - turn_on_mcp
  - configure_mcp
related_skills:
  - "@gemini-conductor"
  - "@sre-expert"
---

# MCP Manager

Expert in managing Model Context Protocol (MCP) servers for the Expert Intelligence Hub.

## Core Lifecycle

The MCP servers are managed via the lifecycle tool located at `tools/mcp-servers/manage_mcps.sh`.

### Turning On All Servers

To "turn on" all servers (ensure they are downloaded, built, and configured for Gemini/VSCode):

```bash
./tools/mcp-servers/manage_mcps.sh ready
```

> [!IMPORTANT]
> All MCP repositories are localized within `tools/mcp-servers/mcp-*/` and are ignored by Git. If you accidentally clone them to the workspace root, run the `ready` command again to ensure they are correctly placed and then delete the root folders.

### Individual Commands

- **Status**: `./tools/mcp-servers/manage_mcps.sh status`  Show build and runtime status.
- **Build**: `./tools/mcp-servers/manage_mcps.sh build [server]`  Build specific or all servers.
- **Config**: `./tools/mcp-servers/manage_mcps.sh config`  Regenerate `.gemini/settings.json` and `.vscode/mcp.json`.
- **Health**: `./tools/mcp-servers/manage_mcps.sh health [server]`  Verify JSON-RPC capability.

## Configuration Details

- **Gemini CLI**: Configuration is stored in `.gemini/settings.json`.
- **VS Code**: Configuration is stored in `.vscode/mcp.json`.

> [!NOTE]
> Ensure you have `npx`, `uvx`, and `go` installed for runtime or build-time dependencies of specific servers.