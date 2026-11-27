#!/usr/bin/env python3
"""PreToolUse hook for Claude Code and Antigravity: send the agent to a code map only when a search is noisy.

The policy is "grep first; if grep returns too much, orient with the map, then search inside what the map names".
The hook measures the noise itself, so the agent needs no standing instruction:
  * a search whose pattern matches at most NOISE_MIN_HITS files is allowed untouched;
  * a search that matches more is denied once, with a reason naming the map command (NOISE_HINT);
  * after the agent runs a map command (NOISE_CMD_RE) or after NOISE_MAX_DENIES denials, searches are allowed again.

Payloads: Claude Code sends {"tool_name": "Grep"|"Bash"|..., "tool_input": {...}}; Antigravity sends
{"toolCall": {"name": "grep_search"|"run_command"|..., "args": {...}}, "workspacePaths": [...]}.
The reply is `permissionDecision` JSON for Claude and `decision` JSON for Antigravity.

Everything has a default so the hook works with no setup. Environment (all optional): NOISE_REPO (git checkout to
count in;
default the git root of the payload's working directory), NOISE_GLOB (files to count; default all tracked files),
NOISE_MIN_HITS (default 100), NOISE_HINT (map command named in the denial; default the sibling `semantic_query.py` and
`auto_context.py`), NOISE_NOTE (appended to the denial), NOISE_CMD_RE (what counts as using the map; default
`semantic_query\\.py|auto_context\\.py`), NOISE_MAX_DENIES (default 1), NOISE_STATE (state file; default one per
session,
keyed on the payload's session id or the parent process), NOISE_LOG (append-only decision log).
Measured in Finding 20: the gate stays silent on quiet searches and redirects noisy ones, but did not lower cost by
itself.
"""

import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_HINT = (
    f'python3 {HERE}/semantic_query.py --graph <graph.json> find-usages <name> (who uses a symbol) or '
    f'python3 {HERE}/auto_context.py "<task>" --src <dir> --max-tokens 8000 (a multi-file task)'
)

# Repository config can name programs for git to run; this hook runs git on every search, so switch them off.
GIT_HARDENING = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "safe.bareRepository=explicit"]
SEARCH_WORD = re.compile(r"(^|[\s;&|(])(grep|egrep|fgrep|rg|ag|ack|git\s+grep)\s")


def pattern_of(tool: str, args: dict) -> str | None:
    """The search pattern of a call, or None when the call is not a content search."""
    if tool in ("Grep", "grep_search"):
        return str(args.get("pattern") or args.get("Query") or args.get("query") or "") or None
    cmd = str(args.get("command") or args.get("CommandLine") or "") if tool in ("Bash", "run_command") else ""
    if not cmd or not SEARCH_WORD.search(cmd):
        return None
    try:
        words = shlex.split(cmd)
    except ValueError:
        words = cmd.split()
    skip_next = {"-e", "-f", "-g", "--glob", "-t", "--type", "-m", "-A", "-B", "-C", "--include", "--exclude"}
    args_left, explicit = [], None
    it = iter(words)
    for w in it:
        if w in ("-e", "--regexp"):
            explicit = next(it, None)
        elif w in skip_next:
            next(it, None)
        elif not w.startswith("-"):
            args_left.append(w)
    if explicit:
        return explicit
    # words: [grep|rg|git, (grep)], pattern, paths...
    lead = 2 if args_left[:2] == ["git", "grep"] else 1
    return args_left[lead] if len(args_left) > lead else None


def count_hits(repo: str, pattern: str, glob: str, timeout: float = 8.0) -> int:
    for flag in ("-E", "-F"):
        proc = subprocess.run(
            ["git", *GIT_HARDENING, "-C", repo, "grep", "--no-textconv", "-l", flag, "-e", pattern,
             *(["--", glob] if glob else [])],
            capture_output=True, text=True, timeout=timeout,
        )  # fmt: skip
        if proc.returncode in (0, 1):
            return len(proc.stdout.split())
    return 0  # an unreadable pattern is not evidence of noise


def decide(payload: dict, env=os.environ) -> tuple[bool, str, str]:
    """Return (deny, reason, label)."""
    call = payload.get("toolCall") or {}
    tool = payload.get("tool_name") or call.get("name", "")
    args = payload.get("tool_input") or call.get("args") or {}
    repo = env.get("NOISE_REPO") or _git_root(payload)
    state = Path(env.get("NOISE_STATE") or _default_state(payload, repo))
    saved = _load(state)
    cmd = str(args.get("command") or args.get("CommandLine") or "")
    map_cmd = env.get("NOISE_CMD_RE", r"semantic_query\.py|auto_context\.py")
    if tool in ("Bash", "run_command") and re.search(map_cmd, cmd):
        state.write_text(json.dumps({"map_used": True, "denies": saved.get("denies", 0)}))
        return False, "", "map-command"
    pattern = pattern_of(tool, args)
    if pattern is None:
        return False, "", "not-a-search"
    if saved.get("map_used"):
        return False, "", "map-already-used"
    if saved.get("denies", 0) >= int(env.get("NOISE_MAX_DENIES", "1")):
        return False, "", "deny-limit-reached"
    hits = count_hits(repo, pattern, env.get("NOISE_GLOB", ""))
    if hits <= int(env.get("NOISE_MIN_HITS", "100")):
        return False, "", f"quiet({hits})"
    state.write_text(json.dumps({"map_used": False, "denies": saved.get("denies", 0) + 1}))
    hint = env.get("NOISE_HINT", DEFAULT_HINT)
    reason = (
        f"This search matches {hits} files, too many to read. Orient first with `{hint}`, "
        "then search or read only the files it names."
    )
    if env.get("NOISE_NOTE"):
        reason += " " + env["NOISE_NOTE"]
    return True, reason, f"denied({hits})"


def _git_root(payload: dict) -> str:
    cwd = payload.get("cwd") or ((payload.get("workspacePaths") or [None])[0]) or os.getcwd()
    cmd = ["git", *GIT_HARDENING, "-C", str(cwd), "rev-parse", "--show-toplevel"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    return out.stdout.strip() or str(cwd)


def _private_dir(path: Path) -> Path:
    """Create `path` as 0700, or raise: a shared temp directory lets another user plant a link or a file first."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise OSError(f"refusing {path}: not a directory owned by this user")
    path.chmod(0o700)
    return path


def _default_state(payload: dict, repo: str) -> Path:
    key = payload.get("session_id") or f"{repo}:{os.getppid()}"
    folder = _private_dir(Path(tempfile.gettempdir()) / f"noise_gate-{os.getuid()}")
    return folder / f"{hashlib.sha1(str(key).encode(), usedforsecurity=False).hexdigest()[:12]}.json"


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def append_log(path: str, line: str) -> None:
    """Append without following a link someone planted at the log path; a log failure never affects the hook."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "a") as fh:
            if os.fstat(fd).st_uid == os.getuid():  # not a file someone else created for us to fill
                fh.write(line)
    except OSError:
        pass


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    agy = "toolCall" in payload
    try:
        deny, reason, label = decide(payload)
    except Exception as exc:  # a hook must never break the agent
        deny, reason, label = False, "", f"error:{type(exc).__name__}"
    if os.environ.get("NOISE_LOG"):
        append_log(os.environ["NOISE_LOG"], f"{time.strftime('%H:%M:%S')}\t{label}\n")
    if agy:
        print(json.dumps({"decision": "deny", "reason": reason} if deny else {"decision": "allow"}))
    elif deny:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))  # fmt: skip


if __name__ == "__main__":
    main()
