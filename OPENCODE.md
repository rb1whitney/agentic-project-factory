# OpenCode & Local Model Workspace

This repository is optimized for high-performance agentic workflows using **OpenCode.ai** and **Ollama**. It features a "Deterministic Model Calculus" that automatically scales intelligence based on your local hardware (GPU/RAM).

## 🚀 Quick Start (New System)

To replicate this entire high-performance stack on a new machine:

1.  **Run Core Setup**:
    ```bash
    bash bin/setup.sh
    ```
    *This will automatically install Homebrew, OpenCode, Ollama (with GPU detection), and all agent dependencies.*

2.  **Verify Synchronization**:
    ```bash
    python3 bin/nexus.py --global-sync
    ```
    *Ensures all agent skills, policies, and personas are cross-linked to OpenCode's configuration directories.*

3.  **Perform Hardware Sync**:
    ```bash
    python3 bin/model_selector.py install
    ```
    *Detects your VRAM/RAM tier and pulls the best-in-class 2026 models (Gemma 4, Qwen 3, DeepSeek R1).*

## 🏛️ Source of Truth & Architecture

Instead of manual configuration, this repository treats OpenCode as a "Linked Client." All logic is sourced from the repo and automated:

### 1. The Configuration Hub (Nexus)
We don't copy agents or skills to OpenCode. **`bin/nexus.py`** creates symbolic links from `.agent/` to `~/.config/opencode/`. 
*   **Result**: Any change you make in this repo is instantly live in OpenCode.

### 2. Database Integration (The Agent Fixer)
OpenCode's internal SQLite database (`opencode.db`) requires a specific boolean tool format. **`bin/fix_agents_for_opencode.py`** automatically "scrounges" your agent markdown files and ensures their frontmatter is formatted correctly for the database parser.

### 3. Dynamic Provider Logic
The `opencode.jsonc` (which tells OpenCode how to talk to your local models) is generated dynamically by **`bin/model_selector.py`**.
*   It detects your **RTX 3060 VRAM** and builds the provider JSON using the high-performance `@ai-sdk/openai-compatible` SDK.

### 4. GPU Automation (The Flag Bridge)
**`bin/setup.sh`** automatically injects the necessary `LD_LIBRARY_PATH` flags into your shell profile. This allows the database and inference server to communicate with your NVIDIA hardware seamlessly in WSL2.

## 🛠️ Key Tools Reference

- **`bin/model_selector.py`**: The "Package Manager" for your local LLMs. It handles hardware detection, version checking, and OpenCode configuration.
- **`bin/nexus.py`**: The "Sync Engine" that keeps your local agent personas and skills in sync across all AI tools (OpenCode, Claude, Copilot).
- **`bin/fix_agents_for_opencode.py`**: A utility to ensure all agent markdown files follow OpenCode's specific `tools: { name: true }` boolean format.

## 📈 Performance Expectation

- **On GPU (RTX 3060)**: ~45-50 tokens/second (Instant feel).
- **On CPU (11th Gen i7)**: ~2-5 tokens/second (Delayed feel, use for background tasks).

For the best experience, use **OpenCode Cloud** models (`opencode/deepseek-v4-flash-free`) for interactive exploration, and local models for private, secure, or repetitive structural edits.
