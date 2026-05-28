#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import read_code_map as repo_mapper

logger = logging.getLogger('skeleton-generator')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

def process_file(file_path: Path):
    try:
        skeleton = repo_mapper.index_file(str(file_path))
        return f"FILE: {file_path}\n{skeleton}\n{'-'*40}\n"
    except Exception as e:
        logger.warning(f"Skipping {file_path}: {e}")
        return f"ERROR: {file_path} | {e}\n\n"

def main():
    parser = argparse.ArgumentParser(description="Generate repository-wide code skeletons.")
    parser.add_argument("--root", type=Path, help="Project root directory.")
    parser.add_argument("dirs", nargs="*", type=Path, help="Specific directories to index.")
    args = parser.parse_args()

    root = args.root or Path(os.environ.get('GEMINI_PROJECT_DIR', Path.cwd()))

    if args.dirs:
        search_dirs = [d for d in args.dirs if d.is_dir()]
    else:
        skip = {'.git', '.agent', 'node_modules', 'venv', '__pycache__'}
        search_dirs = [p for p in root.iterdir() if p.is_dir() and p.name not in skip]

    target_extensions = {cfg["extension"] for cfg in repo_mapper.LANGUAGE_QUERIES.values()}
    files_to_index = []

    for d in search_dirs:
        for ext in target_extensions:
            files_to_index.extend(d.rglob(f"*{ext}"))

    logger.info(f"Indexing {len(files_to_index)} files across {len(search_dirs)} directories.")

    output_path = root / 'repository_skeleton.txt'
    with open(output_path, 'w', encoding='utf-8') as f:
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            results = list(executor.map(process_file, files_to_index))
            for result in results:
                f.write(result)

    logger.info(f"Repository skeleton generated at {output_path}")

if __name__ == "__main__":
    main()
