---
pack_id: wa-pack-go-ops
language: go
pillar: OPS
rule_count: 7
rules:
- id: wa-go-ops-context-todo
  pillar: OPS
  severity: LOW
  language: go
  problem: '`context.TODO()` drops distributed tracing and caller cancellation deadlines.'
  fix: Thread the caller's `ctx context.Context` parameter down the call chain.
  rule:
    pattern: context.TODO()
- id: wa-go-ops-fmt-println
  pillar: OPS
  severity: LOW
  language: go
  problem: '`fmt.Println` emits unstructured stdout lines without severity or trace
    attributes.'
  fix: Use `log/slog` structured logging (`slog.Info(...)`).
  rule:
    pattern: fmt.Println($$$ARGS)
- id: wa-go-ops-fmt-printf
  pillar: OPS
  severity: LOW
  language: go
  problem: '`fmt.Printf` emits unstructured stdout text instead of structured JSON/key-value
    logs.'
  fix: Use `slog.Info` / `slog.Error`.
  rule:
    pattern: fmt.Printf($$$ARGS)
- id: wa-go-ops-log-println
  pillar: OPS
  severity: LOW
  language: go
  problem: Standard `log.Println` lacks structured key-value fields and log levels.
  fix: Use `log/slog` (`slog.Info`, `slog.Warn`, `slog.Error`).
  rule:
    pattern: log.Println($$$ARGS)
- id: wa-go-ops-errors-new-fmt
  pillar: OPS
  severity: LOW
  language: go
  problem: '`errors.New(fmt.Sprintf(...))` is redundant and loses `%w` error wrapping.'
  fix: 'Use `fmt.Errorf("...: %w", err)`.'
  rule:
    pattern: errors.New(fmt.Sprintf($$$ARGS))
- id: wa-go-ops-recover-call
  pillar: OPS
  severity: MEDIUM
  language: go
  problem: Ensure `recover()` logs `debug.Stack()` and converts panics into structured
    error telemetry.
  fix: Log panic value + `string(debug.Stack())` via `slog.Error`.
  rule:
    pattern: recover()
- id: go-no-code-barricade
  pillar: OPS
  severity: MEDIUM
  language: go
  problem: Replace this decorative divider with a plain section comment.
  fix: Refactor to satisfy ast-grep structural policy.
  rule:
    kind: comment
    regex: "(?s).*(?:={5,}|-{5,}|\u2500{5,}|\\*{5,}|/{8,}).*"
  constraints: null
---

# Well-Architected Policy Pack: GO — OPS

Contains **7** verified `ast-grep` structural policies for `go` mapped to the **OPS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-ops-context-todo` | `LOW` | `context.TODO()` drops distributed tracing and caller cancellation deadlines. | Thread the caller's `ctx context.Context` parameter down the call chain. |
| `wa-go-ops-fmt-println` | `LOW` | `fmt.Println` emits unstructured stdout lines without severity or trace attributes. | Use `log/slog` structured logging (`slog.Info(...)`). |
| `wa-go-ops-fmt-printf` | `LOW` | `fmt.Printf` emits unstructured stdout text instead of structured JSON/key-value logs. | Use `slog.Info` / `slog.Error`. |
| `wa-go-ops-log-println` | `LOW` | Standard `log.Println` lacks structured key-value fields and log levels. | Use `log/slog` (`slog.Info`, `slog.Warn`, `slog.Error`). |
| `wa-go-ops-errors-new-fmt` | `LOW` | `errors.New(fmt.Sprintf(...))` is redundant and loses `%w` error wrapping. | Use `fmt.Errorf("...: %w", err)`. |
| `wa-go-ops-recover-call` | `MEDIUM` | Ensure `recover()` logs `debug.Stack()` and converts panics into structured error telemetry. | Log panic value + `string(debug.Stack())` via `slog.Error`. |
| `go-no-code-barricade` | `MEDIUM` | Replace this decorative divider with a plain section comment. | Refactor to satisfy ast-grep structural policy. |
