"""Rules for working on a repository that may be hostile. See docs/security-review.md for the threat model."""

import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Iterable, List, Optional, Union

MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_YAML_NODES = 1_000_000  # large CRD bundles are legitimate; alias bombs are far past this
REDACTED = "[REDACTED]"

_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]+")
# Secret names are matched as words (`access_key`, `accessKey`), so `author` and `connectTimeout` are left alone.
_WORDS = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
_SECRET_WORDS = {"secret", "secrets", "password", "passwd", "pass", "pwd", "token", "tokens", "credential",
                 "credentials", "private", "key", "keys", "apikey", "auth", "cert", "dsn"}
_SECRET_PART = re.compile(r"(?i)secret|passw|token|credential|api_?key|private_?key|conn(ection)?_?str")
_SECRET_VALUE = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY|\beyJ[\w-]{8,}\.[\w-]{8,}\.|\bAKIA[0-9A-Z]{16}\b|\bgh[pousr]_\w{30,}"
    r"|://[^/\s:@]+:[^/\s@]+@|(?i:passw\w*|pwd|token|secret|api[-_]?key)[\w-]*\s*[=:]\s*[^\s=:]"
    r"|^[\"']?(?=[A-Za-z0-9+/]*\d)(?=[A-Za-z0-9+/]*[A-Z])[A-Za-z0-9+/]{40,}={0,2}[\"']?$"
)

# Repository config can name programs for git to run; switch those off for every call on a target repository.
_GIT_HARDENING = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "safe.bareRepository=explicit"]

# A target must not be able to hide files from an audit with its own ignore files.
AST_GREP_SCAN_ALL = [
    arg for kind in ("hidden", "dot", "vcs", "parent", "exclude", "global") for arg in ("--no-ignore", kind)
] + ["--globs", "!**/node_modules/**", "--globs", "!**/.git/**"]


def git_argv(repo: Any) -> List[str]:
    return ["git", *_GIT_HARDENING, "-C", str(repo)]


def clean_text(value: Any, limit: int = 2000) -> str:
    """One line, bounded: text taken from a repository must not start a new line in what an agent reads."""
    return _CONTROL.sub(" ", str(value))[:limit]


def md_cell(value: Any) -> str:
    return clean_text(value, 500).replace("|", "\\|").replace("`", "'")


def clean_tree(value: Any) -> Any:
    """`clean_text` over every string in a loaded graph."""
    if isinstance(value, str):
        return _CONTROL.sub(" ", value)
    if isinstance(value, dict):
        return {clean_tree(k): clean_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean_tree(v) for v in value]
    return value


def inside(path: Any, roots: Iterable[Any]) -> bool:
    real = Path(os.path.realpath(path))
    return any(real == r or r in real.parents for r in (Path(os.path.realpath(x)) for x in roots))


def readable(path: Any, root: Any, max_bytes: Optional[int] = MAX_SOURCE_BYTES) -> bool:
    """A regular file of sane size whose name is printable and which, if it is a link, stays inside `root`."""
    if _CONTROL.search(str(path)):
        return False
    try:
        if os.path.islink(path) and not inside(path, [root]):
            return False
        info = os.stat(path)
    except OSError:
        return False
    return stat.S_ISREG(info.st_mode) and (max_bytes is None or info.st_size <= max_bytes)


def is_secret(name: str, value: Any) -> bool:
    words = {w.lower() for w in _WORDS.findall(str(name))}
    if words & _SECRET_WORDS or _SECRET_PART.search(str(name)):
        return True
    return bool(isinstance(value, str) and _SECRET_VALUE.search(value))


def has_local_filters(repo: Any) -> bool:
    """A checkout's own filter programs run during `git diff`, and git has no switch to turn them off."""
    found = subprocess.run([*git_argv(repo), "config", "--local", "--get-regexp", r"^filter\."], capture_output=True)
    return found.returncode == 0 and bool(found.stdout.strip())


def write_atomic(path: Any, text: Union[str, Iterable[str]], mode: Optional[int] = None) -> None:
    """Write through a fresh temporary file, so a link planted at the target or a fixed temp name is never followed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines([text] if isinstance(text, str) else text)
        if mode is None:  # what a plain open() would have given, so a strict umask is honoured
            mask = os.umask(0o077)
            os.umask(mask)
            mode = 0o666 & ~mask
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _too_big(obj: Any, limit: int) -> bool:
    """Count nodes as a walker would see them: YAML aliases are shared objects but are expanded on every visit."""
    stack, seen = [obj], 0
    while stack:
        node = stack.pop()
        seen += 1
        if seen > limit:
            return True
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return False


def yaml_documents(text: str, limit: int = MAX_YAML_NODES) -> List[Any]:
    """`safe_load_all` that raises `yaml.YAMLError` on alias bombs and absurd nesting."""
    import yaml  # only the YAML readers need PyYAML

    try:
        docs = list(yaml.safe_load_all(text))
    except RecursionError as exc:
        raise yaml.YAMLError("document is nested too deeply") from exc
    if _too_big(docs, limit):
        raise yaml.YAMLError("document expands past the node limit")
    return docs
