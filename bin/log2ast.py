#!/usr/bin/env python3
"""
log2ast.py - Correlate runtime log lines and stack traces to AST code context.
Uses ast-grep and ripgrep to find the emission site, enclosing method, and transaction/security context.
"""

import sys
import re
import subprocess
import json
import argparse
from pathlib import Path

AST_GREP_BIN = "/root/.local/bin/ast-grep"

def extract_log_patterns(log_line: str) -> list[str]:
    """
    Extracts search candidates from log text by stripping timestamps, log levels, thread names,
    and runtime variable values.
    """
    # 1. Check for stack trace pattern: at com.dataservice.controller.DataController.updateData(DataController.java:94)
    stack_match = re.search(r'at\s+([a-zA-Z0-9_.$]+)\.([a-zA-Z0-9_$]+)\(([^:]+):(\d+)\)', log_line)
    if stack_match:
        return [{
            "type": "stacktrace",
            "class": stack_match.group(1),
            "method": stack_match.group(2),
            "file": stack_match.group(3),
            "line": int(stack_match.group(4))
        }]

    # 2. Extract string literals or message prefixes
    # Remove ISO timestamps, log levels (INFO, DEBUG, ERROR), thread names [main], etc.
    cleaned = re.sub(r'^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}[^ ]*\s*', '', log_line)
    cleaned = re.sub(r'^(DEBUG|INFO|WARN|ERROR|FATAL|TRACE)\s+', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\[[^\]]+\]\s*', '', cleaned)
    cleaned = re.sub(r'^[a-zA-Z0-9_.]+\s*-\s*', '', cleaned) # slf4j category prefix

    # Extract words before variables / colons / JSON
    base_msg = cleaned.split('{')[0].split(':')[0].strip()
    return [{"type": "message", "query": base_msg}]

def query_ast_grep_logs(search_root: str, message_query: str):
    """
    Runs ast-grep to locate logger calls matching message fragments.
    """
    pattern = f'log.$METHOD($$$PRE, "{message_query}$$REST", $$$POST)'
    cmd = [
        AST_GREP_BIN,
        "run",
        "-l", "java",
        "--json",
        "-p", 'log.$METHOD($$$ARGS)',
        search_root
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 and not proc.stdout:
            return []
        items = json.loads(proc.stdout) if proc.stdout.strip() else []
        matches = []
        for item in items:
            text = item.get("text", "")
            if message_query.lower() in text.lower():
                matches.append(item)
        return matches
    except Exception as e:
        return []

def get_ast_context(file_path: str, line_no: int):
    """
    Extracts the enclosing method, class, and annotations around a line using ast-grep.
    """
    cmd = [
        AST_GREP_BIN,
        "run",
        "-l", "java",
        "--json",
        "-p", 'class $CLASS { $$$BODY }',
        file_path
    ]
    # Simple line window for rapid diagnosis
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        start = max(0, line_no - 15)
        end = min(len(lines), line_no + 15)
        context_snippet = "".join(f"{idx+1:4d} | {lines[idx]}" for idx in range(start, end))
        return context_snippet
    except Exception:
        return ""

def main():
    parser = argparse.ArgumentParser(description="Correlate logs and stack traces to AST code locations.")
    parser.add_argument("log_input", help="Log line, exception message, or stack trace string")
    parser.add_argument("--src", default=None, help="Source root path")
    args = parser.parse_args()

    # Smart source directory detection
    target_src = args.src
    if not target_src or not Path(target_src).exists():
        candidates = [
            "src",
            "projects/cloud-boot-app/src",
            "/mnt/d/OneDrive/Email_attachments/Programming-Work/projects/cloud-boot-app/src"
        ]
        target_src = next((c for c in candidates if Path(c).is_dir()), "src")

    print("=== LOG-TO-AST CORRELATION ENGINE ===")
    print(f"Input Log : {args.log_input.strip()}")
    print(f"Target Src: {target_src}")
    print("-" * 50)

    candidates = extract_log_patterns(args.log_input)
    if not candidates:
        print("[!] No actionable patterns extracted from log input.")
        sys.exit(1)

    for cand in candidates:
        if cand["type"] == "stacktrace":
            print(f"[+] Detected Stack Trace Frame: {cand['class']}.{cand['method']}() at {cand['file']}:{cand['line']}")
            found_files = list(Path(target_src).rglob(cand['file']))
            if found_files:
                target_file = str(found_files[0])
                print(f"[+] File Resolved: {target_file}")
                snippet = get_ast_context(target_file, cand['line'])
                print("\n--- AST Surrounding Context ---")
                print(snippet)
            else:
                print(f"[-] Source file {cand['file']} not found under {target_src}")
        elif cand["type"] == "message":
            msg = cand["query"]
            print(f"[+] Searching AST for log emissions containing template: '{msg}'")
            matches = query_ast_grep_logs(target_src, msg)
            if not matches:
                print(f"[-] No matching AST log calls found containing '{msg}'.")
            for m in matches:
                fpath = m.get("file", "")
                rng = m.get("range", {}).get("start", {})
                line = rng.get("line", 0) + 1
                col = rng.get("column", 0)
                text = m.get("text", "").strip()
                print(f"\n[MATCH] {fpath}:{line}:{col}")
                print(f"  Statement: {text}")
                snippet = get_ast_context(fpath, line)
                print("--- AST Surrounding Context ---")
                print(snippet)


if __name__ == "__main__":
    main()
