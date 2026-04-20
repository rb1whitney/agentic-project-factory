import argparse
import logging
import os
import sys
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("auto_context")


def auto_context(query: str, code_map_file: str) -> Optional[str]:
    """
    Sub-agent utility that identifies the 5-10 most relevant files for a task.
    This is intended to be called by an LLM with the code_map.md as context.
    """
    if not os.path.exists(code_map_file):
        logger.error(f"Code map file not found: {code_map_file}")
        return None

    try:
        with open(code_map_file, "r", encoding="utf-8") as f:
            code_map = f.read()
    except Exception as e:
        logger.error(f"Failed to read code map file: {e}")
        return None

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate context prompt from a code map.")
    parser.add_argument("query", help="User request or task")
    parser.add_argument("map", help="Code Map file")
    args = parser.parse_args()

    result = auto_context(args.query, args.map)
    if result is None:
        sys.exit(1)
    print(result)


if __name__ == "__main__":
    main()
