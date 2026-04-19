# Agent.md Symbolic Link Configuration Skill

This skill provides comprehensive guidance on configuring AI agents to leverage a central `AGENT.md` file within a repository using symbolic links. This approach ensures all agents (e.g., Gemini CLI, Claude Copilot, custom scripts) adhere to a consistent set of project-specific guidelines, promoting maintainability, collaboration, and standardized behavior.

## Purpose

The primary goal is to establish a single, version-controlled `AGENT.md` file at the repository root as the canonical source of truth for all agentic behavior. By doing so, we achieve:

-   **Unified Agent Directives**: All automated assistants operate under the same set of rules and principles.
-   **Contextual Alignment**: Agent actions are always aligned with the specific conventions, architectural patterns, and workflows of the current project.
-   **Enhanced Collaboration**: Reduces discrepancies in agent behavior, making interactions more predictable for human and AI contributors alike.
-   **Simplified Updates**: Changes to agent guidelines only need to be made in one place.

## How to Use

To enable your AI agent to utilize the repository's central `AGENT.md` via symbolic linking:

1.  **Identify the Target `AGENT.md`**: Locate the `AGENT.md` file at the root of your project repository. This is the source file you want your agent(s) to follow.

    *Example Path:* `/path/to/your/repository/AGENT.md`

2.  **Determine Agent's Expected Path**: Find out where your specific AI agent expects to read its configuration or agentic instructions. This path can vary significantly by agent:

    *   **Claude Copilot**: Might look for a file like `.copilot/AGENT.md` within its working directory.
    *   **Other Gemini CLI Instances**: Could be configured to look for `AGENT.md` in a specific project subdirectory.
    *   **Custom Agents/Scripts**: The location would be defined by your script's logic.

    Consult your agent's documentation or configuration for this information.

3.  **Create the Symbolic Link**: Once you know both the source `AGENT.md` and the agent's expected destination path, create a symbolic link (symlink) from the expected destination path to the source `AGENT.md`.

    ### Linux / macOS

    Use the `ln -s` command. The syntax is `ln -s <source_file> <destination_link>`.

    ```bash
    # Example for Claude Copilot expecting an AGENT.md in a .copilot directory
    ln -s /path/to/your/repository/AGENT.md /path/to/your/project/.copilot/AGENT.md

    # Example for a generic agent expecting AGENT.md in its own configuration folder
    ln -s /path/to/your/repository/AGENT.md /path/to/my-agent/config/AGENT.md
    ```

    ### Windows (Administrator PowerShell)

    Use `mklink /H` (hard link) for files or `mklink /D` (directory symbolic link) for directories. For `AGENT.md` (a file), a hard link or file symbolic link (`/J` or `/H`) is appropriate. The syntax is `mklink /H "Link" "Target"`.

    ```powershell
    # Example for Claude Copilot on Windows (run as Administrator in PowerShell)
    cmd /c mklink /H "C:\Path\To\Your\Project\.copilot\AGENT.md" "D:\Path\To\Your\Repository\AGENT.md"

    # Example for a generic agent on Windows
    cmd /c mklink /H "C:\Path\To\My-Agent\Config\AGENT.md" "D:\Path\To\Your\Repository\AGENT.md"
    ```
    *Note: Replace `/path/to/your/repository/AGENT.md`, `/path/to/your/project/.copilot/AGENT.md`, etc., with the actual paths relevant to your setup.*

## Benefits of This Approach

-   **Single Source of Truth**: All agents operate under the same, consistently updated guidelines.
-   **Version Control**: `AGENT.md` is part of your repository, allowing for version tracking, pull requests, and code reviews for agent directives.
-   **Project Context**: Guidelines are inherently tailored to the project, reducing the likelihood of agents making decisions inconsistent with project standards.
-   **Reduced Duplication**: Eliminates the need to maintain separate agent configuration files across different agent platforms.

## Troubleshooting

-   **Broken Link**: If the agent isn't picking up the `AGENT.md`, ensure the symbolic link's target (`source_file`) still exists and the link itself is correctly pointing.
-   **Permissions**: On some systems, creating symbolic links might require administrator/root privileges or specific user permissions.
-   **Agent Compatibility**: Verify that your AI agent is capable of reading and interpreting `AGENT.md` or a similarly linked file for its instructions.
