---
pack_id: wa-pack-go-sus
language: go
pillar: SUS
rule_count: 6
rules:
- id: wa-go-sus-nested-for-3
  pillar: SUS
  severity: MEDIUM
  language: go
  problem: Triply nested `for` loop (O(N^3)) degrades readability and CPU efficiency.
  fix: Pre-index inner slice into a `map[K]V` before iterating.
  rule:
    kind: for_statement
    inside:
      kind: for_statement
      inside:
        kind: for_statement
        stopBy: end
      stopBy: end
- id: wa-go-sus-init-func
  pillar: SUS
  severity: LOW
  language: go
  problem: '`func init()` hides global initialization order and complicates unit testing.'
  fix: Prefer explicit constructor functions called from `main()`.
  rule:
    pattern: func init() { $$$BODY }
- id: wa-go-sus-os-setenv
  pillar: SUS
  severity: LOW
  language: go
  problem: Mutating process-wide environment variables via `os.Setenv` causes data
    races across goroutines.
  fix: Pass configuration via explicit structs (`t.Setenv` in tests).
  rule:
    pattern: os.Setenv($K, $V)
- id: wa-go-sus-context-withvalue-str
  pillar: SUS
  severity: LOW
  language: go
  problem: Using raw string literals as `context.WithValue` keys causes cross-package
    key collisions.
  fix: Define an unexported custom key type (`type ctxKey struct{}`).
  rule:
    pattern: context.WithValue($CTX, "$KEY", $VAL)
- id: wa-go-sus-sleep-in-test
  pillar: SUS
  severity: LOW
  language: go
  problem: Long hardcoded `time.Sleep` makes suites slow and flaky.
  fix: Use channels, `sync.WaitGroup`, or `require.Eventually`.
  rule:
    pattern: time.Sleep(5 * time.Second)
- id: sg-go-useless-if-body
  pillar: SUS
  severity: MEDIUM
  language: go
  problem: Detected identical statements in the if body and the else body of an if-statement.
    This will lead to the same code being executed no matter what the if-expression
    evaluates to. Instead, remove the if statement.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: "if ($X) {\n    $S\n} else {\n    $S\n}"
---

# Well-Architected Policy Pack: GO — SUS

Contains **6** verified `ast-grep` structural policies for `go` mapped to the **SUS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-sus-nested-for-3` | `MEDIUM` | Triply nested `for` loop (O(N^3)) degrades readability and CPU efficiency. | Pre-index inner slice into a `map[K]V` before iterating. |
| `wa-go-sus-init-func` | `LOW` | `func init()` hides global initialization order and complicates unit testing. | Prefer explicit constructor functions called from `main()`. |
| `wa-go-sus-os-setenv` | `LOW` | Mutating process-wide environment variables via `os.Setenv` causes data races across goroutines. | Pass configuration via explicit structs (`t.Setenv` in tests). |
| `wa-go-sus-context-withvalue-str` | `LOW` | Using raw string literals as `context.WithValue` keys causes cross-package key collisions. | Define an unexported custom key type (`type ctxKey struct{}`). |
| `wa-go-sus-sleep-in-test` | `LOW` | Long hardcoded `time.Sleep` makes suites slow and flaky. | Use channels, `sync.WaitGroup`, or `require.Eventually`. |
| `sg-go-useless-if-body` | `MEDIUM` | Detected identical statements in the if body and the else body of an if-statement. This will lead to the same code being executed no matter what the if-expression evaluates to. Instead, remove the if statement. | Refactor pattern to comply with Well-Architected policy. |
