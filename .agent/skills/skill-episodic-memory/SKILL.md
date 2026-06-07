---
name: skill-episodic-memory
description: Swarm context manager for virtual memory paging (paging dense context out and required history in).
---
# Episodic Memory (Virtual Memory Paging)

This skill implements the 2026 OS-inspired memory management pattern for long-horizon agents.

## Core Principle
Treat the LLM context window as RAM. Treat the interaction history as Disk. You are the Memory Manager.

## Virtual Paging
Do not allow the context window to bloat indefinitely. You must autonomously decide when to page information in or out.

1. **Page In (Load)**
   - When a new track or task is initiated, pull only the specific Core Memory block related to that domain.
   - Example: If the task is about AWS IAM, page out GCP configuration and page in AWS IAM history.

2. **Page Out (Evict)**
   - When a task phase completes, summarize the phase into a dense Core Memory block and clear the verbose logs from active context.
   - Use the `{PROJECT_DIR}/bin/rtk` tool to pipe and compress outputs to assist in keeping the footprint small.

## Caveman-Prose Protocol (MANDATORY)
All outputs MUST use caveman-prose. Rules:
- No articles (a, the, an), no pronouns (I, we, you)
- No preambles, pleasantries, hedging
- Format: Location | Problem | Fix
- BANNED: full sentences, filler phrases, emoji
- GREP before READ. AST before LOAD. Inline before subagent.
- All shell output piped through {PROJECT_DIR}/bin/rtk
