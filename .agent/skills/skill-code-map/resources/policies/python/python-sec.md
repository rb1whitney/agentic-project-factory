---
pack_id: wa-pack-python-sec
language: python
pillar: SEC
rule_count: 33
rules:
- id: wa-py-sec-eval
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: Dynamic code execution via `eval()` enables arbitrary code injection.
  fix: Use `ast.literal_eval()` or explicit parsers.
  rule:
    pattern: eval($$$ARGS)
- id: wa-py-sec-exec
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: Dynamic code execution via `exec()` enables arbitrary code execution.
  fix: Remove `exec()` and use structured dispatch tables.
  rule:
    pattern: exec($$$ARGS)
- id: wa-py-sec-os-system
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: '`os.system()` invokes a subshell vulnerable to command injection.'
  fix: Use `subprocess.run([cmd, arg], shell=False, check=True)`.
  rule:
    pattern: os.system($$$ARGS)
- id: wa-py-sec-os-popen
  pillar: SEC
  severity: HIGH
  language: python
  problem: '`os.popen()` invokes a shell command stream vulnerable to injection.'
  fix: Use `subprocess.run(..., shell=False, capture_output=True)`.
  rule:
    pattern: os.popen($$$ARGS)
- id: wa-py-sec-pickle-loads
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: '`pickle.loads()` executes arbitrary bytecode on untrusted payloads.'
  fix: Use `json.loads()` or `msgpack` with strict schema validation.
  rule:
    pattern: pickle.loads($$$ARGS)
- id: wa-py-sec-pickle-load
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: '`pickle.load()` deserializes untrusted streams with arbitrary code execution.'
  fix: Use `json.load()` or safe serialization formats.
  rule:
    pattern: pickle.load($$$ARGS)
- id: wa-py-sec-marshal-loads
  pillar: SEC
  severity: HIGH
  language: python
  problem: '`marshal.loads()` is not secure against erroneous or maliciously constructed
    data.'
  fix: Use `json.loads()` instead of `marshal`.
  rule:
    pattern: marshal.loads($$$ARGS)
- id: wa-py-sec-shelve-open
  pillar: SEC
  severity: HIGH
  language: python
  problem: '`shelve` is backed by `pickle` and can execute arbitrary code when loading.'
  fix: Use `sqlite3` or JSON storage instead.
  rule:
    pattern: shelve.open($$$ARGS)
- id: wa-py-sec-md5
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: MD5 is cryptographically broken and unsuitable for security digests.
  fix: Use `hashlib.sha256()` or `hashlib.blake2b()`.
  rule:
    pattern: hashlib.md5($$$ARGS)
- id: wa-py-sec-sha1
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: SHA-1 is vulnerable to collision attacks.
  fix: Use `hashlib.sha256()` or stronger.
  rule:
    pattern: hashlib.sha1($$$ARGS)
- id: wa-py-sec-mktemp
  pillar: SEC
  severity: HIGH
  language: python
  problem: '`tempfile.mktemp()` has an inherent TOCTOU symlink race condition.'
  fix: Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()`.
  rule:
    pattern: tempfile.mktemp($$$ARGS)
- id: wa-py-sec-ssl-unverified
  pillar: SEC
  severity: CRITICAL
  language: python
  problem: Disabling SSL certificate verification exposes connections to MITM attacks.
  fix: Use `ssl.create_default_context()`.
  rule:
    pattern: ssl._create_unverified_context($$$ARGS)
- id: sg-python-httpsconnection-detected
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: The HTTPSConnection API has changed frequently with minor releases of Python.
    Ensure you are using the API for your version of Python securely. For example,
    Python 3 versions prior to 3.4.3 will not verify SSL certificates by default.
    See https://docs.python.org/3/library/http.cl
  fix: https://docs.python.org/3/library/http.client.html#http.client.HTTPSConnection
  rule:
    any:
    - pattern: httplib.HTTPSConnection($$$ARGS)
    - pattern: http.client.HTTPSConnection($$$ARGS)
    - pattern: six.moves.http_client.HTTPSConnection($$$ARGS)
- id: sg-python-use-ftp-tls
  pillar: SEC
  severity: LOW
  language: python
  problem: The 'FTP' class sends information unencrypted. Consider using the 'FTP_TLS'
    class instead.
  fix: https://docs.python.org/3/library/ftplib.html#ftplib.FTP_TLS
  rule:
    all:
    - pattern: ftplib.FTP($$$ARGS)
    - not:
        pattern: ftplib.FTP_TLS($$$ARGS)
- id: sg-python-no-set-ciphers
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: The 'ssl' module disables insecure cipher suites by default. Therefore,
    use of 'set_ciphers()' should only be used when you have very specialized requirements.
    Otherwise, you risk lowering the security of the SSL channel.
  fix: https://docs.python.org/3/library/ssl.html#cipher-selection
  rule:
    pattern: $CONTEXT.set_ciphers($$$ARGS)
- id: sg-python-listen-eval
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Because portions of the logging configuration are passed through eval(),
    use of this function may open its users to a security risk. While the function
    only binds to a socket on localhost, and so does not accept connections from remote
    machines, there are scenarios where untruste
  fix: https://docs.python.org/3/library/logging.config.html?highlight=security#logging.config.listen
  rule:
    pattern: logging.config.listen($$$ARGS)
- id: sg-python-mako-templates-detected
  pillar: SEC
  severity: LOW
  language: python
  problem: Mako templates do not provide a global HTML escaping mechanism. This means
    you must escape all sensitive data in your templates using '| u' for URL escaping
    or '| h' for HTML escaping. If you are using Mako to serve web content, consider
    using a system such as Jinja2 which enable
  fix: https://docs.makotemplates.org/en/latest/syntax.html#expression-escaping
  rule:
    pattern: mako.template.Template($$$ARGS)
- id: sg-python-marshal-usage
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: 'The marshal module is not intended to be secure against erroneous or maliciously
    constructed data. Never unmarshal data received from an untrusted or unauthenticated
    source. See more details: https://docs.python.org/3/library/marshal.html?highlight=security'
  fix: https://docs.python.org/3/library/marshal.html?highlight=security
  rule:
    any:
    - pattern: marshal.dump($$$ARGS)
    - pattern: marshal.dumps($$$ARGS)
    - pattern: marshal.load($$$ARGS)
    - pattern: marshal.loads($$$ARGS)
- id: sg-python-http-not-https-connection
  pillar: SEC
  severity: HIGH
  language: python
  problem: Detected HTTPConnectionPool. This will transmit data in cleartext. It is
    recommended to use HTTPSConnectionPool instead for to encrypt communications.
  fix: https://urllib3.readthedocs.io/en/1.2.1/pools.html#urllib3.connectionpool.HTTPSConnectionPool
  rule:
    any:
    - pattern: urllib3.HTTPConnectionPool($$$ARGS)
    - pattern: urllib3.connectionpool.HTTPConnectionPool($$$ARGS)
- id: sg-python-sha224-hash
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: This code uses a 224-bit hash function, which is deprecated or disallowed
    in some security policies. Consider updating to a stronger hash function such
    as SHA-384 or higher to ensure compliance and security.
  fix: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar3.ipd.pdf
  rule:
    any:
    - pattern: hashlib.sha224($$$ARGS)
    - pattern: hashlib.sha3_224($$$ARGS)
- id: sg-python-ssl-wrap-socket-is-deprecated
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: '''ssl.wrap_socket()'' is deprecated. This function creates an insecure
    socket without server name indication or hostname matching. Instead, create an
    SSL context using ''ssl.SSLContext()'' and use that to wrap a socket.'
  fix: https://docs.python.org/3/library/ssl.html#ssl.wrap_socket
  rule:
    pattern: ssl.wrap_socket($$$ARGS)
- id: sg-python-telnetlib
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Telnet does not encrypt communications. Use SSH instead.
  fix: https://docs.python.org/3/library/telnetlib.html
  rule:
    pattern: telnetlib.$ANYTHING($$$ARGS)
- id: sg-python-weak-ssl-version
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: An insecure SSL version was detected. TLS versions 1.0, 1.1, and all SSL
    versions are considered weak encryption and are deprecated. Use 'ssl.PROTOCOL_TLSv1_2'
    or higher.
  fix: https://tools.ietf.org/html/rfc7568
  rule:
    any:
    - pattern: ssl.PROTOCOL_SSLv2
    - pattern: ssl.PROTOCOL_SSLv3
    - pattern: ssl.PROTOCOL_TLSv1
    - pattern: ssl.PROTOCOL_TLSv1_1
    - pattern: pyOpenSSL.SSL.SSLv2_METHOD
    - pattern: pyOpenSSL.SSL.SSLv23_METHOD
    - pattern: pyOpenSSL.SSL.SSLv3_METHOD
    - pattern: pyOpenSSL.SSL.TLSv1_METHOD
    - pattern: pyOpenSSL.SSL.TLSv1_1_METHOD
- id: sg-python-avoid-unsafe-ruamel
  pillar: SEC
  severity: HIGH
  language: python
  problem: Avoid using unsafe `ruamel.yaml.YAML()`. `ruamel.yaml.YAML` can create
    arbitrary Python objects. A malicious actor could exploit this to run arbitrary
    code. Use `YAML(typ='rt')` or `YAML(typ='safe')` instead.
  fix: https://yaml.readthedocs.io/en/latest/basicuse.html?highlight=typ
  rule:
    any:
    - pattern: ruamel.yaml.YAML($$$LEAD, typ='unsafe', $$$ARGS)
    - pattern: ruamel.yaml.YAML($$$LEAD, typ='base', $$$ARGS)
- id: sg-python-avoid-shelve
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Avoid using `shelve`, which uses `pickle`, which is known to lead to code
    execution vulnerabilities. When unpickling, the serialized data could be manipulated
    to run arbitrary code. Instead, consider serializing the relevant data as JSON
    or a similar text-based serialization form
  fix: https://docs.python.org/3/library/pickle.html
  rule:
    pattern: shelve.$FUNC($$$ARGS)
- id: sg-python-insecure-hash-algorithm-md5
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Detected MD5 hash algorithm which is considered insecure. MD5 is not collision
    resistant and is therefore not suitable as a cryptographic signature. Use SHA256
    or SHA3 instead.
  fix: https://www.schneier.com/blog/archives/2012/10/when_will_we_se.html
  rule:
    all:
    - pattern: hashlib.md5($$$ARGS)
    - not:
        pattern: hashlib.md5($$$LEAD, usedforsecurity=False, $$$ARGS)
- id: sg-python-insecure-hash-algorithm-sha1
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Detected SHA1 hash algorithm which is considered insecure. SHA1 is not
    collision resistant and is therefore not suitable as a cryptographic signature.
    Use SHA256 or SHA3 instead.
  fix: https://www.schneier.com/blog/archives/2012/10/when_will_we_se.html
  rule:
    pattern: hashlib.sha1($$$ARGS)
- id: sg-python-insecure-hash-function
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Detected use of an insecure MD4 or MD5 hash function. These functions have
    known vulnerabilities and are considered deprecated. Consider using 'SHA256' or
    a similar function instead.
  fix: https://tools.ietf.org/html/rfc6151
  rule:
    all:
    - any:
      - pattern: hashlib.new("=~/[M|m][D|d][4|5]/", $$$ARGS)
      - pattern: hashlib.new($$$LEAD, name="=~/[M|m][D|d][4|5]/", $$$ARGS)
    - not:
        pattern: hashlib.new($$$LEAD, usedforsecurity=False, $$$ARGS)
- id: sg-python-insecure-uuid-version
  pillar: SEC
  severity: MEDIUM
  language: python
  problem: Using UUID version 1 for UUID generation can lead to predictable UUIDs
    based on system information (e.g., MAC address, timestamp). This may lead to security
    risks such as the sandwich attack. Consider using `uuid.uuid4()` instead for better
    randomness and security.
  fix: https://www.landh.tech/blog/20230811-sandwich-attack/
  rule:
    pattern: uuid.uuid1($$$ARGS)
- id: sg-python-unverified-ssl-context
  pillar: SEC
  severity: HIGH
  language: python
  problem: Unverified SSL context detected. This will permit insecure connections
    without verifying SSL certificates. Use 'ssl.create_default_context' instead.
  fix: https://docs.python.org/3/library/ssl.html#ssl-security
  rule:
    any:
    - pattern: ssl._create_unverified_context($$$ARGS)
    - pattern: ssl._create_default_https_context = ssl._create_unverified_context
- id: sg-python-use-defused-xml
  pillar: SEC
  severity: HIGH
  language: python
  problem: The Python documentation recommends using `defusedxml` instead of `xml`
    because the native Python `xml` library is vulnerable to XML External Entity (XXE)
    attacks. These attacks can leak confidential data and "XML bombs" can cause denial
    of service.
  fix: https://docs.python.org/3/library/xml.html
  rule:
    pattern: import xml
- id: sg-python-use-defused-xmlrpc
  pillar: SEC
  severity: HIGH
  language: python
  problem: Detected use of xmlrpc. xmlrpc is not inherently safe from vulnerabilities.
    Use defusedxml.xmlrpc instead.
  fix: https://pypi.org/project/defusedxml/
  rule:
    any:
    - pattern: import xmlrpclib
    - pattern: import SimpleXMLRPCServer
    - pattern: import xmlrpc
- id: sg-python-use-defusedcsv
  pillar: SEC
  severity: LOW
  language: python
  problem: 'Detected the generation of a CSV file using the built-in `csv` module.
    If user data is used to generate the data in this file, it is possible that an
    attacker could inject a formula when the CSV is imported into a spreadsheet application
    that runs an attacker script, which could '
  fix: https://github.com/raphaelm/defusedcsv
  rule:
    all:
    - pattern: csv.writer($$$ARGS)
    - not:
        pattern: defusedcsv.writer($$$ARGS)
---

# Well-Architected Policy Pack: PYTHON — SEC

Contains **33** verified `ast-grep` structural policies for `python` mapped to the **SEC** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-sec-eval` | `CRITICAL` | Dynamic code execution via `eval()` enables arbitrary code injection. | Use `ast.literal_eval()` or explicit parsers. |
| `wa-py-sec-exec` | `CRITICAL` | Dynamic code execution via `exec()` enables arbitrary code execution. | Remove `exec()` and use structured dispatch tables. |
| `wa-py-sec-os-system` | `CRITICAL` | `os.system()` invokes a subshell vulnerable to command injection. | Use `subprocess.run([cmd, arg], shell=False, check=True)`. |
| `wa-py-sec-os-popen` | `HIGH` | `os.popen()` invokes a shell command stream vulnerable to injection. | Use `subprocess.run(..., shell=False, capture_output=True)`. |
| `wa-py-sec-pickle-loads` | `CRITICAL` | `pickle.loads()` executes arbitrary bytecode on untrusted payloads. | Use `json.loads()` or `msgpack` with strict schema validation. |
| `wa-py-sec-pickle-load` | `CRITICAL` | `pickle.load()` deserializes untrusted streams with arbitrary code execution. | Use `json.load()` or safe serialization formats. |
| `wa-py-sec-marshal-loads` | `HIGH` | `marshal.loads()` is not secure against erroneous or maliciously constructed data. | Use `json.loads()` instead of `marshal`. |
| `wa-py-sec-shelve-open` | `HIGH` | `shelve` is backed by `pickle` and can execute arbitrary code when loading. | Use `sqlite3` or JSON storage instead. |
| `wa-py-sec-md5` | `MEDIUM` | MD5 is cryptographically broken and unsuitable for security digests. | Use `hashlib.sha256()` or `hashlib.blake2b()`. |
| `wa-py-sec-sha1` | `MEDIUM` | SHA-1 is vulnerable to collision attacks. | Use `hashlib.sha256()` or stronger. |
| `wa-py-sec-mktemp` | `HIGH` | `tempfile.mktemp()` has an inherent TOCTOU symlink race condition. | Use `tempfile.NamedTemporaryFile()` or `tempfile.mkstemp()`. |
| `wa-py-sec-ssl-unverified` | `CRITICAL` | Disabling SSL certificate verification exposes connections to MITM attacks. | Use `ssl.create_default_context()`. |
| `sg-python-httpsconnection-detected` | `MEDIUM` | The HTTPSConnection API has changed frequently with minor releases of Python. Ensure you are using the API for your version of Python securely. For example, Python 3 versions prior to 3.4.3 will not verify SSL certificates by default. See https://docs.python.org/3/library/http.cl | https://docs.python.org/3/library/http.client.html#http.client.HTTPSConnection |
| `sg-python-use-ftp-tls` | `LOW` | The 'FTP' class sends information unencrypted. Consider using the 'FTP_TLS' class instead. | https://docs.python.org/3/library/ftplib.html#ftplib.FTP_TLS |
| `sg-python-no-set-ciphers` | `MEDIUM` | The 'ssl' module disables insecure cipher suites by default. Therefore, use of 'set_ciphers()' should only be used when you have very specialized requirements. Otherwise, you risk lowering the security of the SSL channel. | https://docs.python.org/3/library/ssl.html#cipher-selection |
| `sg-python-listen-eval` | `MEDIUM` | Because portions of the logging configuration are passed through eval(), use of this function may open its users to a security risk. While the function only binds to a socket on localhost, and so does not accept connections from remote machines, there are scenarios where untruste | https://docs.python.org/3/library/logging.config.html?highlight=security#logging.config.listen |
| `sg-python-mako-templates-detected` | `LOW` | Mako templates do not provide a global HTML escaping mechanism. This means you must escape all sensitive data in your templates using '| u' for URL escaping or '| h' for HTML escaping. If you are using Mako to serve web content, consider using a system such as Jinja2 which enable | https://docs.makotemplates.org/en/latest/syntax.html#expression-escaping |
| `sg-python-marshal-usage` | `MEDIUM` | The marshal module is not intended to be secure against erroneous or maliciously constructed data. Never unmarshal data received from an untrusted or unauthenticated source. See more details: https://docs.python.org/3/library/marshal.html?highlight=security | https://docs.python.org/3/library/marshal.html?highlight=security |
| `sg-python-http-not-https-connection` | `HIGH` | Detected HTTPConnectionPool. This will transmit data in cleartext. It is recommended to use HTTPSConnectionPool instead for to encrypt communications. | https://urllib3.readthedocs.io/en/1.2.1/pools.html#urllib3.connectionpool.HTTPSConnectionPool |
| `sg-python-sha224-hash` | `MEDIUM` | This code uses a 224-bit hash function, which is deprecated or disallowed in some security policies. Consider updating to a stronger hash function such as SHA-384 or higher to ensure compliance and security. | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-131Ar3.ipd.pdf |
| `sg-python-ssl-wrap-socket-is-deprecated` | `MEDIUM` | 'ssl.wrap_socket()' is deprecated. This function creates an insecure socket without server name indication or hostname matching. Instead, create an SSL context using 'ssl.SSLContext()' and use that to wrap a socket. | https://docs.python.org/3/library/ssl.html#ssl.wrap_socket |
| `sg-python-telnetlib` | `MEDIUM` | Telnet does not encrypt communications. Use SSH instead. | https://docs.python.org/3/library/telnetlib.html |
| `sg-python-weak-ssl-version` | `MEDIUM` | An insecure SSL version was detected. TLS versions 1.0, 1.1, and all SSL versions are considered weak encryption and are deprecated. Use 'ssl.PROTOCOL_TLSv1_2' or higher. | https://tools.ietf.org/html/rfc7568 |
| `sg-python-avoid-unsafe-ruamel` | `HIGH` | Avoid using unsafe `ruamel.yaml.YAML()`. `ruamel.yaml.YAML` can create arbitrary Python objects. A malicious actor could exploit this to run arbitrary code. Use `YAML(typ='rt')` or `YAML(typ='safe')` instead. | https://yaml.readthedocs.io/en/latest/basicuse.html?highlight=typ |
| `sg-python-avoid-shelve` | `MEDIUM` | Avoid using `shelve`, which uses `pickle`, which is known to lead to code execution vulnerabilities. When unpickling, the serialized data could be manipulated to run arbitrary code. Instead, consider serializing the relevant data as JSON or a similar text-based serialization form | https://docs.python.org/3/library/pickle.html |
| `sg-python-insecure-hash-algorithm-md5` | `MEDIUM` | Detected MD5 hash algorithm which is considered insecure. MD5 is not collision resistant and is therefore not suitable as a cryptographic signature. Use SHA256 or SHA3 instead. | https://www.schneier.com/blog/archives/2012/10/when_will_we_se.html |
| `sg-python-insecure-hash-algorithm-sha1` | `MEDIUM` | Detected SHA1 hash algorithm which is considered insecure. SHA1 is not collision resistant and is therefore not suitable as a cryptographic signature. Use SHA256 or SHA3 instead. | https://www.schneier.com/blog/archives/2012/10/when_will_we_se.html |
| `sg-python-insecure-hash-function` | `MEDIUM` | Detected use of an insecure MD4 or MD5 hash function. These functions have known vulnerabilities and are considered deprecated. Consider using 'SHA256' or a similar function instead. | https://tools.ietf.org/html/rfc6151 |
| `sg-python-insecure-uuid-version` | `MEDIUM` | Using UUID version 1 for UUID generation can lead to predictable UUIDs based on system information (e.g., MAC address, timestamp). This may lead to security risks such as the sandwich attack. Consider using `uuid.uuid4()` instead for better randomness and security. | https://www.landh.tech/blog/20230811-sandwich-attack/ |
| `sg-python-unverified-ssl-context` | `HIGH` | Unverified SSL context detected. This will permit insecure connections without verifying SSL certificates. Use 'ssl.create_default_context' instead. | https://docs.python.org/3/library/ssl.html#ssl-security |
| `sg-python-use-defused-xml` | `HIGH` | The Python documentation recommends using `defusedxml` instead of `xml` because the native Python `xml` library is vulnerable to XML External Entity (XXE) attacks. These attacks can leak confidential data and "XML bombs" can cause denial of service. | https://docs.python.org/3/library/xml.html |
| `sg-python-use-defused-xmlrpc` | `HIGH` | Detected use of xmlrpc. xmlrpc is not inherently safe from vulnerabilities. Use defusedxml.xmlrpc instead. | https://pypi.org/project/defusedxml/ |
| `sg-python-use-defusedcsv` | `LOW` | Detected the generation of a CSV file using the built-in `csv` module. If user data is used to generate the data in this file, it is possible that an attacker could inject a formula when the CSV is imported into a spreadsheet application that runs an attacker script, which could  | https://github.com/raphaelm/defusedcsv |
