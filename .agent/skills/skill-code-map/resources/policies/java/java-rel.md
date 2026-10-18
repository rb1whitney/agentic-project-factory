---
pack_id: wa-pack-java-rel
language: java
pillar: REL
rule_count: 13
rules:
- id: wa-java-rel-thread-stop
  pillar: REL
  severity: CRITICAL
  language: java
  problem: '`Thread.stop()` unlocks all monitors abruptly, corrupting shared object
    invariants.'
  fix: Use cooperative cancellation via `Thread.interrupt()`.
  rule:
    pattern: $T.stop()
- id: wa-java-rel-thread-suspend
  pillar: REL
  severity: HIGH
  language: java
  problem: '`Thread.suspend()` holds monitors while suspended and frequently causes
    deadlocks.'
  fix: Use `ReentrantLock` / `Condition` or `CompletableFuture`.
  rule:
    pattern: $T.suspend()
- id: wa-java-rel-system-exit
  pillar: REL
  severity: HIGH
  language: java
  problem: '`System.exit()` kills the entire JVM container abruptly.'
  fix: Throw an exception and let the application lifecycle manage shutdown.
  rule:
    pattern: System.exit($$$ARGS)
- id: wa-java-rel-runtime-halt
  pillar: REL
  severity: CRITICAL
  language: java
  problem: '`Runtime.halt()` terminates the JVM without running shutdown hooks or
    finalizers.'
  fix: Use graceful shutdown hooks.
  rule:
    pattern: Runtime.getRuntime().halt($$$ARGS)
- id: wa-java-rel-new-rest-template
  pillar: REL
  severity: HIGH
  language: java
  problem: '`new RestTemplate()` uses `SimpleClientHttpRequestFactory` with infinite
    read/connect timeouts by default.'
  fix: Inject a timeout-configured `RestTemplateBuilder` or `WebClient`.
  rule:
    pattern: new RestTemplate()
- id: wa-java-rel-http-client-default
  pillar: REL
  severity: MEDIUM
  language: java
  problem: '`HttpClient.newHttpClient()` sets no default connect timeout.'
  fix: Use `HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build()`.
  rule:
    pattern: HttpClient.newHttpClient()
- id: wa-java-rel-executors-fixed-pool
  pillar: REL
  severity: MEDIUM
  language: java
  problem: '`Executors.newFixedThreadPool()` uses an unbounded `LinkedBlockingQueue`
    that can cause OOM under backpressure.'
  fix: Use `new ThreadPoolExecutor(...)` with a bounded `ArrayBlockingQueue`.
  rule:
    pattern: Executors.newFixedThreadPool($$$ARGS)
- id: wa-java-rel-executors-single-pool
  pillar: REL
  severity: MEDIUM
  language: java
  problem: '`Executors.newSingleThreadExecutor()` uses an unbounded work queue.'
  fix: Use a bounded `ThreadPoolExecutor`.
  rule:
    pattern: Executors.newSingleThreadExecutor($$$ARGS)
- id: wa-java-rel-completable-future-get
  pillar: REL
  severity: HIGH
  language: java
  problem: Unbounded `Future.get()` with no timeout can block carrier threads forever.
  fix: Use `$FUT.get(10, TimeUnit.SECONDS)` or `orTimeout()`.
  rule:
    pattern: $FUT.get()
- id: wa-java-rel-latch-await-no-timeout
  pillar: REL
  severity: MEDIUM
  language: java
  problem: Unbounded `CountDownLatch.await()` hangs forever if a worker thread dies.
  fix: Use `$LATCH.await(30, TimeUnit.SECONDS)`.
  rule:
    pattern: $LATCH.await()
- id: wa-java-rel-simple-date-format
  pillar: REL
  severity: MEDIUM
  language: java
  problem: '`SimpleDateFormat` is mutable and not thread-safe.'
  fix: Use immutable `java.time.format.DateTimeFormatter`.
  rule:
    pattern: new SimpleDateFormat($$$ARGS)
- id: wa-java-rel-bigdecimal-double-ctor
  pillar: REL
  severity: MEDIUM
  language: java
  problem: '`new BigDecimal(double)` introduces IEEE-754 binary floating-point inaccuracy
    into monetary calculations.'
  fix: Use `BigDecimal.valueOf(...)` or `new BigDecimal(String)`.
  rule:
    pattern: new BigDecimal($VAL)
- id: sg-java-eqeq
  pillar: REL
  severity: HIGH
  language: java
  problem: '`$X == $X` or `$X != $X` is always true. (Unless the value compared is
    a float or double). To test if `$X` is not-a-number, use `Double.isNaN($X)`.'
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    all:
    - not:
        inside:
          pattern: assert $X;
          stopBy: end
    - not:
        inside:
          pattern: 'assert $X : $Y;'
          stopBy: end
    - any:
      - pattern: $X == $X
      - pattern: $X != $X
    - not:
        pattern: 1 == 1
---

# Well-Architected Policy Pack: JAVA — REL

Contains **13** verified `ast-grep` structural policies for `java` mapped to the **REL** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-rel-thread-stop` | `CRITICAL` | `Thread.stop()` unlocks all monitors abruptly, corrupting shared object invariants. | Use cooperative cancellation via `Thread.interrupt()`. |
| `wa-java-rel-thread-suspend` | `HIGH` | `Thread.suspend()` holds monitors while suspended and frequently causes deadlocks. | Use `ReentrantLock` / `Condition` or `CompletableFuture`. |
| `wa-java-rel-system-exit` | `HIGH` | `System.exit()` kills the entire JVM container abruptly. | Throw an exception and let the application lifecycle manage shutdown. |
| `wa-java-rel-runtime-halt` | `CRITICAL` | `Runtime.halt()` terminates the JVM without running shutdown hooks or finalizers. | Use graceful shutdown hooks. |
| `wa-java-rel-new-rest-template` | `HIGH` | `new RestTemplate()` uses `SimpleClientHttpRequestFactory` with infinite read/connect timeouts by default. | Inject a timeout-configured `RestTemplateBuilder` or `WebClient`. |
| `wa-java-rel-http-client-default` | `MEDIUM` | `HttpClient.newHttpClient()` sets no default connect timeout. | Use `HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build()`. |
| `wa-java-rel-executors-fixed-pool` | `MEDIUM` | `Executors.newFixedThreadPool()` uses an unbounded `LinkedBlockingQueue` that can cause OOM under backpressure. | Use `new ThreadPoolExecutor(...)` with a bounded `ArrayBlockingQueue`. |
| `wa-java-rel-executors-single-pool` | `MEDIUM` | `Executors.newSingleThreadExecutor()` uses an unbounded work queue. | Use a bounded `ThreadPoolExecutor`. |
| `wa-java-rel-completable-future-get` | `HIGH` | Unbounded `Future.get()` with no timeout can block carrier threads forever. | Use `$FUT.get(10, TimeUnit.SECONDS)` or `orTimeout()`. |
| `wa-java-rel-latch-await-no-timeout` | `MEDIUM` | Unbounded `CountDownLatch.await()` hangs forever if a worker thread dies. | Use `$LATCH.await(30, TimeUnit.SECONDS)`. |
| `wa-java-rel-simple-date-format` | `MEDIUM` | `SimpleDateFormat` is mutable and not thread-safe. | Use immutable `java.time.format.DateTimeFormatter`. |
| `wa-java-rel-bigdecimal-double-ctor` | `MEDIUM` | `new BigDecimal(double)` introduces IEEE-754 binary floating-point inaccuracy into monetary calculations. | Use `BigDecimal.valueOf(...)` or `new BigDecimal(String)`. |
| `sg-java-eqeq` | `HIGH` | `$X == $X` or `$X != $X` is always true. (Unless the value compared is a float or double). To test if `$X` is not-a-number, use `Double.isNaN($X)`. | Refactor pattern to comply with Well-Architected policy. |
