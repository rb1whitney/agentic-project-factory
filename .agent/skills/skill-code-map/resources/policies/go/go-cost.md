---
pack_id: wa-pack-go-cost
language: go
pillar: COST
rule_count: 5
rules:
- id: wa-go-cost-io-readall
  pillar: COST
  severity: MEDIUM
  language: go
  problem: Unbounded `io.ReadAll(r)` buffers the entire stream into RAM, risking OOM
    on large responses.
  fix: Wrap reader with `io.LimitReader(r, maxBytes)` before `io.ReadAll`.
  rule:
    pattern: io.ReadAll($R)
- id: wa-go-cost-ioutil-readall
  pillar: COST
  severity: MEDIUM
  language: go
  problem: Deprecated and unbounded `ioutil.ReadAll(r)` buffers full stream into memory.
  fix: Use `io.ReadAll(io.LimitReader(r, maxBytes))`.
  rule:
    pattern: ioutil.ReadAll($R)
- id: wa-go-cost-http-client-in-loop
  pillar: COST
  severity: HIGH
  language: go
  problem: Allocating `&http.Client{}` inside a loop creates a new connection pool
    per iteration.
  fix: Instantiate `&http.Client{}` once and share across requests.
  rule:
    pattern: '&http.Client{$$$FIELDS}'
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-cost-http-transport-in-loop
  pillar: COST
  severity: HIGH
  language: go
  problem: Allocating `&http.Transport{}` inside a loop disables TCP keep-alive reuse
    and leaks idle sockets.
  fix: Reuse a shared `*http.Transport`.
  rule:
    pattern: '&http.Transport{$$$FIELDS}'
    inside:
      kind: for_statement
      stopBy: end
- id: wa-go-cost-go-in-loop
  pillar: COST
  severity: HIGH
  language: go
  problem: Spawning unbounded `go func()` inside a `for` loop causes goroutine and
    memory spikes on large inputs.
  fix: Use `errgroup.Group` with `g.SetLimit(N)` or a worker pool.
  rule:
    kind: go_statement
    inside:
      kind: for_statement
      stopBy: end
---

# Well-Architected Policy Pack: GO — COST

Contains **5** verified `ast-grep` structural policies for `go` mapped to the **COST** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-cost-io-readall` | `MEDIUM` | Unbounded `io.ReadAll(r)` buffers the entire stream into RAM, risking OOM on large responses. | Wrap reader with `io.LimitReader(r, maxBytes)` before `io.ReadAll`. |
| `wa-go-cost-ioutil-readall` | `MEDIUM` | Deprecated and unbounded `ioutil.ReadAll(r)` buffers full stream into memory. | Use `io.ReadAll(io.LimitReader(r, maxBytes))`. |
| `wa-go-cost-http-client-in-loop` | `HIGH` | Allocating `&http.Client{}` inside a loop creates a new connection pool per iteration. | Instantiate `&http.Client{}` once and share across requests. |
| `wa-go-cost-http-transport-in-loop` | `HIGH` | Allocating `&http.Transport{}` inside a loop disables TCP keep-alive reuse and leaks idle sockets. | Reuse a shared `*http.Transport`. |
| `wa-go-cost-go-in-loop` | `HIGH` | Spawning unbounded `go func()` inside a `for` loop causes goroutine and memory spikes on large inputs. | Use `errgroup.Group` with `g.SetLimit(N)` or a worker pool. |
