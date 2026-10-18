---
pack_id: wa-pack-python-perf
language: python
pillar: PERF
rule_count: 10
rules:
- id: wa-py-perf-sleep-in-async
  pillar: PERF
  severity: HIGH
  language: python
  problem: Blocking `time.sleep()` inside `async def` freezes the entire asyncio event
    loop.
  fix: Replace with `await asyncio.sleep(...)`.
  rule:
    pattern: time.sleep($$$ARGS)
    inside:
      kind: function_definition
      regex: ^async\s+def\b
      stopBy: end
- id: wa-py-perf-re-compile-in-loop
  pillar: PERF
  severity: MEDIUM
  language: python
  problem: Compiling regex via `re.compile()` inside a loop wastes CPU on every iteration.
  fix: Hoist `re.compile()` to a module-level constant.
  rule:
    pattern: re.compile($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-json-loads-in-loop
  pillar: PERF
  severity: MEDIUM
  language: python
  problem: Repeated `json.loads()` inside a loop amplifies parsing CPU overhead.
  fix: Use JSONL streaming or batch parse outside hot loops.
  rule:
    pattern: json.loads($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-deepcopy-in-loop
  pillar: PERF
  severity: HIGH
  language: python
  problem: '`copy.deepcopy()` inside a loop causes quadratic object allocation and
    GC pressure.'
  fix: Use shallow copy (`copy.copy`), structural sharing, or immutable tuples/dataclasses.
  rule:
    pattern: copy.deepcopy($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-df-iterrows
  pillar: PERF
  severity: HIGH
  language: python
  problem: Pandas `.iterrows()` boxes every row into a `Series`, running ~100x slower
    than vectorized operations.
  fix: Use vectorized Pandas expressions or `.itertuples()`.
  rule:
    pattern: $DF.iterrows()
- id: wa-py-perf-requests-in-async
  pillar: PERF
  severity: HIGH
  language: python
  problem: Synchronous `requests` call inside `async def` blocks the event loop thread.
  fix: Use `httpx.AsyncClient` or `aiohttp`.
  rule:
    pattern: requests.$METHOD($$$ARGS)
    inside:
      kind: function_definition
      regex: ^async\s+def\b
      stopBy: end
- id: wa-py-perf-glob-in-loop
  pillar: PERF
  severity: MEDIUM
  language: python
  problem: Filesystem `glob.glob()` inside a loop triggers repeated directory walks.
  fix: Hoist directory discovery outside the loop or use `os.scandir()`.
  rule:
    pattern: glob.glob($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-path-rglob-in-loop
  pillar: PERF
  severity: HIGH
  language: python
  problem: Recursive `.rglob()` inside a loop causes O(N * files) filesystem stat
    storms.
  fix: Run `.rglob()` once before the loop and index paths in memory.
  rule:
    pattern: $P.rglob($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-subprocess-in-loop
  pillar: PERF
  severity: HIGH
  language: python
  problem: Spawning `subprocess.run()` inside a loop incurs OS fork/exec overhead
    per item.
  fix: Batch arguments into a single CLI invocation.
  rule:
    pattern: subprocess.run($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-perf-sqlite-connect-in-loop
  pillar: PERF
  severity: HIGH
  language: python
  problem: Opening a new `sqlite3.connect()` inside a loop wastes connection setup
    and prevents transaction batching.
  fix: Create connection once outside the loop and commit in batches.
  rule:
    pattern: sqlite3.connect($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
---

# Well-Architected Policy Pack: PYTHON — PERF

Contains **10** verified `ast-grep` structural policies for `python` mapped to the **PERF** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-perf-sleep-in-async` | `HIGH` | Blocking `time.sleep()` inside `async def` freezes the entire asyncio event loop. | Replace with `await asyncio.sleep(...)`. |
| `wa-py-perf-re-compile-in-loop` | `MEDIUM` | Compiling regex via `re.compile()` inside a loop wastes CPU on every iteration. | Hoist `re.compile()` to a module-level constant. |
| `wa-py-perf-json-loads-in-loop` | `MEDIUM` | Repeated `json.loads()` inside a loop amplifies parsing CPU overhead. | Use JSONL streaming or batch parse outside hot loops. |
| `wa-py-perf-deepcopy-in-loop` | `HIGH` | `copy.deepcopy()` inside a loop causes quadratic object allocation and GC pressure. | Use shallow copy (`copy.copy`), structural sharing, or immutable tuples/dataclasses. |
| `wa-py-perf-df-iterrows` | `HIGH` | Pandas `.iterrows()` boxes every row into a `Series`, running ~100x slower than vectorized operations. | Use vectorized Pandas expressions or `.itertuples()`. |
| `wa-py-perf-requests-in-async` | `HIGH` | Synchronous `requests` call inside `async def` blocks the event loop thread. | Use `httpx.AsyncClient` or `aiohttp`. |
| `wa-py-perf-glob-in-loop` | `MEDIUM` | Filesystem `glob.glob()` inside a loop triggers repeated directory walks. | Hoist directory discovery outside the loop or use `os.scandir()`. |
| `wa-py-perf-path-rglob-in-loop` | `HIGH` | Recursive `.rglob()` inside a loop causes O(N * files) filesystem stat storms. | Run `.rglob()` once before the loop and index paths in memory. |
| `wa-py-perf-subprocess-in-loop` | `HIGH` | Spawning `subprocess.run()` inside a loop incurs OS fork/exec overhead per item. | Batch arguments into a single CLI invocation. |
| `wa-py-perf-sqlite-connect-in-loop` | `HIGH` | Opening a new `sqlite3.connect()` inside a loop wastes connection setup and prevents transaction batching. | Create connection once outside the loop and commit in batches. |
