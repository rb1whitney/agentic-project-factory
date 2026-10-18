---
pack_id: wa-pack-java-cost
language: java
pillar: COST
rule_count: 5
rules:
- id: wa-java-cost-cached-thread-pool
  pillar: COST
  severity: HIGH
  language: java
  problem: '`newCachedThreadPool()` spawns unbounded OS threads under load spikes,
    inflating memory and CPU cost.'
  fix: Use a bounded `ThreadPoolExecutor` or virtual threads with semaphore limits.
  rule:
    pattern: Executors.newCachedThreadPool($$$ARGS)
- id: wa-java-cost-s3-client-create-in-loop
  pillar: COST
  severity: HIGH
  language: java
  problem: Creating `S3Client.create()` inside a loop leaks HTTP connection pools
    and repeats TLS handshakes.
  fix: Inject a singleton `S3Client` bean.
  rule:
    pattern: S3Client.create()
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-cost-dynamodb-client-in-loop
  pillar: COST
  severity: HIGH
  language: java
  problem: Creating `DynamoDbClient.create()` inside a loop recreates Netty/Apache
    HTTP pools per iteration.
  fix: Share a single `DynamoDbClient` bean.
  rule:
    pattern: DynamoDbClient.create()
    inside:
      any:
      - kind: for_statement
      - kind: enhanced_for_statement
      - kind: while_statement
      stopBy: end
- id: wa-java-cost-repo-findall
  pillar: COST
  severity: MEDIUM
  language: java
  problem: Unpaginated `.findAll()` loads the entire database table into JVM heap.
  fix: Use `findAll(Pageable)` or projection queries.
  rule:
    pattern: $REPO.findAll()
- id: wa-java-cost-system-gc
  pillar: COST
  severity: HIGH
  language: java
  problem: Explicit `System.gc()` triggers full stop-the-world garbage collection
    pauses, wasting CPU credits.
  fix: Remove `System.gc()` and let G1GC/ZGC manage heap ergonomics.
  rule:
    pattern: System.gc()
---

# Well-Architected Policy Pack: JAVA — COST

Contains **5** verified `ast-grep` structural policies for `java` mapped to the **COST** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-cost-cached-thread-pool` | `HIGH` | `newCachedThreadPool()` spawns unbounded OS threads under load spikes, inflating memory and CPU cost. | Use a bounded `ThreadPoolExecutor` or virtual threads with semaphore limits. |
| `wa-java-cost-s3-client-create-in-loop` | `HIGH` | Creating `S3Client.create()` inside a loop leaks HTTP connection pools and repeats TLS handshakes. | Inject a singleton `S3Client` bean. |
| `wa-java-cost-dynamodb-client-in-loop` | `HIGH` | Creating `DynamoDbClient.create()` inside a loop recreates Netty/Apache HTTP pools per iteration. | Share a single `DynamoDbClient` bean. |
| `wa-java-cost-repo-findall` | `MEDIUM` | Unpaginated `.findAll()` loads the entire database table into JVM heap. | Use `findAll(Pageable)` or projection queries. |
| `wa-java-cost-system-gc` | `HIGH` | Explicit `System.gc()` triggers full stop-the-world garbage collection pauses, wasting CPU credits. | Remove `System.gc()` and let G1GC/ZGC manage heap ergonomics. |
