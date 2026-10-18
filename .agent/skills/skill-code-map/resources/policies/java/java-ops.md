---
pack_id: wa-pack-java-ops
language: java
pillar: OPS
rule_count: 6
rules:
- id: wa-java-ops-syserr
  pillar: OPS
  severity: LOW
  language: java
  problem: '`System.err.println` bypasses structured SLF4J logging and correlation
    IDs.'
  fix: Use `log.error(...)` via SLF4J.
  rule:
    pattern: System.err.println($$$ARGS)
- id: wa-java-ops-print-stack-trace
  pillar: OPS
  severity: MEDIUM
  language: java
  problem: '`e.printStackTrace()` writes unstructured multi-line stack traces directly
    to stderr.'
  fix: Use `log.error("Context message", e)`.
  rule:
    pattern: $EX.printStackTrace()
- id: wa-java-ops-thread-dump-stack
  pillar: OPS
  severity: LOW
  language: java
  problem: Leftover `Thread.dumpStack()` writes noisy stack dumps to stderr.
  fix: Remove `Thread.dumpStack()` or log through SLF4J.
  rule:
    pattern: Thread.dumpStack()
- id: wa-java-ops-throw-runtime-exception
  pillar: OPS
  severity: LOW
  language: java
  problem: Throwing raw `RuntimeException` loses domain error semantics.
  fix: Throw a dedicated domain exception class.
  rule:
    pattern: new RuntimeException($$$ARGS)
- id: wa-java-ops-java-util-logging
  pillar: OPS
  severity: LOW
  language: java
  problem: Direct `java.util.logging.Logger` fragments logging configuration in Spring/SLF4J
    services.
  fix: Use `org.slf4j.LoggerFactory.getLogger(...)`.
  rule:
    pattern: Logger.getLogger($$$ARGS)
- id: wa-java-ops-system-getenv
  pillar: OPS
  severity: LOW
  language: java
  problem: Scattered `System.getenv()` calls bypass validated configuration properties.
  fix: Use `@ConfigurationProperties` or `@Value` injection.
  rule:
    pattern: System.getenv($KEY)
---

# Well-Architected Policy Pack: JAVA — OPS

Contains **6** verified `ast-grep` structural policies for `java` mapped to the **OPS** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-ops-syserr` | `LOW` | `System.err.println` bypasses structured SLF4J logging and correlation IDs. | Use `log.error(...)` via SLF4J. |
| `wa-java-ops-print-stack-trace` | `MEDIUM` | `e.printStackTrace()` writes unstructured multi-line stack traces directly to stderr. | Use `log.error("Context message", e)`. |
| `wa-java-ops-thread-dump-stack` | `LOW` | Leftover `Thread.dumpStack()` writes noisy stack dumps to stderr. | Remove `Thread.dumpStack()` or log through SLF4J. |
| `wa-java-ops-throw-runtime-exception` | `LOW` | Throwing raw `RuntimeException` loses domain error semantics. | Throw a dedicated domain exception class. |
| `wa-java-ops-java-util-logging` | `LOW` | Direct `java.util.logging.Logger` fragments logging configuration in Spring/SLF4J services. | Use `org.slf4j.LoggerFactory.getLogger(...)`. |
| `wa-java-ops-system-getenv` | `LOW` | Scattered `System.getenv()` calls bypass validated configuration properties. | Use `@ConfigurationProperties` or `@Value` injection. |
