import argparse
import logging
import sys
from typing import Optional

from tree_sitter import Node, Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("semantic_edit")


def semantic_replace(file_path: str, symbol_type: str, symbol_name: str, new_content: str) -> bool:
    """
    Performs a basic semantic replacement based on tree-sitter node identification.

    Args:
        file_path: Path to the file to edit.
        symbol_type: The type of symbol (for language detection).
        symbol_name: The name or content to search for within a node.
        new_content: The content to replace the node with.

    Returns:
        True if the replacement was successful, False otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        return False

    # Determine language from extension
    ext = file_path.split(".")[-1].lower()
    lang_map = {"java": "java", "tf": "hcl", "hcl": "hcl", "yaml": "yaml", "yml": "yaml"}
    lang_name = lang_map.get(ext)

    if not lang_name:
        logger.error(f"Unsupported language: {ext}")
        return False

    try:
        lang = get_language(lang_name)
        parser = Parser()
        parser.set_language(lang)
        tree = parser.parse(content.encode("utf-8"))
        root = tree.root_node
    except Exception as e:
        logger.error(f"Failed to initialize parser for {lang_name}: {e}")
        return False

    def find_node(node: Node, target_name: str) -> Optional[Node]:
        """Recursive search for a node containing the target text."""
        try:
            node_text = content[node.start_byte : node.end_byte]
            if target_name in node_text:
                # If it's a leaf or specific match, return it
                # This is a heuristic and should be replaced with real queries
                return node
            for child in node.children:
                res = find_node(child, target_name)
                if res:
                    return res
        except Exception:
            pass
        return None

    target_node = find_node(root, symbol_name)
    if not target_node:
        logger.warning(f"Could not find symbol '{symbol_name}' in {file_path}")
        return False

    # Perform replacement
    try:
        new_source = content[: target_node.start_byte] + new_content + content[target_node.end_byte :]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_source)
        logger.info(f"Successfully updated '{symbol_name}' in {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write updates to {file_path}: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Perform semantic edits on a file.")
    parser.add_argument("file", help="File to edit")
    parser.add_argument("type", help="Symbol type")
    parser.add_argument("name", help="Symbol name (search string)")
    parser.add_argument("content", help="New content")
    args = parser.parse_args()

    if not semantic_replace(args.file, args.type, args.name, args.content):
        sys.exit(1)


if __name__ == "__main__":
    main()
