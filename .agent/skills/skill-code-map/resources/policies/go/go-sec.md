---
pack_id: wa-pack-go-sec
language: go
pillar: SEC
rule_count: 18
rules:
- id: wa-go-sec-md5-new
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: MD5 is cryptographically broken and unsuitable for security digests.
  fix: Use `sha256.New()`.
  rule:
    pattern: md5.New()
- id: wa-go-sec-md5-sum
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: '`md5.Sum()` is cryptographically broken.'
  fix: Use `sha256.Sum256()`.
  rule:
    pattern: md5.Sum($$$ARGS)
- id: wa-go-sec-sha1-new
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: SHA-1 is vulnerable to collision attacks.
  fix: Use `sha256.New()`.
  rule:
    pattern: sha1.New()
- id: wa-go-sec-sha1-sum
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: '`sha1.Sum()` is vulnerable to collision attacks.'
  fix: Use `sha256.Sum256()`.
  rule:
    pattern: sha1.Sum($$$ARGS)
- id: wa-go-sec-exec-sh-c
  pillar: SEC
  severity: CRITICAL
  language: go
  problem: Spawning `sh -c` with dynamic strings enables shell command injection.
  fix: Pass binary and discrete arguments directly to `exec.CommandContext(ctx, bin,
    arg1, arg2)`.
  rule:
    pattern: exec.Command("sh", "-c", $$$ARGS)
- id: wa-go-sec-exec-bash-c
  pillar: SEC
  severity: CRITICAL
  language: go
  problem: Spawning `bash -c` enables shell command injection.
  fix: Use `exec.CommandContext(ctx, bin, args...)` without a shell.
  rule:
    pattern: exec.Command("bash", "-c", $$$ARGS)
- id: wa-go-sec-http-listen-and-serve
  pillar: SEC
  severity: HIGH
  language: go
  problem: '`http.ListenAndServe` uses a default `http.Server` with zero `ReadHeaderTimeout`
    (Slowloris DoS risk) and cleartext HTTP.'
  fix: 'Configure `&http.Server{Addr: addr, Handler: h, ReadHeaderTimeout: 5 * time.Second}`.'
  rule:
    pattern: http.ListenAndServe($ADDR, $HANDLER)
- id: wa-go-sec-cgi-host
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: '`http.ServeFile` with unvalidated path input can lead to directory traversal.'
  fix: Sanitize paths via `filepath.Clean` and verify prefix with `strings.HasPrefix`.
  rule:
    pattern: http.ServeFile($W, $R, $PATH)
- id: wa-go-sec-chmod-777
  pillar: SEC
  severity: HIGH
  language: go
  problem: Setting file permissions to `0777` makes files world-writable.
  fix: Use `0600` for files or `0750` for directories.
  rule:
    pattern: os.Chmod($P, 0777)
- id: wa-go-sec-mkdirall-777
  pillar: SEC
  severity: HIGH
  language: go
  problem: Creating directories with `0777` allows any local user to modify contents.
  fix: Use `0750` or `0700`.
  rule:
    pattern: os.MkdirAll($P, 0777)
- id: wa-go-sec-unsafe-pointer
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: '`unsafe.Pointer` bypasses Go memory safety and garbage collector invariants.'
  fix: Avoid `unsafe.Pointer` unless required for low-level syscalls.
  rule:
    pattern: unsafe.Pointer($X)
- id: wa-go-sec-template-html-cast
  pillar: SEC
  severity: HIGH
  language: go
  problem: '`template.HTML()` marks strings as safe without escaping, risking XSS
    if `$X` is user-controlled.'
  fix: Let `html/template` auto-escape dynamic values.
  rule:
    pattern: template.HTML($X)
- id: sg-go-avoid-ssh-insecure-ignore-host-key
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: Disabled host key verification detected. This allows man-in-the-middle
    attacks. Use the 'golang.org/x/crypto/ssh/knownhosts' package to do host key verification.
    See https://skarlso.github.io/2019/02/17/go-ssh-with-host-key-verification/ to
    learn more about the problem and how to
  fix: https://skarlso.github.io/2019/02/17/go-ssh-with-host-key-verification/
  rule:
    pattern: ssh.InsecureIgnoreHostKey()
- id: sg-go-avoid-bind-to-all-interfaces
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: Detected a network listener listening on 0.0.0.0 or an empty string. This
    could unexpectedly expose the server publicly as it binds to all available interfaces.
    Instead, specify another IP address that is not 0.0.0.0 nor the empty string.
  fix: https://owasp.org/Top10/A01_2021-Broken_Access_Control
  rule:
    any:
    - pattern: tls.Listen($NETWORK, "=~/^0.0.0.0:.*$/", $$$ARGS)
    - pattern: net.Listen($NETWORK, "=~/^0.0.0.0:.*$/", $$$ARGS)
    - pattern: tls.Listen($NETWORK, "=~/^:.*$/", $$$ARGS)
    - pattern: net.Listen($NETWORK, "=~/^:.*$/", $$$ARGS)
- id: sg-go-use-tls
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: Found an HTTP server without TLS. Use 'http.ListenAndServeTLS' instead.
    See https://golang.org/pkg/net/http/#ListenAndServeTLS for more information.
  fix: http.ListenAndServeTLS($ADDR, certFile, keyFile, $HANDLER)
  rule:
    pattern: http.ListenAndServe($ADDR, $HANDLER)
- id: sg-go-reflect-makefunc
  pillar: SEC
  severity: HIGH
  language: go
  problem: '''reflect.MakeFunc'' detected. This will sidestep protections that are
    normally afforded by Go''s type system. Audit this call and be sure that user
    input cannot be used to affect the code generated by MakeFunc; otherwise, you
    will have a serious security vulnerability.'
  fix: https://owasp.org/Top10/A01_2021-Broken_Access_Control
  rule:
    pattern: reflect.MakeFunc($$$ARGS)
- id: sg-go-use-of-unsafe-block
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: Using the unsafe package in Go gives you low-level memory management and
    many of the strengths of the C language, but also steps around the type safety
    of Go and can lead to buffer overflows and possible arbitrary code execution by
    an attacker. Only use this package if you absolu
  fix: https://cwe.mitre.org/data/definitions/242.html
  rule:
    pattern: unsafe.$FUNC($$$ARGS)
- id: sg-go-bad-tmp-file-creation
  pillar: SEC
  severity: MEDIUM
  language: go
  problem: File creation in shared tmp directory without using `io.CreateTemp`.
  fix: https://owasp.org/Top10/A01_2021-Broken_Access_Control
  rule:
    any:
    - pattern: ioutil.WriteFile("=~//tmp/.*$/", $$$ARGS)
    - pattern: os.Create("=~//tmp/.*$/", $$$ARGS)
    - pattern: os.WriteFile("=~//tmp/.*$/", $$$ARGS)
---

# Well-Architected Policy Pack: GO — SEC

Contains **18** verified `ast-grep` structural policies for `go` mapped to the **SEC** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-go-sec-md5-new` | `MEDIUM` | MD5 is cryptographically broken and unsuitable for security digests. | Use `sha256.New()`. |
| `wa-go-sec-md5-sum` | `MEDIUM` | `md5.Sum()` is cryptographically broken. | Use `sha256.Sum256()`. |
| `wa-go-sec-sha1-new` | `MEDIUM` | SHA-1 is vulnerable to collision attacks. | Use `sha256.New()`. |
| `wa-go-sec-sha1-sum` | `MEDIUM` | `sha1.Sum()` is vulnerable to collision attacks. | Use `sha256.Sum256()`. |
| `wa-go-sec-exec-sh-c` | `CRITICAL` | Spawning `sh -c` with dynamic strings enables shell command injection. | Pass binary and discrete arguments directly to `exec.CommandContext(ctx, bin, arg1, arg2)`. |
| `wa-go-sec-exec-bash-c` | `CRITICAL` | Spawning `bash -c` enables shell command injection. | Use `exec.CommandContext(ctx, bin, args...)` without a shell. |
| `wa-go-sec-http-listen-and-serve` | `HIGH` | `http.ListenAndServe` uses a default `http.Server` with zero `ReadHeaderTimeout` (Slowloris DoS risk) and cleartext HTTP. | Configure `&http.Server{Addr: addr, Handler: h, ReadHeaderTimeout: 5 * time.Second}`. |
| `wa-go-sec-cgi-host` | `MEDIUM` | `http.ServeFile` with unvalidated path input can lead to directory traversal. | Sanitize paths via `filepath.Clean` and verify prefix with `strings.HasPrefix`. |
| `wa-go-sec-chmod-777` | `HIGH` | Setting file permissions to `0777` makes files world-writable. | Use `0600` for files or `0750` for directories. |
| `wa-go-sec-mkdirall-777` | `HIGH` | Creating directories with `0777` allows any local user to modify contents. | Use `0750` or `0700`. |
| `wa-go-sec-unsafe-pointer` | `MEDIUM` | `unsafe.Pointer` bypasses Go memory safety and garbage collector invariants. | Avoid `unsafe.Pointer` unless required for low-level syscalls. |
| `wa-go-sec-template-html-cast` | `HIGH` | `template.HTML()` marks strings as safe without escaping, risking XSS if `$X` is user-controlled. | Let `html/template` auto-escape dynamic values. |
| `sg-go-avoid-ssh-insecure-ignore-host-key` | `MEDIUM` | Disabled host key verification detected. This allows man-in-the-middle attacks. Use the 'golang.org/x/crypto/ssh/knownhosts' package to do host key verification. See https://skarlso.github.io/2019/02/17/go-ssh-with-host-key-verification/ to learn more about the problem and how to | https://skarlso.github.io/2019/02/17/go-ssh-with-host-key-verification/ |
| `sg-go-avoid-bind-to-all-interfaces` | `MEDIUM` | Detected a network listener listening on 0.0.0.0 or an empty string. This could unexpectedly expose the server publicly as it binds to all available interfaces. Instead, specify another IP address that is not 0.0.0.0 nor the empty string. | https://owasp.org/Top10/A01_2021-Broken_Access_Control |
| `sg-go-use-tls` | `MEDIUM` | Found an HTTP server without TLS. Use 'http.ListenAndServeTLS' instead. See https://golang.org/pkg/net/http/#ListenAndServeTLS for more information. | http.ListenAndServeTLS($ADDR, certFile, keyFile, $HANDLER) |
| `sg-go-reflect-makefunc` | `HIGH` | 'reflect.MakeFunc' detected. This will sidestep protections that are normally afforded by Go's type system. Audit this call and be sure that user input cannot be used to affect the code generated by MakeFunc; otherwise, you will have a serious security vulnerability. | https://owasp.org/Top10/A01_2021-Broken_Access_Control |
| `sg-go-use-of-unsafe-block` | `MEDIUM` | Using the unsafe package in Go gives you low-level memory management and many of the strengths of the C language, but also steps around the type safety of Go and can lead to buffer overflows and possible arbitrary code execution by an attacker. Only use this package if you absolu | https://cwe.mitre.org/data/definitions/242.html |
| `sg-go-bad-tmp-file-creation` | `MEDIUM` | File creation in shared tmp directory without using `io.CreateTemp`. | https://owasp.org/Top10/A01_2021-Broken_Access_Control |
