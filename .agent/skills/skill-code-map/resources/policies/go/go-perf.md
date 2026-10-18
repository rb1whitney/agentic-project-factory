---
pack_id: wa-pack-go-perf
language: go
pillar: PERF
rule_count: 10
rules:
- id: wa-go-perf-regexp-compile-in-loop
  pillar: PERF
  severity: HIGH
  language: go
  problem: '`regexp.Compile()` inside a `for` loop recompiles the finite automaton
    on every iteration.'
  fix: Hoist `regexp.MustCompile(...)` to a package-level `var`.
  rule:
    pattern: regexp.Compile($PAT)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-regexp-mustcompile-in-loop
  pillar: PERF
  severity: HIGH
  language: go
  problem: '`regexp.MustCompile()` inside a `for` loop wastes CPU and allocations.'
  fix: Hoist `regexp.MustCompile(...)` to package initialization.
  rule:
    pattern: regexp.MustCompile($PAT)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-http-do-in-loop
  pillar: PERF
  severity: HIGH
  language: go
  problem: Synchronous `client.Do(req)` inside a `for` loop serializes network round-trips
    (N+1 latency).
  fix: Batch requests or use `errgroup.Group` with `SetLimit(N)`.
  rule:
    pattern: $CLIENT.Do($REQ)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-db-query-in-loop
  pillar: PERF
  severity: HIGH
  language: go
  problem: Executing `db.Query()` inside a `for` loop creates an N+1 SQL bottleneck.
  fix: Batch IDs into a single `WHERE id = ANY($1)` query.
  rule:
    pattern: $DB.Query($$$ARGS)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-db-queryctx-in-loop
  pillar: PERF
  severity: HIGH
  language: go
  problem: Executing `db.QueryContext()` inside a `for` loop creates an N+1 SQL bottleneck.
  fix: Batch queries outside the loop.
  rule:
    pattern: $DB.QueryContext($$$ARGS)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-db-exec-in-loop
  pillar: PERF
  severity: MEDIUM
  language: go
  problem: Executing individual `db.Exec()` statements inside a loop incurs per-row
    round-trip latency.
  fix: Use a prepared batch or multi-row `INSERT` inside a single transaction.
  rule:
    pattern: $DB.Exec($$$ARGS)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-reflect-deepequal-in-loop
  pillar: PERF
  severity: MEDIUM
  language: go
  problem: '`reflect.DeepEqual()` inside a loop uses slow reflection and heap allocations.'
  fix: Use typed equality helpers or `slices.Equal` / `maps.Equal`.
  rule:
    pattern: reflect.DeepEqual($A, $B)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-json-marshal-in-loop
  pillar: PERF
  severity: LOW
  language: go
  problem: Repeated `json.Marshal()` in a loop allocates a new `[]byte` buffer every
    iteration.
  fix: Stream with `json.NewEncoder(w).Encode(v)` or reuse a `bytes.Buffer`.
  rule:
    pattern: json.Marshal($V)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-fmt-sprintf-in-loop
  pillar: PERF
  severity: LOW
  language: go
  problem: '`fmt.Sprintf()` inside a hot loop incurs reflection and allocation overhead.'
  fix: Use `strconv` or `strings.Builder`.
  rule:
    pattern: fmt.Sprintf($$$ARGS)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-perf-os-open-in-loop
  pillar: PERF
  severity: MEDIUM
  language: go
  problem: Opening files via `os.Open()` inside a loop increases syscall overhead.
  fix: Batch file operations or reuse handles.
  rule:
    pattern: os.Open($P)
    inside:
      kind: for_statement
      stopBy: end
---

# Well-Architected Policy Pack: GO — PERF

Contains **10** verified `ast-grep` structural policies for `go` mapped to the **PERF** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-perf-regexp-compile-in-loop` | `HIGH` | `regexp.Compile()` inside a `for` loop recompiles the finite automaton on every iteration. | Hoist `regexp.MustCompile(...)` to a package-level `var`. |
| `wa-go-perf-regexp-mustcompile-in-loop` | `HIGH` | `regexp.MustCompile()` inside a `for` loop wastes CPU and allocations. | Hoist `regexp.MustCompile(...)` to package initialization. |
| `wa-go-perf-http-do-in-loop` | `HIGH` | Synchronous `client.Do(req)` inside a `for` loop serializes network round-trips (N+1 latency). | Batch requests or use `errgroup.Group` with `SetLimit(N)`. |
| `wa-go-perf-db-query-in-loop` | `HIGH` | Executing `db.Query()` inside a `for` loop creates an N+1 SQL bottleneck. | Batch IDs into a single `WHERE id = ANY($1)` query. |
| `wa-go-perf-db-queryctx-in-loop` | `HIGH` | Executing `db.QueryContext()` inside a `for` loop creates an N+1 SQL bottleneck. | Batch queries outside the loop. |
| `wa-go-perf-db-exec-in-loop` | `MEDIUM` | Executing individual `db.Exec()` statements inside a loop incurs per-row round-trip latency. | Use a prepared batch or multi-row `INSERT` inside a single transaction. |
| `wa-go-perf-reflect-deepequal-in-loop` | `MEDIUM` | `reflect.DeepEqual()` inside a loop uses slow reflection and heap allocations. | Use typed equality helpers or `slices.Equal` / `maps.Equal`. |
| `wa-go-perf-json-marshal-in-loop` | `LOW` | Repeated `json.Marshal()` in a loop allocates a new `[]byte` buffer every iteration. | Stream with `json.NewEncoder(w).Encode(v)` or reuse a `bytes.Buffer`. |
| `wa-go-perf-fmt-sprintf-in-loop` | `LOW` | `fmt.Sprintf()` inside a hot loop incurs reflection and allocation overhead. | Use `strconv` or `strings.Builder`. |
| `wa-go-perf-os-open-in-loop` | `MEDIUM` | Opening files via `os.Open()` inside a loop increases syscall overhead. | Batch file operations or reuse handles. |
