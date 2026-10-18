---
pack_id: wa-pack-go-rel
language: go
pillar: REL
rule_count: 13
rules:
- id: wa-go-rel-http-post
  pillar: REL
  severity: HIGH
  language: go
  problem: '`http.Post` uses `http.DefaultClient` which has no request timeout and
    can hang goroutines forever.'
  fix: 'Use `&http.Client{Timeout: 10 * time.Second}` with `http.NewRequestWithContext`.'
  rule:
    pattern: http.Post($$$ARGS)
- id: wa-go-rel-http-head
  pillar: REL
  severity: HIGH
  language: go
  problem: '`http.Head` uses `http.DefaultClient` with no timeout.'
  fix: Use a custom `http.Client` with an explicit `Timeout`.
  rule:
    pattern: http.Head($$$ARGS)
- id: wa-go-rel-http-postform
  pillar: REL
  severity: HIGH
  language: go
  problem: '`http.PostForm` uses `http.DefaultClient` with no timeout.'
  fix: Use a custom `http.Client` with an explicit `Timeout`.
  rule:
    pattern: http.PostForm($$$ARGS)
- id: wa-go-rel-panic-call
  pillar: REL
  severity: HIGH
  language: go
  problem: Calling `panic()` in library or handler code crashes the entire Go process
    if unrecovered.
  fix: Return an explicit `error` value instead of panicking.
  rule:
    pattern: panic($MSG)
- id: wa-go-rel-os-exit
  pillar: REL
  severity: MEDIUM
  language: go
  problem: '`os.Exit()` terminates immediately without running `defer` cleanup functions.'
  fix: Return an error to `main()` so deferred resource cleanups execute.
  rule:
    pattern: os.Exit($CODE)
- id: wa-go-rel-log-fatal
  pillar: REL
  severity: MEDIUM
  language: go
  problem: '`log.Fatal()` calls `os.Exit(1)` immediately, skipping all `defer` statements.'
  fix: Return an `error` and only fatal at the top-level `main()` entrypoint.
  rule:
    pattern: log.Fatal($$$ARGS)
- id: wa-go-rel-log-fatalf
  pillar: REL
  severity: MEDIUM
  language: go
  problem: '`log.Fatalf()` calls `os.Exit(1)` and skips deferred cleanup.'
  fix: Return `fmt.Errorf(...)` instead.
  rule:
    pattern: log.Fatalf($$$ARGS)
- id: wa-go-rel-time-after-in-loop
  pillar: REL
  severity: HIGH
  language: go
  problem: '`time.After()` inside a `for` loop leaks underlying `time.Timer` channels
    until every timer fires.'
  fix: Use `time.NewTimer(d)` outside the loop and `timer.Reset(d)`.
  rule:
    pattern: time.After($DUR)
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-rel-time-tick
  pillar: REL
  severity: HIGH
  language: go
  problem: '`time.Tick()` creates a ticker Whose underlying channel can never be stopped
    or garbage-collected.'
  fix: Use `ticker := time.NewTicker(d)` and `defer ticker.Stop()`.
  rule:
    pattern: time.Tick($DUR)
- id: wa-go-rel-exec-command-no-ctx
  pillar: REL
  severity: MEDIUM
  language: go
  problem: '`exec.Command` without context cannot be cancelled when the caller times
    out.'
  fix: Use `exec.CommandContext(ctx, bin, args...)`.
  rule:
    pattern: exec.Command($BIN, $$$ARGS)
- id: wa-go-rel-wg-add-in-goroutine
  pillar: REL
  severity: HIGH
  language: go
  problem: Calling `wg.Add()` inside a `go func()` races with `wg.Wait()` in the parent
    goroutine.
  fix: Call `wg.Add(1)` in the parent goroutine before `go func()`.
  rule:
    pattern: $WG.Add($N)
    inside:
      kind: go_statement
      stopBy: end
- id: wa-go-rel-time-sleep-in-loop
  pillar: REL
  severity: MEDIUM
  language: go
  problem: '`time.Sleep()` inside a loop ignores `ctx.Done()` cancellation signals.'
  fix: 'Use `select { case <-ctx.Done(): return ctx.Err(); case <-time.After(d): }`
    with a reusable timer.'
  rule:
    pattern: time.Sleep($DUR)
    inside:
      kind: for_statement
      stopBy: end
- id: sg-go-eqeq-is-bad
  pillar: REL
  severity: LOW
  language: go
  problem: Detected useless comparison operation `$X == $X` or `$X != $X`. This will
    always return 'True' or 'False' and therefore is not necessary. Instead, remove
    this comparison operation or use another comparison expression that is not deterministic.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    all:
    - not:
        inside:
          pattern: assert($$$ARGS)
          stopBy: end
    - any:
      - pattern: $X == $X
      - pattern: $X != $X
    - not:
        pattern: 1 == 1
---

# Well-Architected Policy Pack: GO — REL

Contains **13** verified `ast-grep` structural policies for `go` mapped to the **REL** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-rel-http-post` | `HIGH` | `http.Post` uses `http.DefaultClient` which has no request timeout and can hang goroutines forever. | Use `&http.Client{Timeout: 10 * time.Second}` with `http.NewRequestWithContext`. |
| `wa-go-rel-http-head` | `HIGH` | `http.Head` uses `http.DefaultClient` with no timeout. | Use a custom `http.Client` with an explicit `Timeout`. |
| `wa-go-rel-http-postform` | `HIGH` | `http.PostForm` uses `http.DefaultClient` with no timeout. | Use a custom `http.Client` with an explicit `Timeout`. |
| `wa-go-rel-panic-call` | `HIGH` | Calling `panic()` in library or handler code crashes the entire Go process if unrecovered. | Return an explicit `error` value instead of panicking. |
| `wa-go-rel-os-exit` | `MEDIUM` | `os.Exit()` terminates immediately without running `defer` cleanup functions. | Return an error to `main()` so deferred resource cleanups execute. |
| `wa-go-rel-log-fatal` | `MEDIUM` | `log.Fatal()` calls `os.Exit(1)` immediately, skipping all `defer` statements. | Return an `error` and only fatal at the top-level `main()` entrypoint. |
| `wa-go-rel-log-fatalf` | `MEDIUM` | `log.Fatalf()` calls `os.Exit(1)` and skips deferred cleanup. | Return `fmt.Errorf(...)` instead. |
| `wa-go-rel-time-after-in-loop` | `HIGH` | `time.After()` inside a `for` loop leaks underlying `time.Timer` channels until every timer fires. | Use `time.NewTimer(d)` outside the loop and `timer.Reset(d)`. |
| `wa-go-rel-time-tick` | `HIGH` | `time.Tick()` creates a ticker Whose underlying channel can never be stopped or garbage-collected. | Use `ticker := time.NewTicker(d)` and `defer ticker.Stop()`. |
| `wa-go-rel-exec-command-no-ctx` | `MEDIUM` | `exec.Command` without context cannot be cancelled when the caller times out. | Use `exec.CommandContext(ctx, bin, args...)`. |
| `wa-go-rel-wg-add-in-goroutine` | `HIGH` | Calling `wg.Add()` inside a `go func()` races with `wg.Wait()` in the parent goroutine. | Call `wg.Add(1)` in the parent goroutine before `go func()`. |
| `wa-go-rel-time-sleep-in-loop` | `MEDIUM` | `time.Sleep()` inside a loop ignores `ctx.Done()` cancellation signals. | Use `select { case <-ctx.Done(): return ctx.Err(); case <-time.After(d): }` with a reusable timer. |
| `sg-go-eqeq-is-bad` | `LOW` | Detected useless comparison operation `$X == $X` or `$X != $X`. This will always return 'True' or 'False' and therefore is not necessary. Instead, remove this comparison operation or use another comparison expression that is not deterministic. | Refactor pattern to comply with Well-Architected policy. |
