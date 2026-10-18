---
pack_id: wa-pack-java-sus
language: java
pillar: SUS
rule_count: 5
rules:
- id: wa-java-sus-nested-for-3
  pillar: SUS
  severity: MEDIUM
  language: java
  problem: Triply nested `for` loop (O(N^3)) harms maintainability and CPU efficiency.
  fix: Index inner collection in a `Map` before iterating.
  rule:
    kind: for_statement
    inside:
      kind: for_statement
      inside:
        kind: for_statement
        stopBy: end
      stopBy: end
- id: wa-java-sus-vector-usage
  pillar: SUS
  severity: LOW
  language: java
  problem: Legacy `java.util.Vector` synchronizes every element access needlessly.
  fix: Use `new ArrayList<>()` or `Collections.synchronizedList()`.
  rule:
    pattern: new Vector($$$ARGS)
- id: wa-java-sus-hashtable-usage
  pillar: SUS
  severity: LOW
  language: java
  problem: Legacy `java.util.Hashtable` locks the entire table on every operation.
  fix: Use `HashMap` or `ConcurrentHashMap`.
  rule:
    pattern: new Hashtable($$$ARGS)
- id: wa-java-sus-stringbuffer-usage
  pillar: SUS
  severity: LOW
  language: java
  problem: '`StringBuffer` pays unnecessary synchronization overhead for local string
    building.'
  fix: Use `new StringBuilder()`.
  rule:
    pattern: new StringBuffer($$$ARGS)
- id: wa-java-sus-thread-run-direct
  pillar: SUS
  severity: HIGH
  language: java
  problem: Calling `.run()` directly executes on the current thread instead of starting
    a new thread.
  fix: Call `.start()` or submit to an `ExecutorService`.
  rule:
    pattern: $T.run()
---

# Well-Architected Policy Pack: JAVA — SUS

Contains **5** verified `ast-grep` structural policies for `java` mapped to the **SUS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-sus-nested-for-3` | `MEDIUM` | Triply nested `for` loop (O(N^3)) harms maintainability and CPU efficiency. | Index inner collection in a `Map` before iterating. |
| `wa-java-sus-vector-usage` | `LOW` | Legacy `java.util.Vector` synchronizes every element access needlessly. | Use `new ArrayList<>()` or `Collections.synchronizedList()`. |
| `wa-java-sus-hashtable-usage` | `LOW` | Legacy `java.util.Hashtable` locks the entire table on every operation. | Use `HashMap` or `ConcurrentHashMap`. |
| `wa-java-sus-stringbuffer-usage` | `LOW` | `StringBuffer` pays unnecessary synchronization overhead for local string building. | Use `new StringBuilder()`. |
| `wa-java-sus-thread-run-direct` | `HIGH` | Calling `.run()` directly executes on the current thread instead of starting a new thread. | Call `.start()` or submit to an `ExecutorService`. |
