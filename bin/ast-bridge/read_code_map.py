import sys
import os
import argparse
import logging
from typing import List, Dict, Optional, Any
import tree_sitter
from pathlib import Path

# Production logging setup
logger = logging.getLogger('universal-skeleton')
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s', stream=sys.stderr)

class UnsupportedLanguage(Exception): pass
class FileTooLarge(Exception): pass
class ParseFailed(Exception): pass
class IndexError(Exception): pass

MAX_FILE_SIZE = 1024 * 1024 # 1MB

LANGUAGE_QUERIES = {
    "java": {
        "extension": ".java",
        "module": "tree_sitter_java",
        "query": """
            (package_declaration) @package
            (import_declaration) @import
            (class_declaration) @type
            (interface_declaration) @type
            (enum_declaration) @type
            (field_declaration) @member
            (constructor_declaration) @member
            (method_declaration) @member
        """
    },
    "python": {
        "extension": ".py",
        "module": "tree_sitter_python",
        "query": """
            (import_from_statement) @import
            (import_statement) @import
            (class_definition name: (identifier) @type)
            (function_definition name: (identifier) @member)
        """
    },
    "typescript": {
        "extension": ".ts",
        "module": "tree_sitter_typescript",
        "query": """
            (import_statement) @import
            (class_declaration name: (type_identifier) @type)
            (interface_declaration name: (type_identifier) @type)
            (method_definition name: (property_identifier) @member)
            (function_declaration name: (identifier) @member)
        """
    }
}

class UniversalExtractor:
    def __init__(self, lang_name: str, language: Any):
        self.lang_name = lang_name
        self.language = language
        self.query = language.query(LANGUAGE_QUERIES[lang_name]["query"])

    def extract(self, node: Any, source: bytes) -> List[Dict[str, Any]]:
        captures = self.query.captures(node)
        entries = []
        for n, tag in captures:
            entries.append({
                "type": tag,
                "text": source[n.start_byte:n.end_byte].decode("utf-8", errors="ignore"),
                "start": n.start_point,
                "end": n.end_point
            })
        return entries

def get_ts_language(lang_name: str):
    try:
        from tree_sitter_languages import get_language
        return get_language(lang_name)
    except ImportError:
        import importlib
        mod_name = LANGUAGE_QUERIES[lang_name]["module"]
        lang_mod = importlib.import_module(mod_name)
        return tree_sitter.Language(lang_mod.language())

def index_file(path: str) -> str:
    path_obj = Path(path)
    ext = path_obj.suffix.lower()
    
    lang_name = next((name for name, cfg in LANGUAGE_QUERIES.items() if cfg["extension"] == ext), None)
    if not lang_name:
        raise UnsupportedLanguage(f"No skeleton support for {ext}")
        
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if path_obj.stat().st_size > MAX_FILE_SIZE:
        raise FileTooLarge(f"File {path} exceeds size limit.")
        
    source = path_obj.read_bytes()
    lang = get_ts_language(lang_name)
    parser = tree_sitter.Parser()
    parser.set_language(lang)
    tree = parser.parse(source)
    
    if not tree:
        raise ParseFailed(f"Failed to parse {path}")
        
    extractor = UniversalExtractor(lang_name, lang)
    entries = extractor.extract(tree.root_node, source)
    return format_skeleton(entries, lang_name)

def format_skeleton(entries: List[Dict], lang_name: str) -> str:
    output = []
    current_type = None
    
    for entry in entries:
        t = entry["type"]
        text = entry["text"].split("{")[0].split(":")[0].strip()
        
        if t == "package":
            output.append(text)
        elif t == "import":
            output.append(text)
        elif t == "type":
            output.append(f"\n{text} {{")
            current_type = text
        elif t == "member":
            output.append(f"  {text}")
            
    if current_type:
        output.append("}")
        
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Universal Code Skeleton Generator.")
    parser.add_argument("file_path", help="Path to the source file.")
    args = parser.parse_args()
    
    try:
        skeleton = index_file(args.file_path)
        sys.stdout.write(skeleton + "\n")
    except Exception as e:
        logger.error(f"Error indexing {args.file_path}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
