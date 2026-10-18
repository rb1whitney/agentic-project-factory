#!/usr/bin/env python3
"""
hydrate_policies.py - Policy-as-Code Hydrator & Semgrep/ast-grep Rule Transpiler.

Capabilities:
1. Curated 150-Rule Baseline (50 Python + 50 Java + 50 Go across SEC, REL, PERF, OPS, COST, SUS).
2. Semgrep YAML -> ast-grep structural rule transpiler (`transpile_semgrep_rule`, `import_semgrep_dir`).
3. Upstream git sparse-checkout fetcher (`--fetch-upstream`) for `semgrep/semgrep-rules` and `ast-grep` catalogs.
4. Live `ast-grep scan` canary validation (`validate_policies`) to guarantee 100% of emitted `.md` policies
   parse and execute cleanly.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


DEFAULT_POLICIES_DIR = SCRIPT_DIR.parent / "resources" / "policies"

LANG_MAP = {
    "python": "python",
    "py": "python",
    "python3": "python",
    "java": "java",
    "go": "go",
    "golang": "go",
}

SEVERITY_MAP = {
    "ERROR": "HIGH",
    "HIGH": "HIGH",
    "CRITICAL": "CRITICAL",
    "WARNING": "MEDIUM",
    "MEDIUM": "MEDIUM",
    "INFO": "LOW",
    "LOW": "LOW",
}

CATEGORY_TO_PILLAR = {
    "security": "SEC",
    "sec": "SEC",
    "correctness": "REL",
    "reliability": "REL",
    "rel": "REL",
    "performance": "PERF",
    "perf": "PERF",
    "best-practice": "OPS",
    "operations": "OPS",
    "ops": "OPS",
    "cost": "COST",
    "maintainability": "SUS",
    "sustainability": "SUS",
    "sus": "SUS",
}


def _convert_semgrep_pattern_str(pat: str) -> Optional[str]:
    """Convert a Semgrep pattern string into an ast-grep compatible pattern string."""
    if not isinstance(pat, str):
        return None
    s = pat.strip()
    if not s:
        return None
    # Reject Semgrep-specific typed metavariables like `($T $X)` or deep statement ellipses `...` on standalone lines
    if re.search(r"\(\$[A-Z0-9_]+\s+\$[A-Z0-9_]+\)", s):
        return None
    if re.search(r"(^|\n)\s*\.\.\.\s*($|\n)", s):
        return None
    # Convert Semgrep `$...X` variadic metavariables to ast-grep `$$$X`
    s = re.sub(r"\$\.\.\.([A-Z_][A-Z0-9_]*)", r"$$$\1", s)
    # Convert Semgrep `...` inside argument lists `(..., ...)` to `$$$`
    s = re.sub(r"\(\s*\.\.\.\s*\)", "($$$ARGS)", s)
    s = re.sub(r",\s*\.\.\.\s*\)", ", $$$ARGS)", s)
    s = re.sub(r"\(\s*\.\.\.\s*,", "($$$LEAD,", s)
    if "..." in s:
        return None
    return s


def _convert_semgrep_clause(clause: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert a single Semgrep pattern clause into an ast-grep rule object."""
    if "pattern" in clause and isinstance(clause["pattern"], str):
        p = _convert_semgrep_pattern_str(clause["pattern"])
        return {"pattern": p} if p else None
    if "pattern-not" in clause and isinstance(clause["pattern-not"], str):
        p = _convert_semgrep_pattern_str(clause["pattern-not"])
        return {"not": {"pattern": p}} if p else None
    if "pattern-inside" in clause and isinstance(clause["pattern-inside"], str):
        p = _convert_semgrep_pattern_str(clause["pattern-inside"])
        return {"inside": {"pattern": p, "stopBy": "end"}} if p else None
    if "pattern-not-inside" in clause and isinstance(clause["pattern-not-inside"], str):
        p = _convert_semgrep_pattern_str(clause["pattern-not-inside"])
        return {"not": {"inside": {"pattern": p, "stopBy": "end"}}} if p else None
    if "pattern-either" in clause and isinstance(clause["pattern-either"], list):
        sub_rules = []
        for item in clause["pattern-either"]:
            if isinstance(item, dict):
                conv = _convert_semgrep_clause(item)
                if not conv:
                    return None
                sub_rules.append(conv)
            elif isinstance(item, str):
                p = _convert_semgrep_pattern_str(item)
                if not p:
                    return None
                sub_rules.append({"pattern": p})
        return {"any": sub_rules} if sub_rules else None
    return None


def transpile_semgrep_rule(raw_rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transpile a single Semgrep rule dictionary into a normalized Policy-as-Code dict
    compatible with `well_architected_audit.py`. Returns None if the rule uses
    unsupported Semgrep features (e.g. taint mode, regex-only, metavariable-regex).
    """
    if not isinstance(raw_rule, dict):
        return None
    rid = str(raw_rule.get("id", "")).strip()
    if not rid:
        return None
    if raw_rule.get("mode") == "taint":
        return None
    unsupported_keys = {
        "pattern-regex",
        "pattern-not-regex",
        "metavariable-regex",
        "metavariable-pattern",
        "metavariable-comparison",
        "pattern-sinks",
        "pattern-sources",
        "r2c-internal-project-depends-on",
    }
    if any(k in raw_rule for k in unsupported_keys):
        return None

    langs = raw_rule.get("languages") or []
    target_lang = None
    for lang in langs:
        mapped = LANG_MAP.get(str(lang).lower())
        if mapped:
            target_lang = mapped
            break
    if not target_lang:
        return None

    ast_rule: Optional[Dict[str, Any]] = None
    if "pattern" in raw_rule and isinstance(raw_rule["pattern"], str):
        p = _convert_semgrep_pattern_str(raw_rule["pattern"])
        if p:
            ast_rule = {"pattern": p}
    elif "pattern-either" in raw_rule and isinstance(raw_rule["pattern-either"], list):
        ast_rule = _convert_semgrep_clause({"pattern-either": raw_rule["pattern-either"]})
    elif "patterns" in raw_rule and isinstance(raw_rule["patterns"], list):
        all_clauses = []
        for cl in raw_rule["patterns"]:
            if not isinstance(cl, dict) or any(k in cl for k in unsupported_keys):
                return None
            conv = _convert_semgrep_clause(cl)
            if not conv:
                return None
            all_clauses.append(conv)
        if all_clauses:
            ast_rule = all_clauses[0] if len(all_clauses) == 1 else {"all": all_clauses}

    if not ast_rule:
        return None

    meta = raw_rule.get("metadata") if isinstance(raw_rule.get("metadata"), dict) else {}
    cat = str(meta.get("category", "")).lower()
    pillar = CATEGORY_TO_PILLAR.get(cat, "SEC" if ("cwe" in meta or "owasp" in meta) else "REL")
    raw_sev = str(raw_rule.get("severity", "WARNING")).upper()
    severity = SEVERITY_MAP.get(raw_sev, "MEDIUM")
    msg = " ".join(str(raw_rule.get("message", rid)).split())
    fix = str(
        raw_rule.get("fix") or meta.get("references", ["Follow language security & reliability best practices."])[0]
        if isinstance(meta.get("references"), list) and meta.get("references")
        else "Refactor pattern to comply with Well-Architected policy."
    )

    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "-", f"sg-{target_lang}-{rid}").lower()
    return {
        "id": clean_id,
        "pillar": pillar,
        "severity": severity,
        "language": target_lang,
        "problem": msg[:280],
        "fix": str(fix)[:240],
        "rule": ast_rule,
    }


def import_semgrep_dir(semgrep_dir: str) -> List[Dict[str, Any]]:
    """Scan a directory of Semgrep `.yaml`/`.yml` files and transpile compatible structural rules."""
    try:
        import yaml
    except ImportError:
        return []
    root = Path(semgrep_dir)
    if not root.is_dir():
        return []
    transpiled: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for yml_path in sorted(list(root.rglob("*.yml")) + list(root.rglob("*.yaml"))):
        if yml_path.name.endswith(".test.yml") or yml_path.name.endswith(".test.yaml"):
            continue
        try:
            doc = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("rules"), list):
            continue
        for r in doc["rules"]:
            pol = transpile_semgrep_rule(r)
            if pol and pol["id"] not in seen_ids:
                seen_ids.add(pol["id"])
                transpiled.append(pol)
    return transpiled


def import_astgrep_dir(astgrep_dir: str) -> List[Dict[str, Any]]:
    """Scan a directory of native ast-grep `.yml`/`.yaml` rules and normalize into Policy-as-Code entries."""
    try:
        import yaml
    except ImportError:
        return []
    root = Path(astgrep_dir)
    if not root.is_dir():
        return []
    imported: List[Dict[str, Any]] = []
    seen_ids: set = set()
    for yml_path in sorted(list(root.rglob("*.yml")) + list(root.rglob("*.yaml"))):
        if yml_path.name == "sgconfig.yml":
            continue
        try:
            docs = list(yaml.safe_load_all(yml_path.read_text(encoding="utf-8")))
        except Exception:
            continue
        for doc in docs:
            if not isinstance(doc, dict) or not doc.get("id") or not doc.get("rule"):
                continue
            lang = LANG_MAP.get(str(doc.get("language", "")).lower())
            if not lang:
                continue
            rid = re.sub(r"[^a-zA-Z0-9_-]", "-", str(doc["id"])).lower()
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            meta = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            pillar = str(
                meta.get("pillar") or CATEGORY_TO_PILLAR.get(str(meta.get("category", "")).lower(), "OPS")
            ).upper()
            sev = SEVERITY_MAP.get(str(doc.get("severity", "MEDIUM")).upper(), "MEDIUM")
            imported.append(
                {
                    "id": rid,
                    "pillar": pillar if pillar in {"SEC", "REL", "OPS", "PERF", "COST", "SUS"} else "OPS",
                    "severity": sev,
                    "language": lang,
                    "problem": " ".join(str(doc.get("message", rid)).split()),
                    "fix": " ".join(
                        str(
                            doc.get("note") or doc.get("fix") or "Refactor to satisfy ast-grep structural policy."
                        ).split()
                    ),
                    "rule": doc["rule"],
                    "constraints": doc.get("constraints"),
                }
            )
    return imported


def validate_policies_with_ast_grep(policies: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Canary-validate each policy against `ast-grep scan` on dummy Python/Java/Go source files.
    Returns `(valid_policies, quarantined_ids)`.
    """
    try:
        import yaml
    except ImportError:
        return policies, []

    if not policies:
        return [], []

    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        src_dir = troot / "canary_src"
        src_dir.mkdir()
        (src_dir / "sample.py").write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
        (src_dir / "Sample.java").write_text("public class Sample { void f() {} }\n", encoding="utf-8")
        (src_dir / "sample.go").write_text("package main\nfunc f() {}\n", encoding="utf-8")

        # First try batch validation (fast path)
        rules_dir = troot / "rules"
        rules_dir.mkdir()
        for pol in policies:
            rdoc = {"id": pol["id"], "language": pol["language"], "rule": pol["rule"]}
            if pol.get("constraints"):
                rdoc["constraints"] = pol["constraints"]
            (rules_dir / f"{pol['id']}.yml").write_text(yaml.safe_dump(rdoc, sort_keys=False), encoding="utf-8")
        sg_cfg = troot / "sgconfig.yml"
        sg_cfg.write_text("ruleDirs:\n  - rules\n", encoding="utf-8")

        proc = subprocess.run(
            ["ast-grep", "scan", "--config", str(sg_cfg), "--json=stream", str(src_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and "Cannot parse rule" not in (proc.stderr or ""):
            return policies, []

        # If batch had a bad rule, isolate individually
        valid: List[Dict[str, Any]] = []
        quarantined: List[str] = []
        for pol in policies:
            single_dir = troot / f"single_{pol['id']}"
            single_dir.mkdir(exist_ok=True)
            rfile = single_dir / "rule.yml"
            rdoc = {"id": pol["id"], "language": pol["language"], "rule": pol["rule"]}
            if pol.get("constraints"):
                rdoc["constraints"] = pol["constraints"]
            rfile.write_text(yaml.safe_dump(rdoc, sort_keys=False), encoding="utf-8")
            p = subprocess.run(
                ["ast-grep", "scan", "--rule", str(rfile), "--json=stream", str(src_dir)],
                capture_output=True,
                text=True,
                check=False,
            )
            if p.returncode == 0 and "Cannot parse rule" not in (p.stderr or ""):
                valid.append(pol)
            else:
                quarantined.append(pol["id"])
        return valid, quarantined


def _rule_entry(
    rid: str,
    pillar: str,
    severity: str,
    language: str,
    pattern: Any,
    problem: str,
    fix: str,
    inside: Optional[Dict[str, Any]] = None,
    not_rule: Optional[Dict[str, Any]] = None,
    constraints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper to construct a compact policy dictionary."""
    if isinstance(pattern, dict):
        rule_obj: Dict[str, Any] = dict(pattern)
    else:
        rule_obj = {"pattern": pattern}
    if inside:
        rule_obj["inside"] = inside
    if not_rule:
        rule_obj["not"] = not_rule
    entry: Dict[str, Any] = {
        "id": rid,
        "pillar": pillar,
        "severity": severity,
        "language": language,
        "problem": problem,
        "fix": fix,
        "rule": rule_obj,
    }
    if constraints:
        entry["constraints"] = constraints
    return entry


def build_curated_150_policies() -> List[Dict[str, Any]]:
    """Return 150 verified AST policies (50 Python, 50 Java, 50 Go) across the 6 AWS Well-Architected Pillars."""
    py_rules: List[Dict[str, Any]] = [
        # SEC (12)
        _rule_entry(
            "wa-py-sec-eval",
            "SEC",
            "CRITICAL",
            "python",
            "eval($$$ARGS)",
            "Dynamic code execution via `eval()` enables arbitrary code injection.",
            "Use `ast.literal_eval()` or explicit parsers.",
        ),
        _rule_entry(
            "wa-py-sec-exec",
            "SEC",
            "CRITICAL",
            "python",
            "exec($$$ARGS)",
            "Dynamic code execution via `exec()` enables arbitrary code execution.",
            "Remove `exec()` and use structured dispatch tables.",
        ),
        _rule_entry(
            "wa-py-sec-os-system",
            "SEC",
            "CRITICAL",
            "python",
            "os.system($$$ARGS)",
            "`os.system()` invokes a subshell vulnerable to command injection.",
            "Use `subprocess.run([cmd, arg], shell=False, check=True)`.",
        ),
        _rule_entry(
            "wa-py-sec-os-popen",
            "SEC",
            "HIGH",
            "python",
            "os.popen($$$ARGS)",
            "`os.popen()` invokes a shell command stream vulnerable to injection.",
            "Use `subprocess.run(..., shell=False, capture_output=True)`.",
        ),
        _rule_entry(
            "wa-py-sec-pickle-loads",
            "SEC",
            "CRITICAL",
            "python",
            "pickle.loads($$$ARGS)",
            "`pickle.loads()` executes arbitrary bytecode on untrusted payloads.",
            "Use `json.loads()` or `msgpack` with strict schema validation.",
        ),
        _rule_entry(
            "wa-py-sec-pickle-load",
            "SEC",
            "CRITICAL",
            "python",
            "pickle.load($$$ARGS)",
            "`pickle.load()` deserializes untrusted streams with arbitrary code execution.",
            "Use `json.load()` or safe serialization formats.",
        ),
        _rule_entry(
            "wa-py-sec-marshal-loads",
            "SEC",
            "HIGH",
            "python",
            "marshal.loads($$$ARGS)",
            "`marshal.loads()` is not secure against erroneous or maliciously constructed data.",
            "Use `json.loads()` instead of `marshal`.",
        ),
        _rule_entry(
            "wa-py-sec-shelve-open",
            "SEC",
            "HIGH",
            "python",
            "shelve.open($$$ARGS)",
            "`shelve` is backed by `pickle` and can execute arbitrary code when loading.",
            "Use `sqlite3` or JSON storage instead.",
        ),
        _rule_entry(
            "wa-py-sec-md5",
            "SEC",
            "MEDIUM",
            "python",
            "hashlib.md5($$$ARGS)",
            "MD5 is cryptographically broken and unsuitable for security digests.",
            "Use `hashlib.sha256()` or `hashlib.blake2b()`.",
        ),
        _rule_entry(
            "wa-py-sec-sha1",
            "SEC",
            "MEDIUM",
            "python",
            "hashlib.sha1($$$ARGS)",
            "SHA-1 is vulnerable to collision attacks.",
            "Use `hashlib.sha256()` or stronger.",
        ),
        _rule_entry(
            "wa-py-sec-mktemp",
            "SEC",
            "HIGH",
            "python",
            "tempfile.mktemp($$$ARGS)",
            "`tempfile.mktemp()` has an inherent TOCTOU symlink race condition.",
            "Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()`.",
        ),
        _rule_entry(
            "wa-py-sec-ssl-unverified",
            "SEC",
            "CRITICAL",
            "python",
            "ssl._create_unverified_context($$$ARGS)",
            "Disabling SSL certificate verification exposes connections to MITM attacks.",
            "Use `ssl.create_default_context()`.",
        ),
        # REL (12)
        _rule_entry(
            "wa-py-rel-asyncio-create-task-unawaited",
            "REL",
            "MEDIUM",
            "python",
            "asyncio.create_task($CORO)",
            (
                "Background task created with `asyncio.create_task()` should retain "
                "a reference to prevent GC disappearance."
            ),
            "Store task in a set (`tasks.add(task); task.add_done_callback(tasks.discard)`).",
        ),
        _rule_entry(
            "wa-py-rel-urllib-urlopen",
            "REL",
            "HIGH",
            "python",
            "urllib.request.urlopen($URL)",
            "`urlopen()` called with a single positional argument has no timeout and can hang indefinitely.",
            "Pass an explicit `timeout=10` argument.",
        ),
        _rule_entry(
            "wa-py-rel-requests-get-single-arg",
            "REL",
            "HIGH",
            "python",
            "requests.get($URL)",
            "`requests.get($URL)` without `timeout=` can block worker threads forever.",
            "Pass `timeout=(3.05, 10)` to all `requests` calls.",
        ),
        _rule_entry(
            "wa-py-rel-requests-post-single-arg",
            "REL",
            "HIGH",
            "python",
            "requests.post($URL)",
            "`requests.post($URL)` without `timeout=` can hang indefinitely.",
            "Pass `timeout=(3.05, 10)` to all `requests` calls.",
        ),
        _rule_entry(
            "wa-py-rel-sys-exit",
            "REL",
            "MEDIUM",
            "python",
            "sys.exit($$$ARGS)",
            "Direct `sys.exit()` inside library or handler code terminates the worker process abruptly.",
            "Raise a domain exception and handle exit only in CLI `main()`.",
        ),
        _rule_entry(
            "wa-py-rel-os-exit",
            "REL",
            "HIGH",
            "python",
            "os._exit($$$ARGS)",
            "`os._exit()` terminates immediately without running `finally` blocks or flushing stdio buffers.",
            "Use normal exception propagation or `sys.exit()` at entrypoint.",
        ),
        _rule_entry(
            "wa-py-rel-time-sleep-in-except",
            "REL",
            "MEDIUM",
            "python",
            "time.sleep($$$ARGS)",
            "Fixed `time.sleep()` inside `except` block causes thundering-herd retries.",
            "Use exponential backoff with jitter (`tenacity` or `random.uniform`).",
            inside={"kind": "except_clause", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-rel-thread-start-in-loop",
            "REL",
            "HIGH",
            "python",
            "threading.Thread($$$ARGS).start()",
            "Spawning unbounded threads inside a loop risks OS thread exhaustion.",
            "Use `concurrent.futures.ThreadPoolExecutor(max_workers=N)`.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-rel-subprocess-popen-in-loop",
            "REL",
            "HIGH",
            "python",
            "subprocess.Popen($$$ARGS)",
            "Spawning `subprocess.Popen` in a loop without bounded concurrency leaks child processes/file descriptors.",
            "Use bounded worker pools or `subprocess.run` with timeouts.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-rel-lock-acquire",
            "REL",
            "MEDIUM",
            "python",
            "$LOCK.acquire()",
            "Manual `.acquire()` without `with lock:` risks permanent deadlock if an exception occurs.",
            "Use `with lock:` context manager.",
        ),
        _rule_entry(
            "wa-py-rel-open-in-loop",
            "REL",
            "MEDIUM",
            "python",
            "open($PATH)",
            "Opening files repeatedly inside a loop increases file-descriptor churn and I/O latency.",
            "Hoist file open outside loop or batch writes.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-rel-asyncio-run-in-async",
            "REL",
            "HIGH",
            "python",
            "asyncio.run($$$ARGS)",
            (
                "Calling `asyncio.run()` inside an `async def` raises "
                "`RuntimeError: Cannot run the event loop while another loop is running`."
            ),
            "Await the coroutine directly (`await coro`).",
            inside={"kind": "function_definition", "regex": r"^async\s+def\b", "stopBy": "end"},
        ),
        # PERF (10)
        _rule_entry(
            "wa-py-perf-sleep-in-async",
            "PERF",
            "HIGH",
            "python",
            "time.sleep($$$ARGS)",
            "Blocking `time.sleep()` inside `async def` freezes the entire asyncio event loop.",
            "Replace with `await asyncio.sleep(...)`.",
            inside={"kind": "function_definition", "regex": r"^async\s+def\b", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-re-compile-in-loop",
            "PERF",
            "MEDIUM",
            "python",
            "re.compile($$$ARGS)",
            "Compiling regex via `re.compile()` inside a loop wastes CPU on every iteration.",
            "Hoist `re.compile()` to a module-level constant.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-json-loads-in-loop",
            "PERF",
            "MEDIUM",
            "python",
            "json.loads($$$ARGS)",
            "Repeated `json.loads()` inside a loop amplifies parsing CPU overhead.",
            "Use JSONL streaming or batch parse outside hot loops.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-deepcopy-in-loop",
            "PERF",
            "HIGH",
            "python",
            "copy.deepcopy($$$ARGS)",
            "`copy.deepcopy()` inside a loop causes quadratic object allocation and GC pressure.",
            "Use shallow copy (`copy.copy`), structural sharing, or immutable tuples/dataclasses.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-df-iterrows",
            "PERF",
            "HIGH",
            "python",
            "$DF.iterrows()",
            "Pandas `.iterrows()` boxes every row into a `Series`, running ~100x slower than vectorized operations.",
            "Use vectorized Pandas expressions or `.itertuples()`.",
        ),
        _rule_entry(
            "wa-py-perf-requests-in-async",
            "PERF",
            "HIGH",
            "python",
            "requests.$METHOD($$$ARGS)",
            "Synchronous `requests` call inside `async def` blocks the event loop thread.",
            "Use `httpx.AsyncClient` or `aiohttp`.",
            inside={"kind": "function_definition", "regex": r"^async\s+def\b", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-glob-in-loop",
            "PERF",
            "MEDIUM",
            "python",
            "glob.glob($$$ARGS)",
            "Filesystem `glob.glob()` inside a loop triggers repeated directory walks.",
            "Hoist directory discovery outside the loop or use `os.scandir()`.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-path-rglob-in-loop",
            "PERF",
            "HIGH",
            "python",
            "$P.rglob($$$ARGS)",
            "Recursive `.rglob()` inside a loop causes O(N * files) filesystem stat storms.",
            "Run `.rglob()` once before the loop and index paths in memory.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-subprocess-in-loop",
            "PERF",
            "HIGH",
            "python",
            "subprocess.run($$$ARGS)",
            "Spawning `subprocess.run()` inside a loop incurs OS fork/exec overhead per item.",
            "Batch arguments into a single CLI invocation.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-perf-sqlite-connect-in-loop",
            "PERF",
            "HIGH",
            "python",
            "sqlite3.connect($$$ARGS)",
            (
                "Opening a new `sqlite3.connect()` inside a loop wastes connection "
                "setup and prevents transaction batching."
            ),
            "Create connection once outside the loop and commit in batches.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        # OPS (6)
        _rule_entry(
            "wa-py-ops-pdb-set-trace",
            "OPS",
            "HIGH",
            "python",
            "pdb.set_trace()",
            "Leftover `pdb.set_trace()` halts production workers waiting for interactive stdin.",
            "Remove interactive debugger statements before committing.",
        ),
        _rule_entry(
            "wa-py-ops-breakpoint",
            "OPS",
            "HIGH",
            "python",
            "breakpoint()",
            "Leftover `breakpoint()` halts production execution.",
            "Remove `breakpoint()` calls.",
        ),
        _rule_entry(
            "wa-py-ops-logging-basicconfig-in-func",
            "OPS",
            "LOW",
            "python",
            "logging.basicConfig($$$ARGS)",
            "Calling `logging.basicConfig()` inside a function mutates global root logger handlers.",
            "Configure logging once at application entrypoint.",
            inside={"kind": "function_definition", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-ops-warnings-filterwarnings-ignore",
            "OPS",
            "MEDIUM",
            "python",
            'warnings.filterwarnings("ignore")',
            "Globally silencing all warnings hides deprecation and runtime safety alerts.",
            "Scope `warnings.catch_warnings()` to specific warning classes.",
        ),
        _rule_entry(
            "wa-py-ops-traceback-print-exc",
            "OPS",
            "LOW",
            "python",
            "traceback.print_exc()",
            "`traceback.print_exc()` writes unstructured stack traces to stderr bypassing structured log aggregators.",
            "Use `logger.exception(...)`.",
        ),
        _rule_entry(
            "wa-py-ops-raise-base-exception",
            "OPS",
            "MEDIUM",
            "python",
            "raise Exception($$$ARGS)",
            "Raising generic `Exception` prevents callers from catching specific failure modes.",
            "Raise a specific domain or built-in exception subclass.",
        ),
        # COST (5)
        _rule_entry(
            "wa-py-cost-boto3-client-in-loop",
            "COST",
            "HIGH",
            "python",
            "boto3.client($$$ARGS)",
            (
                "Instantiating `boto3.client()` inside a loop re-parses botocore "
                "service JSON and resets HTTP connection pools."
            ),
            "Create the `boto3.client` once at module/class init and reuse it.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-cost-boto3-resource-in-loop",
            "COST",
            "HIGH",
            "python",
            "boto3.resource($$$ARGS)",
            (
                "Instantiating `boto3.resource()` inside a loop disables connection "
                "pooling and increases AWS API latency/cost."
            ),
            "Reuse a shared `boto3.resource` instance.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-cost-httpx-client-in-loop",
            "COST",
            "MEDIUM",
            "python",
            "httpx.Client($$$ARGS)",
            "Creating `httpx.Client()` inside a loop forces a new TCP+TLS handshake per iteration.",
            "Hoist `with httpx.Client() as client:` outside the loop.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-cost-requests-session-in-loop",
            "COST",
            "MEDIUM",
            "python",
            "requests.Session()",
            "Creating `requests.Session()` inside a loop defeats HTTP keep-alive connection pooling.",
            "Instantiate `requests.Session()` once outside the loop.",
            inside={"any": [{"kind": "for_statement"}, {"kind": "while_statement"}], "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-cost-dynamodb-scan",
            "COST",
            "HIGH",
            "python",
            "$TABLE.scan($$$ARGS)",
            "DynamoDB `.scan()` reads every item in the table, consuming massive RCU quota.",
            "Use `.query()` with a partition key or GSI.",
        ),
        # SUS (5)
        _rule_entry(
            "wa-py-sus-wildcard-import",
            "SUS",
            "MEDIUM",
            "python",
            {"kind": "wildcard_import"},
            "Wildcard `from module import *` pollutes namespace and breaks static dependency analysis.",
            "Import explicit symbols (`from module import sym1, sym2`).",
        ),
        _rule_entry(
            "wa-py-sus-global-stmt",
            "SUS",
            "MEDIUM",
            "python",
            {"kind": "global_statement"},
            "Mutating module-level state via `global` couples functions and breaks thread safety.",
            "Pass state explicitly or encapsulate in a class.",
        ),
        _rule_entry(
            "wa-py-sus-nested-for-3",
            "SUS",
            "MEDIUM",
            "python",
            {"kind": "for_statement"},
            "Triply nested `for` loop (O(N^3)) degrades readability and CPU sustainability.",
            "Pre-index inner collections into a `dict` or `set` for O(1) lookup.",
            inside={"kind": "for_statement", "inside": {"kind": "for_statement", "stopBy": "end"}, "stopBy": "end"},
        ),
        _rule_entry(
            "wa-py-sus-exec-compile",
            "SUS",
            "MEDIUM",
            "python",
            "compile($SRC, $$$ARGS)",
            "Runtime `compile()` obscures call graphs and static type checking.",
            "Use standard functions or dataclasses.",
        ),
        _rule_entry(
            "wa-py-sus-locals-mutation",
            "SUS",
            "LOW",
            "python",
            "locals()[$$$ARGS]",
            "Accessing `locals()` dynamically harms readability and JIT/static analysis.",
            "Use an explicit dictionary.",
        ),
    ]

    java_rules: List[Dict[str, Any]] = [
        # SEC (12)
        _rule_entry(
            "wa-java-sec-runtime-exec",
            "SEC",
            "CRITICAL",
            "java",
            "Runtime.getRuntime().exec($$$ARGS)",
            "`Runtime.exec()` is prone to command injection and shell argument splitting bugs.",
            "Use `new ProcessBuilder(List.of(cmd, arg))` with explicit argument array.",
        ),
        _rule_entry(
            "wa-java-sec-object-input-stream",
            "SEC",
            "CRITICAL",
            "java",
            "new ObjectInputStream($$$ARGS)",
            "Java native deserialization via `ObjectInputStream` is vulnerable to remote code execution gadget chains.",
            "Use Jackson/JSON or configure an `ObjectInputFilter` allowlist.",
        ),
        _rule_entry(
            "wa-java-sec-xml-decoder",
            "SEC",
            "CRITICAL",
            "java",
            "new XMLDecoder($$$ARGS)",
            "`XMLDecoder` executes arbitrary Java methods during XML deserialization.",
            "Use standard JAXB or Jackson XML with XXE disabled.",
        ),
        _rule_entry(
            "wa-java-sec-cipher-inst",
            "SEC",
            "HIGH",
            "java",
            'Cipher.getInstance("DES")',
            "DES uses a 56-bit key and can be brute-forced in hours.",
            "Use `AES/GCM/NoPadding`.",
        ),
        _rule_entry(
            "wa-java-sec-cipher-ecb",
            "SEC",
            "HIGH",
            "java",
            'Cipher.getInstance("AES/ECB/PKCS5Padding")',
            "AES in ECB mode leaks plaintext block patterns and lacks authentication.",
            "Use `AES/GCM/NoPadding` with a 12-byte IV.",
        ),
        _rule_entry(
            "wa-java-sec-md5",
            "SEC",
            "MEDIUM",
            "java",
            'MessageDigest.getInstance("MD5")',
            "MD5 is cryptographically broken.",
            'Use `MessageDigest.getInstance("SHA-256")`.',
        ),
        _rule_entry(
            "wa-java-sec-sha1",
            "SEC",
            "MEDIUM",
            "java",
            'MessageDigest.getInstance("SHA-1")',
            "SHA-1 is vulnerable to collision attacks.",
            'Use `MessageDigest.getInstance("SHA-256")`.',
        ),
        _rule_entry(
            "wa-java-sec-util-random",
            "SEC",
            "MEDIUM",
            "java",
            "new Random($$$ARGS)",
            "`java.util.Random` uses a predictable linear congruential PRNG unsuitable for tokens or keys.",
            "Use `java.security.SecureRandom`.",
        ),
        _rule_entry(
            "wa-java-sec-script-engine-eval",
            "SEC",
            "CRITICAL",
            "java",
            "$ENGINE.eval($$$ARGS)",
            "`ScriptEngine.eval()` executes dynamic script payloads and enables code injection.",
            "Avoid `ScriptEngine.eval()` on external input.",
        ),
        _rule_entry(
            "wa-java-sec-stmt-execute-query",
            "SEC",
            "HIGH",
            "java",
            "$STMT.executeQuery($SQL)",
            "Executing raw SQL on a `Statement` risks SQL injection if `$SQL` is concatenated.",
            "Use `PreparedStatement` with `?` parameter binding.",
        ),
        _rule_entry(
            "wa-java-sec-stmt-execute-update",
            "SEC",
            "HIGH",
            "java",
            "$STMT.executeUpdate($SQL)",
            "Executing raw SQL via `executeUpdate($SQL)` risks SQL injection.",
            "Use `PreparedStatement` with bound parameters.",
        ),
        _rule_entry(
            "wa-java-sec-file-create-temp",
            "SEC",
            "MEDIUM",
            "java",
            "File.createTempFile($$$ARGS)",
            "`File.createTempFile()` creates files with default world/group permissions on shared systems.",
            "Use `Files.createTempFile()` with restrictive `PosixFilePermissions`.",
        ),
        # REL (12)
        _rule_entry(
            "wa-java-rel-thread-stop",
            "REL",
            "CRITICAL",
            "java",
            "$T.stop()",
            "`Thread.stop()` unlocks all monitors abruptly, corrupting shared object invariants.",
            "Use cooperative cancellation via `Thread.interrupt()`.",
        ),
        _rule_entry(
            "wa-java-rel-thread-suspend",
            "REL",
            "HIGH",
            "java",
            "$T.suspend()",
            "`Thread.suspend()` holds monitors while suspended and frequently causes deadlocks.",
            "Use `ReentrantLock` / `Condition` or `CompletableFuture`.",
        ),
        _rule_entry(
            "wa-java-rel-system-exit",
            "REL",
            "HIGH",
            "java",
            "System.exit($$$ARGS)",
            "`System.exit()` kills the entire JVM container abruptly.",
            "Throw an exception and let the application lifecycle manage shutdown.",
        ),
        _rule_entry(
            "wa-java-rel-runtime-halt",
            "REL",
            "CRITICAL",
            "java",
            "Runtime.getRuntime().halt($$$ARGS)",
            "`Runtime.halt()` terminates the JVM without running shutdown hooks or finalizers.",
            "Use graceful shutdown hooks.",
        ),
        _rule_entry(
            "wa-java-rel-new-rest-template",
            "REL",
            "HIGH",
            "java",
            "new RestTemplate()",
            (
                "`new RestTemplate()` uses `SimpleClientHttpRequestFactory` "
                "with infinite read/connect timeouts by default."
            ),
            "Inject a timeout-configured `RestTemplateBuilder` or `WebClient`.",
        ),
        _rule_entry(
            "wa-java-rel-http-client-default",
            "REL",
            "MEDIUM",
            "java",
            "HttpClient.newHttpClient()",
            "`HttpClient.newHttpClient()` sets no default connect timeout.",
            "Use `HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build()`.",
        ),
        _rule_entry(
            "wa-java-rel-executors-fixed-pool",
            "REL",
            "MEDIUM",
            "java",
            "Executors.newFixedThreadPool($$$ARGS)",
            (
                "`Executors.newFixedThreadPool()` uses an unbounded `LinkedBlockingQueue` "
                "that can cause OOM under backpressure."
            ),
            "Use `new ThreadPoolExecutor(...)` with a bounded `ArrayBlockingQueue`.",
        ),
        _rule_entry(
            "wa-java-rel-executors-single-pool",
            "REL",
            "MEDIUM",
            "java",
            "Executors.newSingleThreadExecutor($$$ARGS)",
            "`Executors.newSingleThreadExecutor()` uses an unbounded work queue.",
            "Use a bounded `ThreadPoolExecutor`.",
        ),
        _rule_entry(
            "wa-java-rel-completable-future-get",
            "REL",
            "HIGH",
            "java",
            "$FUT.get()",
            "Unbounded `Future.get()` with no timeout can block carrier threads forever.",
            "Use `$FUT.get(10, TimeUnit.SECONDS)` or `orTimeout()`.",
        ),
        _rule_entry(
            "wa-java-rel-latch-await-no-timeout",
            "REL",
            "MEDIUM",
            "java",
            "$LATCH.await()",
            "Unbounded `CountDownLatch.await()` hangs forever if a worker thread dies.",
            "Use `$LATCH.await(30, TimeUnit.SECONDS)`.",
        ),
        _rule_entry(
            "wa-java-rel-simple-date-format",
            "REL",
            "MEDIUM",
            "java",
            "new SimpleDateFormat($$$ARGS)",
            "`SimpleDateFormat` is mutable and not thread-safe.",
            "Use immutable `java.time.format.DateTimeFormatter`.",
        ),
        _rule_entry(
            "wa-java-rel-bigdecimal-double-ctor",
            "REL",
            "MEDIUM",
            "java",
            "new BigDecimal($VAL)",
            "`new BigDecimal(double)` introduces IEEE-754 binary floating-point inaccuracy into monetary calculations.",
            "Use `BigDecimal.valueOf(...)` or `new BigDecimal(String)`.",
        ),
        # PERF (10)
        _rule_entry(
            "wa-java-perf-thread-sleep",
            "PERF",
            "HIGH",
            "java",
            "Thread.sleep($$$ARGS)",
            "Blocking `Thread.sleep()` pins OS/carrier threads and degrades throughput.",
            "Use `ScheduledExecutorService` or non-blocking delays.",
        ),
        _rule_entry(
            "wa-java-perf-pattern-compile-in-loop",
            "PERF",
            "HIGH",
            "java",
            "Pattern.compile($$$ARGS)",
            "Compiling regex via `Pattern.compile()` inside a loop wastes CPU and heap.",
            "Hoist `Pattern.compile()` to a `private static final Pattern` constant.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-object-mapper-in-loop",
            "PERF",
            "HIGH",
            "java",
            "new ObjectMapper($$$ARGS)",
            "Instantiating Jackson `ObjectMapper` inside a loop rebuilds serializer caches on every iteration.",
            "Inject or share a single thread-safe `ObjectMapper` bean.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-gson-in-loop",
            "PERF",
            "MEDIUM",
            "java",
            "new Gson($$$ARGS)",
            "Creating `new Gson()` inside a loop wastes reflection cache initialization.",
            "Share a single static/injected `Gson` instance.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-class-forname-in-loop",
            "PERF",
            "HIGH",
            "java",
            "Class.forName($$$ARGS)",
            "`Class.forName()` inside a loop contends on classloader locks.",
            "Cache resolved `Class<?>` references outside the loop.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-driver-manager-get-conn",
            "PERF",
            "HIGH",
            "java",
            "DriverManager.getConnection($$$ARGS)",
            "`DriverManager.getConnection()` opens a raw unpooled physical TCP database connection per call.",
            "Use a pooled `DataSource` (e.g., HikariCP).",
        ),
        _rule_entry(
            "wa-java-perf-files-read-all-bytes-in-loop",
            "PERF",
            "MEDIUM",
            "java",
            "Files.readAllBytes($$$ARGS)",
            "Loading entire files via `Files.readAllBytes()` inside a loop spikes heap allocation.",
            "Stream via `BufferedInputStream` or `Files.newInputStream()`.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-string-format-in-loop",
            "PERF",
            "LOW",
            "java",
            "String.format($$$ARGS)",
            "`String.format()` parses format specifiers via regex on every loop iteration.",
            "Use `StringBuilder` in hot loops.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-rest-exchange-in-loop",
            "PERF",
            "HIGH",
            "java",
            "$CLIENT.exchange($$$ARGS)",
            "Synchronous HTTP `.exchange()` inside a loop causes serial N+1 network latency.",
            "Batch API requests or use bounded `CompletableFuture.allOf()`.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-perf-jdbc-query-in-loop",
            "PERF",
            "HIGH",
            "java",
            "$JDBC.queryForObject($$$ARGS)",
            "Executing `queryForObject()` inside a loop creates an N+1 database query bottleneck.",
            "Use a batch `IN (...)` query outside the loop.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        # OPS (6)
        _rule_entry(
            "wa-java-ops-syserr",
            "OPS",
            "LOW",
            "java",
            "System.err.println($$$ARGS)",
            "`System.err.println` bypasses structured SLF4J logging and correlation IDs.",
            "Use `log.error(...)` via SLF4J.",
        ),
        _rule_entry(
            "wa-java-ops-print-stack-trace",
            "OPS",
            "MEDIUM",
            "java",
            "$EX.printStackTrace()",
            "`e.printStackTrace()` writes unstructured multi-line stack traces directly to stderr.",
            'Use `log.error("Context message", e)`.',
        ),
        _rule_entry(
            "wa-java-ops-thread-dump-stack",
            "OPS",
            "LOW",
            "java",
            "Thread.dumpStack()",
            "Leftover `Thread.dumpStack()` writes noisy stack dumps to stderr.",
            "Remove `Thread.dumpStack()` or log through SLF4J.",
        ),
        _rule_entry(
            "wa-java-ops-throw-runtime-exception",
            "OPS",
            "LOW",
            "java",
            "new RuntimeException($$$ARGS)",
            "Throwing raw `RuntimeException` loses domain error semantics.",
            "Throw a dedicated domain exception class.",
        ),
        _rule_entry(
            "wa-java-ops-java-util-logging",
            "OPS",
            "LOW",
            "java",
            "Logger.getLogger($$$ARGS)",
            "Direct `java.util.logging.Logger` fragments logging configuration in Spring/SLF4J services.",
            "Use `org.slf4j.LoggerFactory.getLogger(...)`.",
        ),
        _rule_entry(
            "wa-java-ops-system-getenv",
            "OPS",
            "LOW",
            "java",
            "System.getenv($KEY)",
            "Scattered `System.getenv()` calls bypass validated configuration properties.",
            "Use `@ConfigurationProperties` or `@Value` injection.",
        ),
        # COST (5)
        _rule_entry(
            "wa-java-cost-cached-thread-pool",
            "COST",
            "HIGH",
            "java",
            "Executors.newCachedThreadPool($$$ARGS)",
            "`newCachedThreadPool()` spawns unbounded OS threads under load spikes, inflating memory and CPU cost.",
            "Use a bounded `ThreadPoolExecutor` or virtual threads with semaphore limits.",
        ),
        _rule_entry(
            "wa-java-cost-s3-client-create-in-loop",
            "COST",
            "HIGH",
            "java",
            "S3Client.create()",
            "Creating `S3Client.create()` inside a loop leaks HTTP connection pools and repeats TLS handshakes.",
            "Inject a singleton `S3Client` bean.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-cost-dynamodb-client-in-loop",
            "COST",
            "HIGH",
            "java",
            "DynamoDbClient.create()",
            "Creating `DynamoDbClient.create()` inside a loop recreates Netty/Apache HTTP pools per iteration.",
            "Share a single `DynamoDbClient` bean.",
            inside={
                "any": [{"kind": "for_statement"}, {"kind": "enhanced_for_statement"}, {"kind": "while_statement"}],
                "stopBy": "end",
            },
        ),
        _rule_entry(
            "wa-java-cost-repo-findall",
            "COST",
            "MEDIUM",
            "java",
            "$REPO.findAll()",
            "Unpaginated `.findAll()` loads the entire database table into JVM heap.",
            "Use `findAll(Pageable)` or projection queries.",
        ),
        _rule_entry(
            "wa-java-cost-system-gc",
            "COST",
            "HIGH",
            "java",
            "System.gc()",
            "Explicit `System.gc()` triggers full stop-the-world garbage collection pauses, wasting CPU credits.",
            "Remove `System.gc()` and let G1GC/ZGC manage heap ergonomics.",
        ),
        # SUS (5)
        _rule_entry(
            "wa-java-sus-nested-for-3",
            "SUS",
            "MEDIUM",
            "java",
            {"kind": "for_statement"},
            "Triply nested `for` loop (O(N^3)) harms maintainability and CPU efficiency.",
            "Index inner collection in a `Map` before iterating.",
            inside={"kind": "for_statement", "inside": {"kind": "for_statement", "stopBy": "end"}, "stopBy": "end"},
        ),
        _rule_entry(
            "wa-java-sus-vector-usage",
            "SUS",
            "LOW",
            "java",
            "new Vector($$$ARGS)",
            "Legacy `java.util.Vector` synchronizes every element access needlessly.",
            "Use `new ArrayList<>()` or `Collections.synchronizedList()`.",
        ),
        _rule_entry(
            "wa-java-sus-hashtable-usage",
            "SUS",
            "LOW",
            "java",
            "new Hashtable($$$ARGS)",
            "Legacy `java.util.Hashtable` locks the entire table on every operation.",
            "Use `HashMap` or `ConcurrentHashMap`.",
        ),
        _rule_entry(
            "wa-java-sus-stringbuffer-usage",
            "SUS",
            "LOW",
            "java",
            "new StringBuffer($$$ARGS)",
            "`StringBuffer` pays unnecessary synchronization overhead for local string building.",
            "Use `new StringBuilder()`.",
        ),
        _rule_entry(
            "wa-java-sus-thread-run-direct",
            "SUS",
            "HIGH",
            "java",
            "$T.run()",
            "Calling `.run()` directly executes on the current thread instead of starting a new thread.",
            "Call `.start()` or submit to an `ExecutorService`.",
        ),
    ]

    go_rules: List[Dict[str, Any]] = [
        # SEC (12)
        _rule_entry(
            "wa-go-sec-md5-new",
            "SEC",
            "MEDIUM",
            "go",
            "md5.New()",
            "MD5 is cryptographically broken and unsuitable for security digests.",
            "Use `sha256.New()`.",
        ),
        _rule_entry(
            "wa-go-sec-md5-sum",
            "SEC",
            "MEDIUM",
            "go",
            "md5.Sum($$$ARGS)",
            "`md5.Sum()` is cryptographically broken.",
            "Use `sha256.Sum256()`.",
        ),
        _rule_entry(
            "wa-go-sec-sha1-new",
            "SEC",
            "MEDIUM",
            "go",
            "sha1.New()",
            "SHA-1 is vulnerable to collision attacks.",
            "Use `sha256.New()`.",
        ),
        _rule_entry(
            "wa-go-sec-sha1-sum",
            "SEC",
            "MEDIUM",
            "go",
            "sha1.Sum($$$ARGS)",
            "`sha1.Sum()` is vulnerable to collision attacks.",
            "Use `sha256.Sum256()`.",
        ),
        _rule_entry(
            "wa-go-sec-exec-sh-c",
            "SEC",
            "CRITICAL",
            "go",
            'exec.Command("sh", "-c", $$$ARGS)',
            "Spawning `sh -c` with dynamic strings enables shell command injection.",
            "Pass binary and discrete arguments directly to `exec.CommandContext(ctx, bin, arg1, arg2)`.",
        ),
        _rule_entry(
            "wa-go-sec-exec-bash-c",
            "SEC",
            "CRITICAL",
            "go",
            'exec.Command("bash", "-c", $$$ARGS)',
            "Spawning `bash -c` enables shell command injection.",
            "Use `exec.CommandContext(ctx, bin, args...)` without a shell.",
        ),
        _rule_entry(
            "wa-go-sec-http-listen-and-serve",
            "SEC",
            "HIGH",
            "go",
            "http.ListenAndServe($ADDR, $HANDLER)",
            (
                "`http.ListenAndServe` uses a default `http.Server` with zero `ReadHeaderTimeout` "
                "(Slowloris DoS risk) and cleartext HTTP."
            ),
            "Configure `&http.Server{Addr: addr, Handler: h, ReadHeaderTimeout: 5 * time.Second}`.",
        ),
        _rule_entry(
            "wa-go-sec-cgi-host",
            "SEC",
            "MEDIUM",
            "go",
            "http.ServeFile($W, $R, $PATH)",
            "`http.ServeFile` with unvalidated path input can lead to directory traversal.",
            "Sanitize paths via `filepath.Clean` and verify prefix with `strings.HasPrefix`.",
        ),
        _rule_entry(
            "wa-go-sec-chmod-777",
            "SEC",
            "HIGH",
            "go",
            "os.Chmod($P, 0777)",
            "Setting file permissions to `0777` makes files world-writable.",
            "Use `0600` for files or `0750` for directories.",
        ),
        _rule_entry(
            "wa-go-sec-mkdirall-777",
            "SEC",
            "HIGH",
            "go",
            "os.MkdirAll($P, 0777)",
            "Creating directories with `0777` allows any local user to modify contents.",
            "Use `0750` or `0700`.",
        ),
        _rule_entry(
            "wa-go-sec-unsafe-pointer",
            "SEC",
            "MEDIUM",
            "go",
            "unsafe.Pointer($X)",
            "`unsafe.Pointer` bypasses Go memory safety and garbage collector invariants.",
            "Avoid `unsafe.Pointer` unless required for low-level syscalls.",
        ),
        _rule_entry(
            "wa-go-sec-template-html-cast",
            "SEC",
            "HIGH",
            "go",
            "template.HTML($X)",
            "`template.HTML()` marks strings as safe without escaping, risking XSS if `$X` is user-controlled.",
            "Let `html/template` auto-escape dynamic values.",
        ),
        # REL (12)
        _rule_entry(
            "wa-go-rel-http-post",
            "REL",
            "HIGH",
            "go",
            "http.Post($$$ARGS)",
            "`http.Post` uses `http.DefaultClient` which has no request timeout and can hang goroutines forever.",
            "Use `&http.Client{Timeout: 10 * time.Second}` with `http.NewRequestWithContext`.",
        ),
        _rule_entry(
            "wa-go-rel-http-head",
            "REL",
            "HIGH",
            "go",
            "http.Head($$$ARGS)",
            "`http.Head` uses `http.DefaultClient` with no timeout.",
            "Use a custom `http.Client` with an explicit `Timeout`.",
        ),
        _rule_entry(
            "wa-go-rel-http-postform",
            "REL",
            "HIGH",
            "go",
            "http.PostForm($$$ARGS)",
            "`http.PostForm` uses `http.DefaultClient` with no timeout.",
            "Use a custom `http.Client` with an explicit `Timeout`.",
        ),
        _rule_entry(
            "wa-go-rel-panic-call",
            "REL",
            "HIGH",
            "go",
            "panic($MSG)",
            "Calling `panic()` in library or handler code crashes the entire Go process if unrecovered.",
            "Return an explicit `error` value instead of panicking.",
        ),
        _rule_entry(
            "wa-go-rel-os-exit",
            "REL",
            "MEDIUM",
            "go",
            "os.Exit($CODE)",
            "`os.Exit()` terminates immediately without running `defer` cleanup functions.",
            "Return an error to `main()` so deferred resource cleanups execute.",
        ),
        _rule_entry(
            "wa-go-rel-log-fatal",
            "REL",
            "MEDIUM",
            "go",
            "log.Fatal($$$ARGS)",
            "`log.Fatal()` calls `os.Exit(1)` immediately, skipping all `defer` statements.",
            "Return an `error` and only fatal at the top-level `main()` entrypoint.",
        ),
        _rule_entry(
            "wa-go-rel-log-fatalf",
            "REL",
            "MEDIUM",
            "go",
            "log.Fatalf($$$ARGS)",
            "`log.Fatalf()` calls `os.Exit(1)` and skips deferred cleanup.",
            "Return `fmt.Errorf(...)` instead.",
        ),
        _rule_entry(
            "wa-go-rel-time-after-in-loop",
            "REL",
            "HIGH",
            "go",
            "time.After($DUR)",
            "`time.After()` inside a `for` loop leaks underlying `time.Timer` channels until every timer fires.",
            "Use `time.NewTimer(d)` outside the loop and `timer.Reset(d)`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-rel-time-tick",
            "REL",
            "HIGH",
            "go",
            "time.Tick($DUR)",
            "`time.Tick()` creates a ticker Whose underlying channel can never be stopped or garbage-collected.",
            "Use `ticker := time.NewTicker(d)` and `defer ticker.Stop()`.",
        ),
        _rule_entry(
            "wa-go-rel-exec-command-no-ctx",
            "REL",
            "MEDIUM",
            "go",
            "exec.Command($BIN, $$$ARGS)",
            "`exec.Command` without context cannot be cancelled when the caller times out.",
            "Use `exec.CommandContext(ctx, bin, args...)`.",
        ),
        _rule_entry(
            "wa-go-rel-wg-add-in-goroutine",
            "REL",
            "HIGH",
            "go",
            "$WG.Add($N)",
            "Calling `wg.Add()` inside a `go func()` races with `wg.Wait()` in the parent goroutine.",
            "Call `wg.Add(1)` in the parent goroutine before `go func()`.",
            inside={"kind": "go_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-rel-time-sleep-in-loop",
            "REL",
            "MEDIUM",
            "go",
            "time.Sleep($DUR)",
            "`time.Sleep()` inside a loop ignores `ctx.Done()` cancellation signals.",
            "Use `select { case <-ctx.Done(): return ctx.Err(); case <-time.After(d): }` with a reusable timer.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        # PERF (10)
        _rule_entry(
            "wa-go-perf-regexp-compile-in-loop",
            "PERF",
            "HIGH",
            "go",
            "regexp.Compile($PAT)",
            "`regexp.Compile()` inside a `for` loop recompiles the finite automaton on every iteration.",
            "Hoist `regexp.MustCompile(...)` to a package-level `var`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-regexp-mustcompile-in-loop",
            "PERF",
            "HIGH",
            "go",
            "regexp.MustCompile($PAT)",
            "`regexp.MustCompile()` inside a `for` loop wastes CPU and allocations.",
            "Hoist `regexp.MustCompile(...)` to package initialization.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-http-do-in-loop",
            "PERF",
            "HIGH",
            "go",
            "$CLIENT.Do($REQ)",
            "Synchronous `client.Do(req)` inside a `for` loop serializes network round-trips (N+1 latency).",
            "Batch requests or use `errgroup.Group` with `SetLimit(N)`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-db-query-in-loop",
            "PERF",
            "HIGH",
            "go",
            "$DB.Query($$$ARGS)",
            "Executing `db.Query()` inside a `for` loop creates an N+1 SQL bottleneck.",
            "Batch IDs into a single `WHERE id = ANY($1)` query.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-db-queryctx-in-loop",
            "PERF",
            "HIGH",
            "go",
            "$DB.QueryContext($$$ARGS)",
            "Executing `db.QueryContext()` inside a `for` loop creates an N+1 SQL bottleneck.",
            "Batch queries outside the loop.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-db-exec-in-loop",
            "PERF",
            "MEDIUM",
            "go",
            "$DB.Exec($$$ARGS)",
            "Executing individual `db.Exec()` statements inside a loop incurs per-row round-trip latency.",
            "Use a prepared batch or multi-row `INSERT` inside a single transaction.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-reflect-deepequal-in-loop",
            "PERF",
            "MEDIUM",
            "go",
            "reflect.DeepEqual($A, $B)",
            "`reflect.DeepEqual()` inside a loop uses slow reflection and heap allocations.",
            "Use typed equality helpers or `slices.Equal` / `maps.Equal`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-json-marshal-in-loop",
            "PERF",
            "LOW",
            "go",
            "json.Marshal($V)",
            "Repeated `json.Marshal()` in a loop allocates a new `[]byte` buffer every iteration.",
            "Stream with `json.NewEncoder(w).Encode(v)` or reuse a `bytes.Buffer`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-fmt-sprintf-in-loop",
            "PERF",
            "LOW",
            "go",
            "fmt.Sprintf($$$ARGS)",
            "`fmt.Sprintf()` inside a hot loop incurs reflection and allocation overhead.",
            "Use `strconv` or `strings.Builder`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-perf-os-open-in-loop",
            "PERF",
            "MEDIUM",
            "go",
            "os.Open($P)",
            "Opening files via `os.Open()` inside a loop increases syscall overhead.",
            "Batch file operations or reuse handles.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        # OPS (6)
        _rule_entry(
            "wa-go-ops-context-todo",
            "OPS",
            "LOW",
            "go",
            "context.TODO()",
            "`context.TODO()` drops distributed tracing and caller cancellation deadlines.",
            "Thread the caller's `ctx context.Context` parameter down the call chain.",
        ),
        _rule_entry(
            "wa-go-ops-fmt-println",
            "OPS",
            "LOW",
            "go",
            "fmt.Println($$$ARGS)",
            "`fmt.Println` emits unstructured stdout lines without severity or trace attributes.",
            "Use `log/slog` structured logging (`slog.Info(...)`).",
        ),
        _rule_entry(
            "wa-go-ops-fmt-printf",
            "OPS",
            "LOW",
            "go",
            "fmt.Printf($$$ARGS)",
            "`fmt.Printf` emits unstructured stdout text instead of structured JSON/key-value logs.",
            "Use `slog.Info` / `slog.Error`.",
        ),
        _rule_entry(
            "wa-go-ops-log-println",
            "OPS",
            "LOW",
            "go",
            "log.Println($$$ARGS)",
            "Standard `log.Println` lacks structured key-value fields and log levels.",
            "Use `log/slog` (`slog.Info`, `slog.Warn`, `slog.Error`).",
        ),
        _rule_entry(
            "wa-go-ops-errors-new-fmt",
            "OPS",
            "LOW",
            "go",
            "errors.New(fmt.Sprintf($$$ARGS))",
            "`errors.New(fmt.Sprintf(...))` is redundant and loses `%w` error wrapping.",
            'Use `fmt.Errorf("...: %w", err)`.',
        ),
        _rule_entry(
            "wa-go-ops-recover-call",
            "OPS",
            "MEDIUM",
            "go",
            "recover()",
            "Ensure `recover()` logs `debug.Stack()` and converts panics into structured error telemetry.",
            "Log panic value + `string(debug.Stack())` via `slog.Error`.",
        ),
        # COST (5)
        _rule_entry(
            "wa-go-cost-io-readall",
            "COST",
            "MEDIUM",
            "go",
            "io.ReadAll($R)",
            "Unbounded `io.ReadAll(r)` buffers the entire stream into RAM, risking OOM on large responses.",
            "Wrap reader with `io.LimitReader(r, maxBytes)` before `io.ReadAll`.",
        ),
        _rule_entry(
            "wa-go-cost-ioutil-readall",
            "COST",
            "MEDIUM",
            "go",
            "ioutil.ReadAll($R)",
            "Deprecated and unbounded `ioutil.ReadAll(r)` buffers full stream into memory.",
            "Use `io.ReadAll(io.LimitReader(r, maxBytes))`.",
        ),
        _rule_entry(
            "wa-go-cost-http-client-in-loop",
            "COST",
            "HIGH",
            "go",
            "&http.Client{$$$FIELDS}",
            "Allocating `&http.Client{}` inside a loop creates a new connection pool per iteration.",
            "Instantiate `&http.Client{}` once and share across requests.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-cost-http-transport-in-loop",
            "COST",
            "HIGH",
            "go",
            "&http.Transport{$$$FIELDS}",
            "Allocating `&http.Transport{}` inside a loop disables TCP keep-alive reuse and leaks idle sockets.",
            "Reuse a shared `*http.Transport`.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-cost-go-in-loop",
            "COST",
            "HIGH",
            "go",
            {"kind": "go_statement"},
            "Spawning unbounded `go func()` inside a `for` loop causes goroutine and memory spikes on large inputs.",
            "Use `errgroup.Group` with `g.SetLimit(N)` or a worker pool.",
            inside={"kind": "for_statement", "stopBy": "end"},
        ),
        # SUS (5)
        _rule_entry(
            "wa-go-sus-nested-for-3",
            "SUS",
            "MEDIUM",
            "go",
            {"kind": "for_statement"},
            "Triply nested `for` loop (O(N^3)) degrades readability and CPU efficiency.",
            "Pre-index inner slice into a `map[K]V` before iterating.",
            inside={"kind": "for_statement", "inside": {"kind": "for_statement", "stopBy": "end"}, "stopBy": "end"},
        ),
        _rule_entry(
            "wa-go-sus-init-func",
            "SUS",
            "LOW",
            "go",
            "func init() { $$$BODY }",
            "`func init()` hides global initialization order and complicates unit testing.",
            "Prefer explicit constructor functions called from `main()`.",
        ),
        _rule_entry(
            "wa-go-sus-os-setenv",
            "SUS",
            "LOW",
            "go",
            "os.Setenv($K, $V)",
            "Mutating process-wide environment variables via `os.Setenv` causes data races across goroutines.",
            "Pass configuration via explicit structs (`t.Setenv` in tests).",
        ),
        _rule_entry(
            "wa-go-sus-context-withvalue-str",
            "SUS",
            "LOW",
            "go",
            'context.WithValue($CTX, "$KEY", $VAL)',
            "Using raw string literals as `context.WithValue` keys causes cross-package key collisions.",
            "Define an unexported custom key type (`type ctxKey struct{}`).",
        ),
        _rule_entry(
            "wa-go-sus-sleep-in-test",
            "SUS",
            "LOW",
            "go",
            "time.Sleep(5 * time.Second)",
            "Long hardcoded `time.Sleep` makes suites slow and flaky.",
            "Use channels, `sync.WaitGroup`, or `require.Eventually`.",
        ),
    ]

    return py_rules + java_rules + go_rules


def write_policy_packs(policies: List[Dict[str, Any]], out_dir: Path) -> List[Path]:
    """Write grouped Kodus-style Markdown Policy-as-Code packs organized by `<lang>/<pillar>.md`."""
    try:
        import yaml
    except ImportError:
        return []
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for pol in policies:
        key = (pol["language"], pol["pillar"])
        grouped.setdefault(key, []).append(pol)

    written: List[Path] = []
    for (lang, pillar), items in sorted(grouped.items()):
        lang_dir = out_dir / lang
        lang_dir.mkdir(parents=True, exist_ok=True)
        md_path = lang_dir / f"{lang}-{pillar.lower()}.md"
        front = {
            "pack_id": f"wa-pack-{lang}-{pillar.lower()}",
            "language": lang,
            "pillar": pillar,
            "rule_count": len(items),
            "rules": items,
        }
        body_lines = [
            f"# Well-Architected Policy Pack: {lang.upper()} — {pillar}",
            "",
            (
                f"Contains **{len(items)}** verified `ast-grep` structural policies "
                f"for `{lang}` mapped to the **{pillar}** pillar."
            ),
            "",
            "| Rule ID | Severity | Problem | Remediation |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for it in items:
            prob = " ".join(str(it["problem"]).split()).replace("|", "\\|")
            fix = " ".join(str(it["fix"]).split()).replace("|", "\\|")
            body_lines.append(f"| `{it['id']}` | `{it['severity']}` | {prob} | {fix} |")
        content = "---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n" + "\n".join(body_lines) + "\n"
        md_path.write_text(content, encoding="utf-8")
        written.append(md_path)
    return written


def fetch_upstream_repos(cache_dir: Path) -> Tuple[Optional[Path], Optional[Path]]:
    """Shallow sparse-checkout `semgrep/semgrep-rules` and `joshuadavidthomas/ast-grep-rules` into `cache_dir`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    sg_dir = cache_dir / "semgrep-rules"
    ag_dir = cache_dir / "ast-grep-rules"

    if not sg_dir.exists():
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/semgrep/semgrep-rules.git",
                str(sg_dir),
            ],
            check=False,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(sg_dir), "sparse-checkout", "set", "python/lang", "java/lang", "java/spring", "go/lang"],
            check=False,
            capture_output=True,
        )
    if not ag_dir.exists():
        subprocess.run(
            ["git", "clone", "--depth", "1", "https://github.com/joshuadavidthomas/ast-grep-rules.git", str(ag_dir)],
            check=False,
            capture_output=True,
        )
    return (sg_dir if sg_dir.is_dir() else None), (ag_dir if ag_dir.is_dir() else None)


def hydrate(
    out_dir: str = str(DEFAULT_POLICIES_DIR),
    semgrep_dir: Optional[str] = None,
    astgrep_dir: Optional[str] = None,
    fetch_upstream: bool = False,
    cache_dir: str = "/tmp/codemap-upstream-rules",
) -> Dict[str, Any]:
    """Hydrate Curated 150 + optional upstream Semgrep/ast-grep rules, canary-validate, and write Markdown packs."""
    all_policies = build_curated_150_policies()
    seen_ids = {p["id"] for p in all_policies}

    if fetch_upstream:
        sg_path, ag_path = fetch_upstream_repos(Path(cache_dir))
        if sg_path and not semgrep_dir:
            semgrep_dir = str(sg_path)
        if ag_path and not astgrep_dir:
            astgrep_dir = str(ag_path)

    imported_semgrep = 0
    if semgrep_dir:
        for p in import_semgrep_dir(semgrep_dir):
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_policies.append(p)
                imported_semgrep += 1

    imported_astgrep = 0
    if astgrep_dir:
        for p in import_astgrep_dir(astgrep_dir):
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_policies.append(p)
                imported_astgrep += 1

    valid_policies, quarantined_ids = validate_policies_with_ast_grep(all_policies)
    written_files = write_policy_packs(valid_policies, Path(out_dir))

    by_lang: Dict[str, int] = {}
    by_pillar: Dict[str, int] = {}
    for p in valid_policies:
        by_lang[p["language"]] = by_lang.get(p["language"], 0) + 1
        by_pillar[p["pillar"]] = by_pillar.get(p["pillar"], 0) + 1

    return {
        "total_valid_policies": len(valid_policies),
        "quarantined_count": len(quarantined_ids),
        "quarantined_ids": quarantined_ids,
        "imported_semgrep": imported_semgrep,
        "imported_astgrep": imported_astgrep,
        "by_language": by_lang,
        "by_pillar": by_pillar,
        "written_packs": [str(f) for f in written_files],
    }


def verify_well_hydrated(policies_dir: str = str(DEFAULT_POLICIES_DIR), min_per_lang: int = 50) -> Dict[str, Any]:
    """
    Certify whether a policies directory is 'Well-Hydrated' across 4 deterministic gates:
    1. Language Quota Gate (>= min_per_lang rules for each of python, java, go).
    2. 3x6 Language x Pillar Matrix Gate (all 18 (lang, pillar) cells populated).
    3. Zero-Quarantine Syntax Gate (0 rules rejected by `ast-grep scan`).
    4. Positive & Negative Behavioral Canary Gate (fires across all 3 languages & 6 pillars on bad code;
       0 false positives on clean code).
    """
    import well_architected_audit as waa

    policies = waa.load_markdown_policies(policies_dir)
    valid, quarantined = validate_policies_with_ast_grep(policies)

    langs = ("python", "java", "go")
    pillars = ("SEC", "REL", "PERF", "OPS", "COST", "SUS")
    by_lang: Dict[str, int] = {lang: 0 for lang in langs}
    by_pillar: Dict[str, int] = {p: 0 for p in pillars}
    matrix: Dict[str, int] = {}

    for pol in valid:
        lang = pol.get("language", "")
        p = pol.get("pillar", "")
        if lang in by_lang:
            by_lang[lang] += 1
        if p in by_pillar:
            by_pillar[p] += 1
        matrix[f"{lang}:{p}"] = matrix.get(f"{lang}:{p}", 0) + 1

    missing_quotas = [lang for lang in langs if by_lang.get(lang, 0) < min_per_lang]
    missing_cells = [f"{lang}:{p}" for lang in langs for p in pillars if matrix.get(f"{lang}:{p}", 0) < 1]

    # Behavioral canary gate: positive bad code + negative clean code
    with tempfile.TemporaryDirectory() as tmp:
        troot = Path(tmp)
        bad_dir = troot / "bad"
        clean_dir = troot / "clean"
        bad_dir.mkdir()
        clean_dir.mkdir()

        (bad_dir / "bad.py").write_text(
            "from os import *\n"
            "async def f(items, table):\n"
            "    eval('1+1')\n"
            "    requests.get('https://example.com')\n"
            "    time.sleep(1)\n"
            "    breakpoint()\n"
            "    table.scan()\n",
            encoding="utf-8",
        )
        (bad_dir / "Bad.java").write_text(
            "public class Bad {\n"
            "    void f( java.util.List<String> items ) throws Exception {\n"
            "        Runtime.getRuntime().exec(\"ls\");\n"
            "        new RestTemplate();\n"
            "        Thread.sleep(100);\n"
            "        System.err.println(\"err\");\n"
            "        System.gc();\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
        (bad_dir / "bad.go").write_text(
            "package main\n"
            "func f() {\n"
            "    _ = md5.New()\n"
            "    panic(\"boom\")\n"
            "    for i := 0; i < 3; i++ { _ = regexp.Compile(\"a+\") }\n"
            "    _ = context.TODO()\n"
            "    _, _ = io.ReadAll(r)\n"
            "}\n",
            encoding="utf-8",
        )

        (clean_dir / "clean.py").write_text(
            "def add(a: int, b: int) -> int:\n    return a + b\n",
            encoding="utf-8",
        )
        (clean_dir / "Clean.java").write_text(
            "public class Clean {\n    public int add(int a, int b) { return a + b; }\n}\n",
            encoding="utf-8",
        )
        (clean_dir / "clean.go").write_text(
            "package main\nfunc add(a int, b int) int { return a + b }\n",
            encoding="utf-8",
        )

        pos_findings = waa.evaluate_markdown_policies(str(bad_dir), policies_dir)
        neg_findings = waa.evaluate_markdown_policies(str(clean_dir), policies_dir)

    fired_pillars = sorted({f["pillar"] for f in pos_findings})
    fired_exts = sorted({Path(f["path"]).suffix for f in pos_findings})
    canary_passed = (
        len(fired_pillars) == 6
        and set(fired_exts) == {".py", ".java", ".go"}
        and len(neg_findings) == 0
    )

    certified = (
        not missing_quotas
        and not missing_cells
        and len(quarantined) == 0
        and canary_passed
    )
    return {
        "status": "CERTIFIED_WELL_HYDRATED" if certified else "FAILED",
        "certified": certified,
        "total_valid_policies": len(valid),
        "by_language": by_lang,
        "by_pillar": by_pillar,
        "missing_language_quotas": missing_quotas,
        "missing_matrix_cells": missing_cells,
        "quarantined_ids": quarantined,
        "canary": {
            "passed": canary_passed,
            "positive_findings_count": len(pos_findings),
            "fired_pillars": fired_pillars,
            "fired_file_extensions": fired_exts,
            "negative_false_positives": len(neg_findings),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hydrate Kodus-style Well-Architected Policy Packs from curated + Semgrep/ast-grep sources."
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_POLICIES_DIR), help="Target policies directory.")
    parser.add_argument("--from-semgrep-dir", help="Local directory containing Semgrep YAML rules to transpile.")
    parser.add_argument("--from-astgrep-dir", help="Local directory containing ast-grep YAML rules to import.")
    parser.add_argument(
        "--fetch-upstream", action="store_true", help="Shallow sparse-checkout upstream semgrep-rules & ast-grep-rules."
    )
    parser.add_argument(
        "--cache-dir", default="/tmp/codemap-upstream-rules", help="Cache directory for upstream rule repos."
    )
    parser.add_argument(
        "--verify", action="store_true", help="Run 4-gate Well-Hydrated Certification check on --out-dir."
    )
    args = parser.parse_args()

    if args.verify:
        cert = verify_well_hydrated(policies_dir=args.out_dir)
        print(json.dumps(cert, indent=2))
        return 0 if cert.get("certified") else 1

    summary = hydrate(
        out_dir=args.out_dir,
        semgrep_dir=args.from_semgrep_dir,
        astgrep_dir=args.from_astgrep_dir,
        fetch_upstream=args.fetch_upstream,
        cache_dir=args.cache_dir,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

