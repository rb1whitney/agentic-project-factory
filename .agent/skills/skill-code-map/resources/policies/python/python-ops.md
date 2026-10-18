---
pack_id: wa-pack-python-ops
language: python
pillar: OPS
rule_count: 11
rules:
- id: wa-py-ops-pdb-set-trace
  pillar: OPS
  severity: HIGH
  language: python
  problem: Leftover `pdb.set_trace()` halts production workers waiting for interactive
    stdin.
  fix: Remove interactive debugger statements before committing.
  rule:
    pattern: pdb.set_trace()
- id: wa-py-ops-breakpoint
  pillar: OPS
  severity: HIGH
  language: python
  problem: Leftover `breakpoint()` halts production execution.
  fix: Remove `breakpoint()` calls.
  rule:
    pattern: breakpoint()
- id: wa-py-ops-logging-basicconfig-in-func
  pillar: OPS
  severity: LOW
  language: python
  problem: Calling `logging.basicConfig()` inside a function mutates global root logger
    handlers.
  fix: Configure logging once at application entrypoint.
  rule:
    pattern: logging.basicConfig($$$ARGS)
    inside:
      kind: function_definition
      stopBy: end
- id: wa-py-ops-warnings-filterwarnings-ignore
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: Globally silencing all warnings hides deprecation and runtime safety alerts.
  fix: Scope `warnings.catch_warnings()` to specific warning classes.
  rule:
    pattern: warnings.filterwarnings("ignore")
- id: wa-py-ops-traceback-print-exc
  pillar: OPS
  severity: LOW
  language: python
  problem: '`traceback.print_exc()` writes unstructured stack traces to stderr bypassing
    structured log aggregators.'
  fix: Use `logger.exception(...)`.
  rule:
    pattern: traceback.print_exc()
- id: wa-py-ops-raise-base-exception
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: Raising generic `Exception` prevents callers from catching specific failure
    modes.
  fix: Raise a specific domain or built-in exception subclass.
  rule:
    pattern: raise Exception($$$ARGS)
- id: sg-python-hardcoded-tmp-path
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: Detected hardcoded temp directory. Consider using 'tempfile.TemporaryFile'
    instead.
  fix: https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryFile
  rule:
    pattern: open("=~/^\/tmp.*/", $$$ARGS)
- id: sg-python-pass-body-range
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: '`pass` is the body of for $X in $Y. Consider removing this or raise NotImplementedError()
    if this is a TODO'
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: "for $X in $Y:\n    pass"
- id: sg-python-python-debugger-found
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: Importing the python debugger; did you mean to leave this in?
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    any:
    - pattern: import pdb
    - pattern: pdb.set_trace()
- id: sg-python-arbitrary-sleep
  pillar: OPS
  severity: HIGH
  language: python
  problem: time.sleep() call; did you mean to leave this in?
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    all:
    - not:
        pattern: time.sleep($F($$$ARGS))
    - any:
      - pattern: 'time.sleep($X: int)'
      - pattern: 'time.sleep($X: float)'
- id: python-no-code-barricade
  pillar: OPS
  severity: MEDIUM
  language: python
  problem: Replace this decorative divider with a plain section comment.
  fix: Refactor to satisfy ast-grep structural policy.
  rule:
    kind: comment
    regex: "(?s).*(?:={5,}|-{5,}|\u2500{5,}|\\*{5,}|#{5,}).*"
  constraints: null
---

# Well-Architected Policy Pack: PYTHON — OPS

Contains **11** verified `ast-grep` structural policies for `python` mapped to the **OPS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-ops-pdb-set-trace` | `HIGH` | Leftover `pdb.set_trace()` halts production workers waiting for interactive stdin. | Remove interactive debugger statements before committing. |
| `wa-py-ops-breakpoint` | `HIGH` | Leftover `breakpoint()` halts production execution. | Remove `breakpoint()` calls. |
| `wa-py-ops-logging-basicconfig-in-func` | `LOW` | Calling `logging.basicConfig()` inside a function mutates global root logger handlers. | Configure logging once at application entrypoint. |
| `wa-py-ops-warnings-filterwarnings-ignore` | `MEDIUM` | Globally silencing all warnings hides deprecation and runtime safety alerts. | Scope `warnings.catch_warnings()` to specific warning classes. |
| `wa-py-ops-traceback-print-exc` | `LOW` | `traceback.print_exc()` writes unstructured stack traces to stderr bypassing structured log aggregators. | Use `logger.exception(...)`. |
| `wa-py-ops-raise-base-exception` | `MEDIUM` | Raising generic `Exception` prevents callers from catching specific failure modes. | Raise a specific domain or built-in exception subclass. |
| `sg-python-hardcoded-tmp-path` | `MEDIUM` | Detected hardcoded temp directory. Consider using 'tempfile.TemporaryFile' instead. | https://docs.python.org/3/library/tempfile.html#tempfile.TemporaryFile |
| `sg-python-pass-body-range` | `MEDIUM` | `pass` is the body of for $X in $Y. Consider removing this or raise NotImplementedError() if this is a TODO | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python-debugger-found` | `MEDIUM` | Importing the python debugger; did you mean to leave this in? | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-arbitrary-sleep` | `HIGH` | time.sleep() call; did you mean to leave this in? | Refactor pattern to comply with Well-Architected policy. |
| `python-no-code-barricade` | `MEDIUM` | Replace this decorative divider with a plain section comment. | Refactor to satisfy ast-grep structural policy. |
