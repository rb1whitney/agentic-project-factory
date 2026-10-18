---
pack_id: wa-pack-java-perf
language: java
pillar: PERF
rule_count: 10
rules:
- id: wa-java-perf-thread-sleep
  pillar: PERF
  severity: HIGH
  language: java
  problem: Blocking `Thread.sleep()` pins OS/carrier threads and degrades throughput.
  fix: Use `ScheduledExecutorService` or non-blocking delays.
  rule:
    pattern: Thread.sleep($$$ARGS)
- id: wa-java-perf-pattern-compile-in-loop
  pillar: PERF
  severity: HIGH
  language: java
  problem: Compiling regex via `Pattern.compile()` inside a loop wastes CPU and heap.
  fix: Hoist `Pattern.compile()` to a `private static final Pattern` constant.
  rule:
    pattern: Pattern.compile($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-object-mapper-in-loop
  pillar: PERF
  severity: HIGH
  language: java
  problem: Instantiating Jackson `ObjectMapper` inside a loop rebuilds serializer
    caches on every iteration.
  fix: Inject or share a single thread-safe `ObjectMapper` bean.
  rule:
    pattern: new ObjectMapper($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-gson-in-loop
  pillar: PERF
  severity: MEDIUM
  language: java
  problem: Creating `new Gson()` inside a loop wastes reflection cache initialization.
  fix: Share a single static/injected `Gson` instance.
  rule:
    pattern: new Gson($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-class-forname-in-loop
  pillar: PERF
  severity: HIGH
  language: java
  problem: '`Class.forName()` inside a loop contends on classloader locks.'
  fix: Cache resolved `Class<?>` references outside the loop.
  rule:
    pattern: Class.forName($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-driver-manager-get-conn
  pillar: PERF
  severity: HIGH
  language: java
  problem: '`DriverManager.getConnection()` opens a raw unpooled physical TCP database
    connection per call.'
  fix: Use a pooled `DataSource` (e.g., HikariCP).
  rule:
    pattern: DriverManager.getConnection($$$ARGS)
- id: wa-java-perf-files-read-all-bytes-in-loop
  pillar: PERF
  severity: MEDIUM
  language: java
  problem: Loading entire files via `Files.readAllBytes()` inside a loop spikes heap
    allocation.
  fix: Stream via `BufferedInputStream` or `Files.newInputStream()`.
  rule:
    pattern: Files.readAllBytes($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-string-format-in-loop
  pillar: PERF
  severity: LOW
  language: java
  problem: '`String.format()` parses format specifiers via regex on every loop iteration.'
  fix: Use `StringBuilder` in hot loops.
  rule:
    pattern: String.format($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-rest-exchange-in-loop
  pillar: PERF
  severity: HIGH
  language: java
  problem: Synchronous HTTP `.exchange()` inside a loop causes serial N+1 network
    latency.
  fix: Batch API requests or use bounded `CompletableFuture.allOf()`.
  rule:
    pattern: $CLIENT.exchange($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-perf-jdbc-query-in-loop
  pillar: PERF
  severity: HIGH
  language: java
  problem: Executing `queryForObject()` inside a loop creates an N+1 database query
    bottleneck.
  fix: Use a batch `IN (...)` query outside the loop.
  rule:
    pattern: $JDBC.queryForObject($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
---

# Well-Architected Policy Pack: JAVA — PERF

Contains **10** verified `ast-grep` structural policies for `java` mapped to the **PERF** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-perf-thread-sleep` | `HIGH` | Blocking `Thread.sleep()` pins OS/carrier threads and degrades throughput. | Use `ScheduledExecutorService` or non-blocking delays. |
| `wa-java-perf-pattern-compile-in-loop` | `HIGH` | Compiling regex via `Pattern.compile()` inside a loop wastes CPU and heap. | Hoist `Pattern.compile()` to a `private static final Pattern` constant. |
| `wa-java-perf-object-mapper-in-loop` | `HIGH` | Instantiating Jackson `ObjectMapper` inside a loop rebuilds serializer caches on every iteration. | Inject or share a single thread-safe `ObjectMapper` bean. |
| `wa-java-perf-gson-in-loop` | `MEDIUM` | Creating `new Gson()` inside a loop wastes reflection cache initialization. | Share a single static/injected `Gson` instance. |
| `wa-java-perf-class-forname-in-loop` | `HIGH` | `Class.forName()` inside a loop contends on classloader locks. | Cache resolved `Class<?>` references outside the loop. |
| `wa-java-perf-driver-manager-get-conn` | `HIGH` | `DriverManager.getConnection()` opens a raw unpooled physical TCP database connection per call. | Use a pooled `DataSource` (e.g., HikariCP). |
| `wa-java-perf-files-read-all-bytes-in-loop` | `MEDIUM` | Loading entire files via `Files.readAllBytes()` inside a loop spikes heap allocation. | Stream via `BufferedInputStream` or `Files.newInputStream()`. |
| `wa-java-perf-string-format-in-loop` | `LOW` | `String.format()` parses format specifiers via regex on every loop iteration. | Use `StringBuilder` in hot loops. |
| `wa-java-perf-rest-exchange-in-loop` | `HIGH` | Synchronous HTTP `.exchange()` inside a loop causes serial N+1 network latency. | Batch API requests or use bounded `CompletableFuture.allOf()`. |
| `wa-java-perf-jdbc-query-in-loop` | `HIGH` | Executing `queryForObject()` inside a loop creates an N+1 database query bottleneck. | Use a batch `IN (...)` query outside the loop. |
