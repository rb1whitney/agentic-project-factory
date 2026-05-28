#!/usr/bin/env python3
import json
import sys
import logging
import os
import argparse
from pathlib import Path

# Intent Scoring Engine
INTENT_MARKERS = {
    "investigator": {
        "keywords": ["where is", "find all uses", "explain how", "how does", "locate", "track down", "understand"],
        "weight": 1.0,
        "threshold": 1.5
    }
}

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
    return logging.getLogger('cavecrew-delegate')

def score_intent(prompt: str) -> bool:
    prompt = prompt.lower()
    score = 0
    for marker in INTENT_MARKERS["investigator"]["keywords"]:
        if marker in prompt:
            score += INTENT_MARKERS["investigator"]["weight"]
    return score >= INTENT_MARKERS["investigator"]["threshold"]

def get_project_root():
    return Path(os.environ.get('GEMINI_PROJECT_DIR', Path.cwd()))

def main():
    parser = argparse.ArgumentParser(description="Intelligent tool delegation based on prompt intent.")
    parser.add_argument("--root", type=Path, help="Project root directory.")
    args = parser.parse_args()

    root = args.root or get_project_root()
    logger = setup_logging(root / 'gemini' / 'logs')

    try:
        input_text = sys.stdin.read()
        if not input_text:
            json.dump({"decision": "allow"}, sys.stdout)
            return
            
        data = json.loads(input_text)
        prompt = data.get('prompt', '') or data.get('llm_request', {}).get('prompt', '')
        
        if score_intent(prompt):
            logger.info("Activating Investigator Mode.")
            response = {
                "hookSpecificOutput": {
                    "llm_request": {
                        "toolConfig": {
                            "mode": "ANY",
                            "allowedFunctionNames": ["read_file", "grep", "list_dir", "list_directory", "grep_search", "glob"]
                        }
                    }
                }
            }
            json.dump(response, sys.stdout)
            return

        json.dump({"decision": "allow"}, sys.stdout)

    except Exception as e:
        logger.error(f"Error in cavecrew-delegate: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
