---
id: policy-py-blocking-sleep-in-async
pillar: PERF
severity: HIGH
language: python
fix: "Replace blocking time.sleep(...) with await asyncio.sleep(...) inside async functions."
rule:
  pattern: time.sleep($$$ARGS)
  inside:
    kind: function_definition
    regex: '^async\s+def\b'
    stopBy: end
---
# Policy: Never Block the Event Loop with time.sleep() in Async Functions
Calling synchronous `time.sleep()` inside an `async def` coroutine blocks the entire Python event loop and stalls all concurrent tasks.
