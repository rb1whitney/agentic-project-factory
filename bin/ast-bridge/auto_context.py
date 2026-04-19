import os
import argparse
import sys

def auto_context(query, code_map_file):
    """
    Sub-agent utility that identifies the 5-10 most relevant files for a task.
    This is intended to be called by an LLM with the code_map.md as context.
    """
    with open(code_map_file, "r") as f:
        code_map = f.read()

    # The actual 'Auto-Context' logic happens in the LLM's reasoning.
    # This utility just provides the structured context.
    
    prompt = f"""
Given the following Code Map of a repository, identify the most relevant files to address the user request:

User Request: {query}

---
{code_map}
---

Return a list of file paths that should be prioritized for reasoning, along with a brief reason for each.
"""
    # In a production tool, this would call the Flash API.
    # For this skill-based implementation, the agent uses this tool to 'lens' into the repo.
    return prompt

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query", help="User request or task")
    parser.add_argument("map", help="Code Map file")
    args = parser.parse_args()
    
    print(auto_context(args.query, args.map))
