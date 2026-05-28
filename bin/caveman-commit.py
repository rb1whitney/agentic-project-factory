#!/usr/bin/env python3
import json
import sys
import logging
import os
import re
import argparse
from pathlib import Path

def setup_logging(log_dir: Path):
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'hooks.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stderr)
        ]
    )
    return logging.getLogger('caveman-commit')

def lint_commit_message(message: str) -> (bool, str):
    subject = message.split('\n')[0].strip()
    
    if len(subject) > 50:
        return False, "Subject too verbose (> 50 chars)."
        
    forbidden = r'\b(the|a|an)\b'
    if re.search(forbidden, subject, re.IGNORECASE):
         return False, "Subject contains articles. Use caveman prose."
         
    return True, ""

def get_project_root():
    return Path(os.environ.get('GEMINI_PROJECT_DIR', Path.cwd()))

def main():
    parser = argparse.ArgumentParser(description="Enforce Caveman commit message constraints.")
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
        tool_calls = data.get('llm_request', {}).get('toolCalls', [])
        
        for call in tool_calls:
            if call.get('name') == 'run_shell_command':
                cmd = call.get('arguments', {}).get('command', '')
                if 'git commit' in cmd:
                    msg_match = re.search(r'(?:-m|--message)(?:\s+|=)["\']([^"\']+)["\']', cmd)
                    if msg_match:
                        msg = msg_match.group(1)
                        valid, error = lint_commit_message(msg)
                        if not valid:
                            response = {
                                "decision": "deny",
                                "reason": f"Caveman Violation: {error}",
                                "systemMessage": "Blocked verbose/non-caveman commit."
                            }
                            logger.warning(f"Commit denied: {error}")
                            json.dump(response, sys.stdout)
                            return

        json.dump({"decision": "allow"}, sys.stdout)

    except Exception as e:
        logger.error(f"Error in caveman-commit: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
