# Track Specification: MCP Expert Intelligence Hub

## Objective
Stand up the MCP server infrastructure in `tools/mcp-servers/` so every expert agent has access to live, ground-truth intelligence from official cloud and tool APIs via the Model Context Protocol.

## Context
The workspace has 11 expert sub-agents but they currently operate without any real-time external intelligence. MCP servers provide a standardized protocol for AI agents to query live documentation, cloud APIs, registries, and cluster state. This track downloads, builds, configures, and wires 9 MCP servers into the agent system.

## Scope
- **Download**: Clone all 9 upstream MCP server repositories with consistent `mcp-<service>` naming.
- **Build**: Install runtime prerequisites (uv/uvx for Python, Go for binary servers) and build or verify each server.
- **Configure**: Generate `.gemini/settings.json` and `.vscode/mcp.json` with all server entries.
- **Wire**: Annotate each agent SYSTEM.md with the MCP tools available to it.
- **Orchestrate**: Create `manage_mcps.sh` for lifecycle management (build, start, stop, health, config-gen).

## Success Criteria
- [ ] All 9 `mcp-*` directories present and verified via `download_mcps.sh`.
- [ ] Terraform MCP server responds to a stdio `initialize` request.
- [ ] gcloud MCP server starts via `npx @google-cloud/gcloud-mcp`.
- [ ] AWS documentation MCP server starts via `uvx`.
- [ ] `.gemini/settings.json` contains mcpServers block with all functional servers.
- [ ] `.vscode/mcp.json` contains matching server configuration.
- [ ] Agent SYSTEM.md files annotated with their MCP tool inventory.
- [ ] `manage_mcps.sh` can build, start, and health-check all servers.

## Agent Coverage

| Agent | MCP Server(s) |
|:---|:---|
| terraform-expert | mcp-terraform |
| aws-expert | mcp-aws (docs, iac, eks, iam) |
| gcp-expert | mcp-gcloud, mcp-gke |
| k8s-expert | mcp-kubernetes, mcp-gke, mcp-marketplace |
| sre-expert | mcp-gcloud (observability), mcp-aws (cloudwatch) |
| security-reviewer | mcp-security |
| github-reviewer | mcp-github |
| packer-expert | None (no upstream MCP exists) |
| architecture-expert | None (design-only, no MCP needed) |
| shell-expert | None (terminal-only, no MCP needed) |
| gemini-conductor | None (lifecycle-only, no MCP needed) |