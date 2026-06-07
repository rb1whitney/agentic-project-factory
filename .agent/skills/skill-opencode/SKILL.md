---
name: skill-opencode
description: Model server administrator for managing OpenCode providers, GPU optimization, and local LLM endpoints.
  - opencode
  - local_models
  - model_management
  - install_models
  - check_hardware
  - "@mcp-manager"
  - "@gemini-conductor"
---
# Opencode Manager (GPU Accelerated)

Expert in managing the `opencode` platform for local LLM execution. Optimized for **NVIDIA RTX 3060 (6GB VRAM)**.

## Core Management

### `check-hardware`
Detects GPU/CPU/RAM and recommends the best SOTA models for the current tier.
- **Command**: `python3 {PROJECT_DIR}/bin/model_selector.py check`

### `install-best-models`
Downloads and installs the GPU-optimized 2026 model stack.
- **Command**: `python3 {PROJECT_DIR}/bin/model_selector.py install`

## Platform Commands

- **Serve**: `opencode serve` (Starts headless server)
- **Web**: `opencode web` (Opens browser TUI)
- **Stats**: `opencode stats` (Token/Cost usage)

## High-Performance 2026 Stack

| Model | Usage | Target Device |
| :--- | :--- | :--- |
| **Qwen 2.5 Coder 7B** | Primary Agentic Work (Tools/Coding) | **GPU** (Fits in 6GB) |
| **DeepSeek R1 8B** | Complex Reasoning / Math / Logic | **GPU** (Fits in 6GB) |
| **Gemma 4 E4B** | Ultra-fast Edge Reasoning | **GPU** (Instant) |
| **Llama 3.2 3B** | Lightweight Chat Fallback | **GPU/CPU** |

## Performance Note
Local execution on this system is currently configured for **GPU Acceleration** via CUDA 12.7. Expect speeds of **30-50 tokens/second** on primary models.
