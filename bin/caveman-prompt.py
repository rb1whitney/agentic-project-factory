#!/usr/bin/env python3
import json
import sys
import logging
import os
import argparse
from pathlib import Path

def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'hooks.log'),
            logging.StreamHandler(sys.stderr)
        ]
    )
    return logging.getLogger('caveman-prompt')

def get_project_root():
    return Path(os.environ.get('GEMINI_PROJECT_DIR', Path.cwd()))

def main():
    parser = argparse.ArgumentParser(description="Inject caveman prose rules.")
    parser.add_argument("--root", type=Path, help="Project root directory.")
    args = parser.parse_args()

    root = args.root or get_project_root()
    logger = setup_logging(root / 'gemini' / 'logs')

    try:
        input_text = sys.stdin.read()
        if not input_text:
            json.dump({}, sys.stdout)
            return
            
        input_data = json.loads(input_text)
        logger.info("Injecting Caveman Override.")
        
        caveman_prompt = """
SYSTEM OVERRIDE: CAVEMAN MODE ACTIVE.
Rules:
1. Strip articles, fillers, politeness, and preambles. Keep technical substance.
2. Use fragmented, telegraphic sentences ("New object ref each render. Wrap in useMemo").
3. Full technical accuracy: Retain paths, variable names, and exact code byte-for-byte.
4. No full sentences unless quoting external docs.
"""
        
        output = {
            "hookSpecificOutput": {
                "llm_request": {
                    "additionalContext": caveman_prompt
                }
            }
        }
        
        json.dump(output, sys.stdout)

    except Exception as e:
        logger.error(f"Error in caveman-prompt: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
