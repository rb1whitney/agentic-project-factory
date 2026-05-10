---
name: gemini
description: Provides expertise on Gemini CLI. Crucially, it contains the complete workflow to update its own knowledge by fetching and summarizing the latest official documentation.
related_skills: []
auto_triggers: []
---

# Gemini CLI Expert and Knowledge Updater

## Overview

This skill serves two purposes:
1.  It provides the agent with core principles about how the Gemini CLI works.
2.  It contains the complete, end-to-end workflow for updating its own knowledge base.

When asked to "update your knowledge" or "update the cli docs", this skill should be activated to perform the full update and summarization process.

---

## Workflow: Update Knowledge Base

This is a multi-step process to refresh the `references/latest_docs.md` file with a comprehensive summary of the entire Gemini CLI documentation.

**Step 1: Fetch Documentation**
- **Action:** Use the `run_shell_command` tool to execute the script at `.gemini/commands/update-self-knowledge`.
- **Expected Output:** The script will print a single line to standard output, which is the absolute path to a temporary file containing all the concatenated documentation. Capture this file path.

**Step 2: Read Documentation Content**
- **Action:** Use the `read_file` tool on the file path you received from Step 1. This will bring the full documentation into your context.
- **Note:** The file may be large. Read the entire file.

**Step 3: Summarize Documentation**
- **Action:** Perform a comprehensive summarization of the documentation you just read.
- **Guidance:** The summary should be in markdown and well-structured with clear headings. It should cover all major capabilities of the Gemini CLI, including its architecture, commands, options, skills, extensions, and other features.

**Step 4: Save the New Summary**
- **Action:** Use the `write_file` tool to save your newly generated summary.
- **Destination:** Overwrite the file at `.gemini/skills/gemini-cli-expert/references/latest_docs.md`.

**Step 5: Clean Up**
- **Action:** Use the `run_shell_command` tool to delete the temporary file from Step 1. The command should be `rm <file_path>`. This is important to avoid leaving temporary files on the user's system.
- **Completion:** The process is now complete. The knowledge base is up to date.


##  Capability Reference Guide
Use the following runbooks for deep-dive investigation and implementation.

| Capability | Reference File |
| :--- | :--- |
| **Latest_Docs** | [latest_docs.md](./references/latest_docs.md) |