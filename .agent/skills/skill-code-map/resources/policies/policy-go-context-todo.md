---
id: policy-go-context-todo
pillar: OPS
severity: LOW
language: go
fix: "Propagate caller context.Context (ctx) or use context.WithTimeout instead of context.TODO() in production paths."
rule:
  pattern:
    context: "package p; func f() { context.TODO() }"
    selector: call_expression
---
# Policy: Replace Placeholder context.TODO() Before Production Release
`context.TODO()` disables cancellation and deadline propagation across downstream RPC and database calls.
