# Knowledge Validator Skill

## Overview

This skill provides a formal, step-by-step process for validating the agent's current understanding of a topic against fresh, external information. Activate this skill when you need to perform a rigorous fact-check.

## Validation Workflow

**Goal:** To validate the core facts and assumptions related to the current task and update your understanding.

**Step 1: Identify Core Assumptions**
- **Action:** Before using any tools, explicitly state the key pieces of information, facts, or assumptions you are currently using to address the user's request.

**Step 2: Seek External Information**
- **Action:** Use the `google_web_search` tool to perform targeted searches on the assumptions identified in Step 1. Formulate queries that are likely to find recent and authoritative sources.
- **Guidance:** If other tools are relevant (e.g., checking a file's modification date), use them as well.

**Step 3: Synthesize and Compare**
- **Action:** Analyze the results from your search. Compare the new information with the assumptions you stated in Step 1.

**Step 4: Report Findings**
- **Action:** Clearly report your findings to the user. Explicitly state:
    - What your original assumption was.
    - What the new information is.
    - Whether the new information **confirms**, **contradicts**, or **updates** your original assumption.
- **Completion:** Once you have reported the validation results, you may proceed with the original task, using the newly validated information.