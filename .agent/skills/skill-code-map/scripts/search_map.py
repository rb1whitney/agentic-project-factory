#!/usr/bin/env python3
import argparse
import logging
import os
import sys

logger = logging.getLogger('map-search')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

def search_map(query: str, map_path: str):
    if not os.path.exists(map_path):
        logger.error(f"Repository map not found at {map_path}")
        return

    query_lower = query.lower()
    current_block = []
    current_header = ""
    found_in_block = False
    match_count = 0

    with open(map_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if line.startswith("FILE:"):
                if found_in_block:
                    sys.stdout.write(f"\n{current_header}\n")
                    sys.stdout.write("".join(current_block))
                    sys.stdout.write("-" * 40 + "\n")
                    match_count += 1

                current_header = line.strip()
                current_block = []
                found_in_block = False

                if match_count >= 10:
                    sys.stdout.write("\n(Truncated: too many matches. Please refine your search query.)\n")
                    break
            else:
                current_block.append(line)
                if query_lower in line.lower():
                    found_in_block = True

    if found_in_block and match_count < 10:
        sys.stdout.write(f"\n{current_header}\n")
        sys.stdout.write("".join(current_block))

def main():
    parser = argparse.ArgumentParser(description="Query the repository code map.")
    parser.add_argument("query", help="The symbol or signature to search for.")
    parser.add_argument("map_path", help="Path to the generated code map file.")
    args = parser.parse_args()

    search_map(args.query, args.map_path)

if __name__ == "__main__":
    main()
