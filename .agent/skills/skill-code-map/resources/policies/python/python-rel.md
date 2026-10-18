---
pack_id: wa-pack-python-rel
language: python
pillar: REL
rule_count: 35
rules:
- id: wa-py-rel-asyncio-create-task-unawaited
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Background task created with `asyncio.create_task()` should retain a reference
    to prevent GC disappearance.
  fix: Store task in a set (`tasks.add(task); task.add_done_callback(tasks.discard)`).
  rule:
    pattern: asyncio.create_task($CORO)
- id: wa-py-rel-urllib-urlopen
  pillar: REL
  severity: HIGH
  language: python
  problem: '`urlopen()` called with a single positional argument has no timeout and
    can hang indefinitely.'
  fix: Pass an explicit `timeout=10` argument.
  rule:
    pattern: urllib.request.urlopen($URL)
- id: wa-py-rel-requests-get-single-arg
  pillar: REL
  severity: HIGH
  language: python
  problem: '`requests.get($URL)` without `timeout=` can block worker threads forever.'
  fix: Pass `timeout=(3.05, 10)` to all `requests` calls.
  rule:
    pattern: requests.get($URL)
- id: wa-py-rel-requests-post-single-arg
  pillar: REL
  severity: HIGH
  language: python
  problem: '`requests.post($URL)` without `timeout=` can hang indefinitely.'
  fix: Pass `timeout=(3.05, 10)` to all `requests` calls.
  rule:
    pattern: requests.post($URL)
- id: wa-py-rel-sys-exit
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Direct `sys.exit()` inside library or handler code terminates the worker
    process abruptly.
  fix: Raise a domain exception and handle exit only in CLI `main()`.
  rule:
    pattern: sys.exit($$$ARGS)
- id: wa-py-rel-os-exit
  pillar: REL
  severity: HIGH
  language: python
  problem: '`os._exit()` terminates immediately without running `finally` blocks or
    flushing stdio buffers.'
  fix: Use normal exception propagation or `sys.exit()` at entrypoint.
  rule:
    pattern: os._exit($$$ARGS)
- id: wa-py-rel-time-sleep-in-except
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Fixed `time.sleep()` inside `except` block causes thundering-herd retries.
  fix: Use exponential backoff with jitter (`tenacity` or `random.uniform`).
  rule:
    pattern: time.sleep($$$ARGS)
    inside:
      kind: except_clause
      stopBy: end
- id: wa-py-rel-thread-start-in-loop
  pillar: REL
  severity: HIGH
  language: python
  problem: Spawning unbounded threads inside a loop risks OS thread exhaustion.
  fix: Use `concurrent.futures.ThreadPoolExecutor(max_workers=N)`.
  rule:
    pattern: threading.Thread($$$ARGS).start()
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-rel-subprocess-popen-in-loop
  pillar: REL
  severity: HIGH
  language: python
  problem: Spawning `subprocess.Popen` in a loop without bounded concurrency leaks
    child processes/file descriptors.
  fix: Use bounded worker pools or `subprocess.run` with timeouts.
  rule:
    pattern: subprocess.Popen($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-rel-lock-acquire
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Manual `.acquire()` without `with lock:` risks permanent deadlock if an
    exception occurs.
  fix: Use `with lock:` context manager.
  rule:
    pattern: $LOCK.acquire()
- id: wa-py-rel-open-in-loop
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Opening files repeatedly inside a loop increases file-descriptor churn
    and I/O latency.
  fix: Hoist file open outside loop or batch writes.
  rule:
    pattern: open($PATH)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-rel-asyncio-run-in-async
  pillar: REL
  severity: HIGH
  language: python
  problem: 'Calling `asyncio.run()` inside an `async def` raises `RuntimeError: Cannot
    run the event loop while another loop is running`.'
  fix: Await the coroutine directly (`await coro`).
  rule:
    pattern: asyncio.run($$$ARGS)
    inside:
      kind: function_definition
      regex: ^async\s+def\b
      stopBy: end
- id: sg-python-python36-compatibility-ssl
  pillar: REL
  severity: HIGH
  language: python
  problem: this function is only available on Python 3.6+
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: ssl.get_ciphers()
- id: sg-python-python36-compatibility-popen1
  pillar: REL
  severity: HIGH
  language: python
  problem: the `errors` argument to Popen is only available on Python 3.6+
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: subprocess.Popen(errors=$X, $$$ARGS)
- id: sg-python-python36-compatibility-popen2
  pillar: REL
  severity: HIGH
  language: python
  problem: the `encoding` argument to Popen is only available on Python 3.6+
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: subprocess.Popen(encoding=$X, $$$ARGS)
- id: sg-python-python37-compatibility-importlib
  pillar: REL
  severity: HIGH
  language: python
  problem: source_hash' is only available on Python 3.7+. This does not work in lower
    versions, and therefore is not backwards compatible. Instead, use another hash
    function.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: importlib.source_hash()
- id: sg-python-python37-compatibility-importlib2
  pillar: REL
  severity: HIGH
  language: python
  problem: Found 'importlib.resources', which is a module only available on Python
    3.7+. This does not work in lower versions, and therefore is not backwards compatible.
    Use importlib_resources instead for older Python versions.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: import importlib.resources
- id: sg-python-python37-compatibility-httpconn
  pillar: REL
  severity: HIGH
  language: python
  problem: Found usage of the 'blocksize' argument in a HTTPConnection call. This
    is only available on Python 3.7+ and is therefore not backwards compatible. Remove
    this in order for this code to work in Python 3.6 and below.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: http.client.HTTPConnection(blocksize=$X, $$$ARGS)
- id: sg-python-python37-compatibility-httpsconn
  pillar: REL
  severity: HIGH
  language: python
  problem: Found usage of the 'blocksize' argument in a HTTPSConnection call. This
    is only available on Python 3.7+ and is therefore not backwards compatible. Remove
    this in order for this code to work in Python 3.6 and below.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: http.client.HTTPSConnection(blocksize=$X, $$$ARGS)
- id: sg-python-python37-compatibility-importlib3
  pillar: REL
  severity: HIGH
  language: python
  problem: Found usage of 'importlib.abc.ResourceReader'. This module is only available
    on Python 3.7+ and is therefore not backwards compatible. Instead, use another
    loader.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: import importlib.abc.ResourceReader
- id: sg-python-python37-compatibility-textiowrapper
  pillar: REL
  severity: HIGH
  language: python
  problem: Found usage of 'importlib.abc.ResourceReader'. This module is only available
    on Python 3.7+ and is therefore not backwards compatible. Instead, use another
    loader.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: TextIOWrapper.reconfigure($$$ARGS)
- id: sg-python-python37-compatibility-ipv6network1
  pillar: REL
  severity: HIGH
  language: python
  problem: IPv6Network.subnet_of is only available on Python 3.7+ and is therefore
    not backwards compatible. Instead, check if the subnet is in 'subnets'.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: ipaddress.IPv6Network.subnet_of($X)
- id: sg-python-python37-compatibility-ipv6network2
  pillar: REL
  severity: HIGH
  language: python
  problem: IPv6Network.supernet_of is only available on Python 3.7+ and is therefore
    not backwards compatible. Instead, check if the supernet is in 'supernet'.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: ipaddress.IPv6Network.supernet_of($X)
- id: sg-python-python37-compatibility-ipv4network1
  pillar: REL
  severity: HIGH
  language: python
  problem: IPv4Network.subnet_of is only available on Python 3.7+ and is therefore
    not backwards compatible. Instead, check if the subnet is in 'subnets'.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: ipaddress.IPv4Network.subnet_of($X)
- id: sg-python-python37-compatibility-ipv4network2
  pillar: REL
  severity: HIGH
  language: python
  problem: IPv4Network.supernet_of is only available on Python 3.7+ and is therefore
    not backwards compatible. Instead, check if the supernet is in 'supernet'.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: ipaddress.IPv4Network.supernet_of($X)
- id: sg-python-python37-compatibility-locale1
  pillar: REL
  severity: HIGH
  language: python
  problem: Found usage of the 'monetary' argument in a function call of 'locale.format_string'.
    This is only available on Python 3.7+ and is therefore not backwards compatible.
    Instead, remove the 'monetary' argument.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: locale.format_string(monetary=$X, $$$ARGS)
- id: sg-python-python37-compatibility-math1
  pillar: REL
  severity: HIGH
  language: python
  problem: math.remainder is only available on Python 3.7+ and is therefore not backwards
    compatible. Instead, use math.fmod() or calculate $X - n* $Y.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: math.remainder($X, $Y)
- id: sg-python-python37-compatibility-multiprocess1
  pillar: REL
  severity: HIGH
  language: python
  problem: multiprocessing.Process.close() is only available on Python 3.7+ and is
    therefore not backwards compatible. Instead, use join().
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: multiprocessing.Process.close()
- id: sg-python-python37-compatibility-multiprocess2
  pillar: REL
  severity: HIGH
  language: python
  problem: multiprocessing.Process.kill() is only available on Python 3.7+ and is
    therefore not backwards compatible. Instead, use terminate().
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: multiprocessing.Process.kill()
- id: sg-python-python37-compatibility-os1
  pillar: REL
  severity: HIGH
  language: python
  problem: os.preadv() is only available on Python 3.7+ and is therefore not backwards
    compatible. Instead, use a combination of os.readv() and os.pread().
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: os.preadv($$$ARGS)
- id: sg-python-python37-compatibility-pdb
  pillar: REL
  severity: HIGH
  language: python
  problem: pdb.set_trace() with the header argument is only available on Python 3.7+
    and is therefore not backwards compatible. Instead, use set_trace() without the
    header argument.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: pdb.set_trace(header=$X, $$$ARGS)
- id: sg-python-identical-is-comparison
  pillar: REL
  severity: HIGH
  language: python
  problem: Found identical comparison using is. Ensure this is what you intended.
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: $S is $S
- id: sg-python-use-sys-exit
  pillar: REL
  severity: MEDIUM
  language: python
  problem: Detected use of `exit`. Use `sys.exit` over the python shell `exit` built-in.
    `exit` is a helper for the interactive shell and may not be available on all Python
    implementations.
  fix: sys.exit($X)
  rule:
    all:
    - pattern: exit($X)
    - not:
        pattern: sys.exit($X)
- id: sg-python-pdb-remove
  pillar: REL
  severity: MEDIUM
  language: python
  problem: pdb is an interactive debugging tool and you may have forgotten to remove
    it before committing your code
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    any:
    - pattern: pdb.$X($$$ARGS)
    - pattern: pdb.Pdb.$X($$$ARGS)
- id: sg-python-tempfile-insecure
  pillar: REL
  severity: HIGH
  language: python
  problem: 'Use tempfile.NamedTemporaryFile instead. From the official Python documentation:
    THIS FUNCTION IS UNSAFE AND SHOULD NOT BE USED. The file name may refer to a file
    that did not exist at some point, but by the time you get around to creating it,
    someone else may have beaten you to '
  fix: Refactor pattern to comply with Well-Architected policy.
  rule:
    pattern: tempfile.mktemp($$$ARGS)
---

# Well-Architected Policy Pack: PYTHON — REL

Contains **35** verified `ast-grep` structural policies for `python` mapped to the **REL** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-rel-asyncio-create-task-unawaited` | `MEDIUM` | Background task created with `asyncio.create_task()` should retain a reference to prevent GC disappearance. | Store task in a set (`tasks.add(task); task.add_done_callback(tasks.discard)`). |
| `wa-py-rel-urllib-urlopen` | `HIGH` | `urlopen()` called with a single positional argument has no timeout and can hang indefinitely. | Pass an explicit `timeout=10` argument. |
| `wa-py-rel-requests-get-single-arg` | `HIGH` | `requests.get($URL)` without `timeout=` can block worker threads forever. | Pass `timeout=(3.05, 10)` to all `requests` calls. |
| `wa-py-rel-requests-post-single-arg` | `HIGH` | `requests.post($URL)` without `timeout=` can hang indefinitely. | Pass `timeout=(3.05, 10)` to all `requests` calls. |
| `wa-py-rel-sys-exit` | `MEDIUM` | Direct `sys.exit()` inside library or handler code terminates the worker process abruptly. | Raise a domain exception and handle exit only in CLI `main()`. |
| `wa-py-rel-os-exit` | `HIGH` | `os._exit()` terminates immediately without running `finally` blocks or flushing stdio buffers. | Use normal exception propagation or `sys.exit()` at entrypoint. |
| `wa-py-rel-time-sleep-in-except` | `MEDIUM` | Fixed `time.sleep()` inside `except` block causes thundering-herd retries. | Use exponential backoff with jitter (`tenacity` or `random.uniform`). |
| `wa-py-rel-thread-start-in-loop` | `HIGH` | Spawning unbounded threads inside a loop risks OS thread exhaustion. | Use `concurrent.futures.ThreadPoolExecutor(max_workers=N)`. |
| `wa-py-rel-subprocess-popen-in-loop` | `HIGH` | Spawning `subprocess.Popen` in a loop without bounded concurrency leaks child processes/file descriptors. | Use bounded worker pools or `subprocess.run` with timeouts. |
| `wa-py-rel-lock-acquire` | `MEDIUM` | Manual `.acquire()` without `with lock:` risks permanent deadlock if an exception occurs. | Use `with lock:` context manager. |
| `wa-py-rel-open-in-loop` | `MEDIUM` | Opening files repeatedly inside a loop increases file-descriptor churn and I/O latency. | Hoist file open outside loop or batch writes. |
| `wa-py-rel-asyncio-run-in-async` | `HIGH` | Calling `asyncio.run()` inside an `async def` raises `RuntimeError: Cannot run the event loop while another loop is running`. | Await the coroutine directly (`await coro`). |
| `sg-python-python36-compatibility-ssl` | `HIGH` | this function is only available on Python 3.6+ | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python36-compatibility-popen1` | `HIGH` | the `errors` argument to Popen is only available on Python 3.6+ | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python36-compatibility-popen2` | `HIGH` | the `encoding` argument to Popen is only available on Python 3.6+ | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-importlib` | `HIGH` | source_hash' is only available on Python 3.7+. This does not work in lower versions, and therefore is not backwards compatible. Instead, use another hash function. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-importlib2` | `HIGH` | Found 'importlib.resources', which is a module only available on Python 3.7+. This does not work in lower versions, and therefore is not backwards compatible. Use importlib_resources instead for older Python versions. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-httpconn` | `HIGH` | Found usage of the 'blocksize' argument in a HTTPConnection call. This is only available on Python 3.7+ and is therefore not backwards compatible. Remove this in order for this code to work in Python 3.6 and below. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-httpsconn` | `HIGH` | Found usage of the 'blocksize' argument in a HTTPSConnection call. This is only available on Python 3.7+ and is therefore not backwards compatible. Remove this in order for this code to work in Python 3.6 and below. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-importlib3` | `HIGH` | Found usage of 'importlib.abc.ResourceReader'. This module is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use another loader. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-textiowrapper` | `HIGH` | Found usage of 'importlib.abc.ResourceReader'. This module is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use another loader. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-ipv6network1` | `HIGH` | IPv6Network.subnet_of is only available on Python 3.7+ and is therefore not backwards compatible. Instead, check if the subnet is in 'subnets'. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-ipv6network2` | `HIGH` | IPv6Network.supernet_of is only available on Python 3.7+ and is therefore not backwards compatible. Instead, check if the supernet is in 'supernet'. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-ipv4network1` | `HIGH` | IPv4Network.subnet_of is only available on Python 3.7+ and is therefore not backwards compatible. Instead, check if the subnet is in 'subnets'. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-ipv4network2` | `HIGH` | IPv4Network.supernet_of is only available on Python 3.7+ and is therefore not backwards compatible. Instead, check if the supernet is in 'supernet'. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-locale1` | `HIGH` | Found usage of the 'monetary' argument in a function call of 'locale.format_string'. This is only available on Python 3.7+ and is therefore not backwards compatible. Instead, remove the 'monetary' argument. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-math1` | `HIGH` | math.remainder is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use math.fmod() or calculate $X - n* $Y. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-multiprocess1` | `HIGH` | multiprocessing.Process.close() is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use join(). | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-multiprocess2` | `HIGH` | multiprocessing.Process.kill() is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use terminate(). | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-os1` | `HIGH` | os.preadv() is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use a combination of os.readv() and os.pread(). | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-python37-compatibility-pdb` | `HIGH` | pdb.set_trace() with the header argument is only available on Python 3.7+ and is therefore not backwards compatible. Instead, use set_trace() without the header argument. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-identical-is-comparison` | `HIGH` | Found identical comparison using is. Ensure this is what you intended. | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-use-sys-exit` | `MEDIUM` | Detected use of `exit`. Use `sys.exit` over the python shell `exit` built-in. `exit` is a helper for the interactive shell and may not be available on all Python implementations. | sys.exit($X) |
| `sg-python-pdb-remove` | `MEDIUM` | pdb is an interactive debugging tool and you may have forgotten to remove it before committing your code | Refactor pattern to comply with Well-Architected policy. |
| `sg-python-tempfile-insecure` | `HIGH` | Use tempfile.NamedTemporaryFile instead. From the official Python documentation: THIS FUNCTION IS UNSAFE AND SHOULD NOT BE USED. The file name may refer to a file that did not exist at some point, but by the time you get around to creating it, someone else may have beaten you to  | Refactor pattern to comply with Well-Architected policy. |
