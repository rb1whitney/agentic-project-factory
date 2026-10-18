---
id: policy-java-thread-sleep
pillar: PERF
severity: MEDIUM
language: java
fix: "Use ScheduledExecutorService, CompletableFuture.delayedExecutor, or virtual threads instead of Thread.sleep() on request threads."
rule:
  kind: method_invocation
  regex: '^Thread\.sleep\b'
---
# Policy: Avoid Blocking Thread.sleep() in Java Request Threads
Calling `Thread.sleep(...)` inside servlet or reactive worker threads pins carrier/pool threads and degrades concurrency under load.
