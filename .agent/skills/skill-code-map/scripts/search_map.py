#!/usr/bin/env python3
"""
search_map.py - Keyword search over a generated code map, returning matching file blocks only.

Understands both map formats:
  - code_mapper.py   : "### <path>" headings under a "# Repository Code Map" title
  - create_code_map.py: "FILE: <path>" blocks
"""

import argparse
import logging
import os
import sys
from typing import List, Tuple

logger = logging.getLogger("map-search")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

MAX_MATCHES = 10
HEADER_PREFIXES = ("FILE:", "### ")


def read_blocks(map_path: str) -> List[Tuple[str, List[str]]]:
    """Split a map into (header, body_lines) blocks; text before the first header is discarded."""
    blocks: List[Tuple[str, List[str]]] = []
    header, body = None, []
    with open(map_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith(HEADER_PREFIXES):
                if header is not None:
                    blocks.append((header, body))
                header, body = line.rstrip("\n"), []
            elif header is not None:
                body.append(line)
    if header is not None:
        blocks.append((header, body))
    return blocks


def search_map(query: str, map_path: str) -> int:
    """Print up to MAX_MATCHES blocks that mention `query`; returns the number printed."""
    if not os.path.exists(map_path):
        logger.error(f"Repository map not found at {map_path}")
        return 0

    needle = query.lower()
    matches = [
        (header, body)
        for header, body in read_blocks(map_path)
        if needle in header.lower() or any(needle in line.lower() for line in body)
    ]
    for header, body in matches[:MAX_MATCHES]:
        sys.stdout.write(f"\n{header}\n{''.join(body)}{'-' * 40}\n")
    if len(matches) > MAX_MATCHES:
        sys.stdout.write(
            f"\n(Truncated: {len(matches)} files match, showing {MAX_MATCHES}. Refine your search query.)\n"
        )
    return min(len(matches), MAX_MATCHES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Query the repository code map.")
    parser.add_argument("query", help="The symbol or signature to search for.")
    parser.add_argument("map_path", help="Path to the generated code map file.")
    args = parser.parse_args()
    return 0 if search_map(args.query, args.map_path) else 1


if __name__ == "__main__":
    sys.exit(main())
