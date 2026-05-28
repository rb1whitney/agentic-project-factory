#!/usr/bin/env python3
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_file: Path):
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('agent_metrics')
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler(sys.stderr))
    return logger

def get_project_root():
    return Path(os.environ.get('GEMINI_PROJECT_DIR', Path.cwd()))

def main():
    parser = argparse.ArgumentParser(description="Track token usage and savings.")
    parser.add_argument("--root", type=Path, help="Project root directory.")
    args = parser.parse_args()

    root = args.root or get_project_root()
    logger = setup_logging(root / 'gemini' / 'logs' / 'metrics.log')

    try:
        input_text = sys.stdin.read()
        if not input_text:
            json.dump({}, sys.stdout)
            return

        data = json.loads(input_text)
        usage = data.get('llm_response', {}).get('usageMetadata', {})
        if not usage:
             candidates = data.get('llm_response', {}).get('candidates', [{}])
             if candidates:
                 usage = candidates[0].get('usageMetadata', {})

        tokens = usage.get('totalTokenCount', 0)
        event = data.get('event', 'unknown_event')

        logger.info(f"Event: {event} | Tokens: {tokens}")

        stats_file = root / 'gemini' / 'metrics.json'
        stats = {}
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    stats = json.load(f)
            except Exception:
                pass

        stats['total_tokens'] = stats.get('total_tokens', 0) + tokens
        stats['last_updated'] = datetime.now(timezone.utc).isoformat()

        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)

    except Exception as e:
        logger.error(f"Failed to track metrics: {e}")

    json.dump({}, sys.stdout)

if __name__ == "__main__":
    main()
