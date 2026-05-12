#  MCP Server: THE GO-LIVE GUIDE

Follow these 5 steps to activate the **Expert Intelligence Hub** and grant your swarm "Ground Truth" sensors for AWS, GCP, GitHub, and Terraform.

##  Total Time Estimate: 20 Minutes

---

### Step 1: Initialize Runtimes (5 mins)
Ensure your environment has the required **Go**, **Node**, and **uv** (Python) runtimes.
```bash
# Run the secure setup script
bash bin/setup.sh
```

### Step 2: Download the Source (2 mins)
Fetch all 9 official MCP servers into your local ecosystem.
```bash
cd tools/mcp-servers
bash download_mcps.sh
```

### Step 3: Provision Credentials (5 mins)
This is a **Zero-Trust** environment. Local `.env` files are strictly forbidden via Gitignore and Policy.
1. Store your secrets in a vault: [**`gopass`**](file:///usr/bin/gopass) or [**`rbw`**](file:///usr/bin/rbw).
2. **Fallback**: Create [**`~/.mcp-servers/credentials`**](file:///root/.mcp-servers/credentials) (strictly outside this repo).
3. Add your tokens there (e.g., `GITHUB_TOKEN=...`).
4. The [**`mcp_wrapper.sh`**](file://./mcp_wrapper.sh) will dynamically inject these at runtime.

### Step 4: Build the Swarm Hub (5 mins)
Compile all servers for your specific OS and architecture.
```bash
./manage_mcps.sh build-all
```

### Step 5: Activate the Agents (3 mins)
Add the `mcpServers` configuration to your **Gemini CLI** or **Cursor** settings.

**For Gemini CLI ([`.gemini/agents/`](file://../../agents/))**:
Use the [**`mcp_wrapper.sh`**](file://./mcp_wrapper.sh) to ensure secret injection:
```yaml
mcpServers:
  github:
    command: "/bin/bash"
    args: ["./mcp-servers/mcp_wrapper.sh", "./mcp-servers/mcp-github/github-mcp-server"]
```

**For Cursor/VS Code**:
Add the server to your **MCP Settings** (Settings > Features > MCP), but set the command to the wrapper:
- **Name**: `MCP GitHub`
- **Command**: `/bin/bash`
- **Args**: `["/path/to/repo/mcp-servers/mcp_wrapper.sh", "/path/to/repo/mcp-servers/mcp-github/github-mcp-server"]`

---

##  Final Verification
Run this command in any terminal to verify the hub is online:
```bash
gemini tell "Look up the latest issues in this repository using the GitHub MCP server."
```

*Status: READY FOR MISSION.*