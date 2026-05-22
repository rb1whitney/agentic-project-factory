import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from tree_sitter import Parser
from tree_sitter_languages import get_language

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("repo_analyzer")


class RepoAnalyzer:
    def __init__(self, root_dir: str) -> None:
        self.root_dir: Path = Path(root_dir)
        self.parsers: Dict[str, Optional[Parser]] = {
            "java": self._setup_parser("java"),
            "hcl": self._setup_parser("hcl"),
            "yaml": self._setup_parser("yaml"),
        }
        self.symbol_map: Dict[str, List[Dict[str, Any]]] = {}

    def _setup_parser(self, lang_name: str) -> Optional[Parser]:
        try:
            lang = get_language(lang_name)
            parser = Parser()
            parser.set_language(lang)
            return parser
        except Exception as e:
            logger.debug(f"Could not setup parser for {lang_name}: {e}")
            return None

    def analyze(self) -> Dict[str, List[Dict[str, Any]]]:
        for path in self.root_dir.rglob("*"):
            if path.is_file():
                ext = path.suffix.lower()
                if ext == ".java":
                    self._parse_java(path)
                elif ext in [".tf", ".hcl"]:
                    self._parse_hcl(path)
                elif ext in [".yaml", ".yml"]:
                    self._parse_yaml_ansible(path)

        return self.symbol_map

    def _parse_java(self, path: Path) -> None:
        parser = self.parsers.get("java")
        if not parser:
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = parser.parse(content)
        root = tree.root_node

        symbols: List[Dict[str, Any]] = []
        query_str = """
        (class_declaration name: (identifier) @class_name)
        (method_declaration name: (identifier) @method_name)
        """
        try:
            query = get_language("java").query(query_str)
            captures = query.captures(root)

            for node, tag in captures:
                try:
                    symbols.append(
                        {
                            "type": tag,
                            "name": content[node.start_byte : node.end_byte].decode("utf-8"),
                            "line": node.start_point[0] + 1,
                        }
                    )
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"Error querying Java file {path}: {e}")

        if symbols:
            self.symbol_map[str(path.relative_to(self.root_dir))] = symbols

    def _parse_hcl(self, path: Path) -> None:
        parser = self.parsers.get("hcl")
        if not parser:
            return
        try:
            content = path.read_bytes()
        except IOError:
            return

        tree = parser.parse(content)
        root = tree.root_node

        symbols: List[Dict[str, Any]] = []
        query_str = """
        (block (identifier) @block_type (string_lit) @block_name)
        (block (identifier) @block_type_no_name)
        """
        try:
            query = get_language("hcl").query(query_str)
            captures = query.captures(root)

            for node, tag in captures:
                try:
                    symbols.append(
                        {
                            "type": tag,
                            "name": content[node.start_byte : node.end_byte].decode("utf-8").strip('"'),
                            "line": node.start_point[0] + 1,
                        }
                    )
                except UnicodeDecodeError:
                    continue
        except Exception as e:
            logger.warning(f"Error querying HCL file {path}: {e}")

        if symbols:
            self.symbol_map[str(path.relative_to(self.root_dir))] = symbols

    def _parse_yaml_ansible(self, path: Path) -> None:
        parser = self.parsers.get("yaml")
        if not parser:
            return
        # High level YAML analysis
        symbols: List[Dict[str, Any]] = []
        symbols.append({"type": "yaml_file", "name": path.name, "line": 1})
        self.symbol_map[str(path.relative_to(self.root_dir))] = symbols


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a repository for symbols.")
    parser.add_argument("dir", help="Directory to analyze")
    parser.add_argument("--output", default="symbol_map.json", help="Output JSON file")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        logger.error(f"Provided path is not a directory: {args.dir}")
        sys.exit(1)

    analyzer = RepoAnalyzer(args.dir)
    logger.info(f"Analyzing repository at {args.dir}...")
    symbol_map = analyzer.analyze()

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(symbol_map, f, indent=2)
        logger.info(f"Analysis complete. Symbol map saved to {args.output}")
    except IOError as e:
        logger.error(f"Failed to save symbol map to {args.output}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
