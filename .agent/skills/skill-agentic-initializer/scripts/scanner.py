import os
from pathlib import Path
from typing import Dict, List


def generate_compressed_index(root_dir: str, base_path: str = ".") -> str:
    """
    Scans root_dir and generates a compressed, pipe-delimited index.
    Format: path/to/dir:{file1,file2,...}
    """
    root = Path(root_dir).resolve()
    if not root.exists():
        return f"Error: {root_dir} does not exist."

    index: Dict[str, List[str]] = {}

    for dirpath, _, filenames in os.walk(root):
        if not filenames:
            continue

        # Get relative path from root
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""

        # Normalize path separators to forward slash
        rel_dir = rel_dir.replace(os.sep, "/")

        # Filter for markdown-ish files
        valid_files = [f for f in filenames if f.endswith(('.md', '.mdx', '.txt'))]
        if not valid_files:
            continue

        valid_files.sort()
        index[rel_dir] = valid_files

    # Sort keys for determinism
    sorted_keys = sorted(index.keys())

    lines = [
        "[Docs Index]|root: " + base_path,
        "|IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning"
    ]

    for key in sorted_keys:
        files_str = "{" + ",".join(index[key]) + "}"
        path_prefix = key if key else "root"
        lines.append(f"|{path_prefix}:{files_str}")

    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1]
        base = sys.argv[2] if len(sys.argv) > 2 else target
        print(generate_compressed_index(target, base))
    else:
        print("Usage: python scanner.py <directory_to_scan> [base_path_for_index]")
