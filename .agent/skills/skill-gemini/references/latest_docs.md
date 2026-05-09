# Gemini CLI: Comprehensive Abilities Summary

This summary is generated from the official Gemini CLI documentation.

## 1. Core Architecture & Interaction Flow

The CLI is composed of two main packages:
-   **CLI package (`packages/cli`):** Handles user input, output presentation, history, display, theming, and configuration.
-   **Core package (`packages/core`):** Acts as the backend, orchestrating interactions with the Gemini API, managing tool execution, prompt construction, and state management.
-   **Tools (`packages/core/src/tools/`):** Individual modules extending Gemini's capabilities to interact with the local environment (filesystem, shell, web).

**Interaction Flow:**
1.  User input via CLI (`packages/cli`).
2.  Input sent to `packages/core`.
3.  Core constructs prompt, sends to Gemini API.
4.  Gemini API responds (direct answer or tool request).
5.  If tool requested, core executes it (with user approval for file/shell modifications).
6.  Tool result sent back to Gemini API.
7.  Final response sent back to CLI (`packages/cli`).
8.  Response displayed to user.

## 2. Agent Skills

Skills are modular, self-contained directories that extend Gemini CLI's capabilities with specialized knowledge, workflows, and tools.

-   **Discovery:** Gemini scans `.gemini/skills/` (workspace), `~/.gemini/skills/` (user), and Extension Skills. Workspace skills take precedence.
-   **Activation:** Gemini autonomously decides to use a skill, calls `activate_skill`, seeks user consent, then injects `SKILL.md` and resources into its context.
-   **Management (Interactive):** Use `/skills` commands (`list`, `link`, `disable`, `enable`, `reload`).
-   **Management (Terminal):** Use `gemini skills` commands (`list`, `link`, `install`, `uninstall`, `enable`, `disable`).
-   `/skills reload` is crucial after modifying skill files.

## 3. CLI Commands & Options

Gemini CLI offers a rich set of commands and options for various tasks:

### Interactive & Headless Execution
-   `gemini`: Start interactive REPL.
-   `gemini "query"`: Non-interactive query.
-   `cat file | gemini`: Process piped content.
-   `gemini -i "query"`: Execute and continue interactively.
-   `gemini -r "latest"`: Resume most recent session.

### Core CLI Options
-   `--debug`, `--model`, `--prompt`, `--prompt-interactive`, `--sandbox`, `--approval-mode` (`default`, `auto_edit`, `yolo`), `--extensions`, `--resume`, `--output-format` (`text`, `json`, `stream-json`).

### Slash Commands (`/`) - Meta-level control
-   `/about`: Show version info.
-   `/auth`: Change authentication method.
-   `/bug`: File an issue.
-   `/chat`: Save/resume/delete/list/share conversation history. Supports tagging.
-   `/clear`: Clear terminal screen (`Ctrl+L`).
-   `/commands`: Manage custom slash commands (`reload`).
-   `/compress`: Replace chat context with a summary (saves tokens).
-   `/copy`: Copy last output to clipboard.
-   `/directory` (`/dir`): Manage workspace directories (`add`, `show`).
-   `/docs`: Open documentation in browser.
-   `/editor`: Select editor.
-   `/extensions`: List active extensions.
-   `/help`: Display help information.
-   `/model`: Select current model.
-   `/rewind`: Navigate session history.
-   `/settings`: Open settings dialog.
-   `/share`: Share conversation.
-   `/stats`: Display token usage.
-   `/subagents`: Manage subagents.
-   `/tasks`: View/manage current tasks.
-   `/tools`: Manage available tools.

## 4. Extensions

Extend Gemini CLI's functionality with extensions (community, partner, Google-built).
-   **Management (`gemini extensions`):** `install`, `uninstall`, `list`, `update`, `enable`, `disable`, `link`, `new`, `validate`.
-   **Examples:** Conductor (planning), Eleven Labs (audio), Workspace (Google services), Redis, Anomalo, Flutter, Hugging Face, Monday.com, Data Commons, Browserbase.

## 5. Checkpointing

Automatically saves project snapshots before file modifications by AI tools.
-   **How it works:** Creates a Git snapshot in `~/.gemini/history/` and saves conversation history.
-   **Enabling:** Set `"general": { "checkpointing": { "enabled": true } }` in `settings.json`.
-   **Using `/restore`:** List (`/restore`) or restore specific checkpoints (`/restore <checkpoint_file>`).

## 6. Release Announcements (v0.28.0 - v0.5.0 highlights)

Recent releases focus on:
-   **AI Capabilities:** Enhanced Agent Skills, `skill-creator`, `pr-creator`, improved `cli_help` agent, subagent improvements, plan mode, dynamic policy registration.
-   **User Experience (UI/UX):** New slash commands (`/prompt-suggest`, `/rewind`, `/introspect`), visual indicators, improved focus switching (Tab), dynamic terminal titles, seamless scrollable UI, mouse support, custom themes.
-   **Security & Authentication:** Interactive/non-interactive OAuth, improved Policy Engine, granular shell command allowlisting, folder trust, API key authentication.
-   **Core Functionality & Performance:** Event-driven architecture, scheduler refactoring, token calculation optimization, caching, retry mechanisms, JSON output mode, `write_todos` tool.
-   **Tooling:** `web_fetch` for JSON, `grep_search` alias, `ask_user` tool markdown rendering.
-   **Extensions:** New partner extensions (Workspace, Redis, Anomalo, Eleven Labs), `gemini extensions install` from various sources.
-   **Experimental Features:** Agent Skills in preview (v0.23.0), Edit Tool, Prompt Completion, A2A development-tool extension.

## 7. Key Design Principles

-   **Modularity:** Separation of CLI (frontend) and Core (backend).
-   **Extensibility:** New capabilities via the tool system.
-   **User Experience:** Rich and interactive terminal.