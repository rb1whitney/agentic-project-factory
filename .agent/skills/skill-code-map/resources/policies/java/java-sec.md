---
pack_id: wa-pack-java-sec
language: java
pillar: SEC
rule_count: 29
rules:
- id: wa-java-sec-runtime-exec
  pillar: SEC
  severity: CRITICAL
  language: java
  problem: '`Runtime.exec()` is prone to command injection and shell argument splitting
    bugs.'
  fix: Use `new ProcessBuilder(List.of(cmd, arg))` with explicit argument array.
  rule:
    pattern: Runtime.getRuntime().exec($$$ARGS)
- id: wa-java-sec-object-input-stream
  pillar: SEC
  severity: CRITICAL
  language: java
  problem: Java native deserialization via `ObjectInputStream` is vulnerable to remote
    code execution gadget chains.
  fix: Use Jackson/JSON or configure an `ObjectInputFilter` allowlist.
  rule:
    pattern: new ObjectInputStream($$$ARGS)
- id: wa-java-sec-xml-decoder
  pillar: SEC
  severity: CRITICAL
  language: java
  problem: '`XMLDecoder` executes arbitrary Java methods during XML deserialization.'
  fix: Use standard JAXB or Jackson XML with XXE disabled.
  rule:
    pattern: new XMLDecoder($$$ARGS)
- id: wa-java-sec-cipher-inst
  pillar: SEC
  severity: HIGH
  language: java
  problem: DES uses a 56-bit key and can be brute-forced in hours.
  fix: Use `AES/GCM/NoPadding`.
  rule:
    pattern: Cipher.getInstance("DES")
- id: wa-java-sec-cipher-ecb
  pillar: SEC
  severity: HIGH
  language: java
  problem: AES in ECB mode leaks plaintext block patterns and lacks authentication.
  fix: Use `AES/GCM/NoPadding` with a 12-byte IV.
  rule:
    pattern: Cipher.getInstance("AES/ECB/PKCS5Padding")
- id: wa-java-sec-md5
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: MD5 is cryptographically broken.
  fix: Use `MessageDigest.getInstance("SHA-256")`.
  rule:
    pattern: MessageDigest.getInstance("MD5")
- id: wa-java-sec-sha1
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: SHA-1 is vulnerable to collision attacks.
  fix: Use `MessageDigest.getInstance("SHA-256")`.
  rule:
    pattern: MessageDigest.getInstance("SHA-1")
- id: wa-java-sec-util-random
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: '`java.util.Random` uses a predictable linear congruential PRNG unsuitable
    for tokens or keys.'
  fix: Use `java.security.SecureRandom`.
  rule:
    pattern: new Random($$$ARGS)
- id: wa-java-sec-script-engine-eval
  pillar: SEC
  severity: CRITICAL
  language: java
  problem: '`ScriptEngine.eval()` executes dynamic script payloads and enables code
    injection.'
  fix: Avoid `ScriptEngine.eval()` on external input.
  rule:
    pattern: $ENGINE.eval($$$ARGS)
- id: wa-java-sec-stmt-execute-query
  pillar: SEC
  severity: HIGH
  language: java
  problem: Executing raw SQL on a `Statement` risks SQL injection if `$SQL` is concatenated.
  fix: Use `PreparedStatement` with `?` parameter binding.
  rule:
    pattern: $STMT.executeQuery($SQL)
- id: wa-java-sec-stmt-execute-update
  pillar: SEC
  severity: HIGH
  language: java
  problem: Executing raw SQL via `executeUpdate($SQL)` risks SQL injection.
  fix: Use `PreparedStatement` with bound parameters.
  rule:
    pattern: $STMT.executeUpdate($SQL)
- id: wa-java-sec-file-create-temp
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: '`File.createTempFile()` creates files with default world/group permissions
    on shared systems.'
  fix: Use `Files.createTempFile()` with restrictive `PosixFilePermissions`.
  rule:
    pattern: File.createTempFile($$$ARGS)
- id: sg-java-cbc-padding-oracle
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Using CBC with PKCS5Padding is susceptible to padding oracle attacks. A
    malicious actor could discern the difference between plaintext with valid or invalid
    padding. Further, CBC mode does not include any integrity checks. Use 'AES/GCM/NoPadding'
    instead.
  fix: '"AES/GCM/NoPadding"

    '
  rule:
    all:
    - inside:
        pattern: Cipher.getInstance("=~/.*\/CBC\/PKCS5Padding/")
        stopBy: end
    - pattern: '"=~/.*\/CBC\/PKCS5Padding/"'
- id: sg-java-des-is-deprecated
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: DES is considered deprecated. AES is the recommended cipher. Upgrade to
    use AES. See https://www.nist.gov/news-events/news/2005/06/nist-withdraws-outdated-data-encryption-standard
    for more information.
  fix: '"AES/GCM/NoPadding"

    '
  rule:
    all:
    - any:
      - inside:
          pattern: $CIPHER.getInstance("=~/DES/.*/")
          stopBy: end
      - inside:
          pattern: $CIPHER.getInstance("DES")
          stopBy: end
    - any:
      - pattern: '"=~/DES/.*/"'
      - pattern: '"DES"'
- id: sg-java-desede-is-deprecated
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Triple DES (3DES or DESede) is considered deprecated. AES is the recommended
    cipher. Upgrade to use AES.
  fix: https://csrc.nist.gov/News/2017/Update-to-Current-Use-and-Deprecation-of-TDEA
  rule:
    any:
    - pattern: $CIPHER.getInstance("=~/DESede.*/")
    - pattern: $CRYPTO.KeyGenerator.getInstance("DES")
- id: sg-java-gcm-detection
  pillar: SEC
  severity: LOW
  language: java
  problem: 'GCM detected, please check that IV/nonce is not reused, an Initialization
    Vector (IV) is a nonce used to randomize the encryption, so that even if multiple
    messages with identical plaintext are encrypted, the generated corresponding ciphertexts
    are different. Unlike the Key, the '
  fix: https://cwe.mitre.org/data/definitions/323.html
  rule:
    any:
    - pattern: $METHOD.getInstance("AES/GCM/NoPadding", $$$ARGS);
    - pattern: new GCMParameterSpec($$$ARGS);
- id: sg-java-no-null-cipher
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: 'NullCipher was detected. This will not encrypt anything; the cipher text
    will be the same as the plain text. Use a valid, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING").
    See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions for
    more information.'
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    any:
    - pattern: new NullCipher($$$ARGS);
    - pattern: new javax.crypto.NullCipher($$$ARGS);
- id: sg-java-rsa-no-padding
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Using RSA without OAEP mode weakens the encryption.
  fix: https://rdist.root.org/2009/10/06/why-rsa-encryption-padding-is-critical/
  rule:
    pattern: $CIPHER.getInstance("=~/RSA/[Nn][Oo][Nn][Ee]/NoPadding/")
- id: sg-java-defaulthttpclient-is-deprecated
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: DefaultHttpClient is deprecated. Further, it does not support connections
    using TLS1.2, which makes using DefaultHttpClient a security hazard. Use HttpClientBuilder
    instead.
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    pattern: new DefaultHttpClient($$$ARGS);
- id: sg-java-unencrypted-socket
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Detected use of a Java socket that is not encrypted. As a result, the traffic
    could be read by an attacker intercepting the network traffic. Use an SSLSocket
    created by 'SSLSocketFactory' or 'SSLServerSocketFactory' instead.
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    any:
    - pattern: new ServerSocket($$$ARGS)
    - pattern: new Socket($$$ARGS)
- id: sg-java-use-of-aes-ecb
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: 'Use of AES with ECB mode detected. ECB doesn''t provide message confidentiality
    and is not semantically secure so should not be used. Instead, use a strong, secure
    cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_'
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    pattern: $CIPHER.getInstance("=~/AES/ECB.*/")
- id: sg-java-use-of-blowfish
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: 'Use of Blowfish was detected. Blowfish uses a 64-bit block size that makes
    it vulnerable to birthday attacks, and is therefore considered non-compliant.
    Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING").
    See https://owasp.org/www-community/Using_the'
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    pattern: $CIPHER.getInstance("Blowfish")
- id: sg-java-use-of-rc2
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: 'Use of RC2 was detected. RC2 is vulnerable to related-key attacks, and
    is therefore considered non-compliant. Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING").
    See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions for
    more inf'
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    pattern: $CIPHER.getInstance("RC2")
- id: sg-java-use-of-rc4
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: 'Use of RC4 was detected. RC4 is vulnerable to several attacks, including
    stream cipher attacks and bit flipping attacks. Instead, use a strong, secure
    cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions
    f'
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    pattern: $CIPHER.getInstance("RC4")
- id: sg-java-weak-random
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Detected use of the functions `Math.random()` or `java.util.Random()`.
    These are both not cryptographically strong random number generators (RNGs). If
    you are using these RNGs to create passwords or secret tokens, use `java.security.SecureRandom`
    instead.
  fix: https://owasp.org/Top10/A02_2021-Cryptographic_Failures
  rule:
    any:
    - pattern: new java.util.Random($$$ARGS).$FUNC($$$ARGS)
    - pattern: java.lang.Math.random($$$ARGS)
- id: sg-java-object-deserialization
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: Found object deserialization using ObjectInputStream. Deserializing entire
    Java objects is dangerous because malicious actors can create Java object streams
    with unintended consequences. Ensure that the objects being deserialized are not
    user-controlled. If this must be done, con
  fix: https://www.owasp.org/index.php/Deserialization_of_untrusted_data
  rule:
    pattern: new ObjectInputStream($$$ARGS);
- id: sg-java-documentbuilderfactory-external-general-entities-true
  pillar: SEC
  severity: HIGH
  language: java
  problem: External entities are allowed for $DBFACTORY. This is vulnerable to XML
    external entity attacks. Disable this by setting the feature "http://xml.org/sax/features/external-general-entities"
    to false.
  fix: $DBFACTORY.setFeature("http://xml.org/sax/features/external-general-entities",
    false);
  rule:
    pattern: $DBFACTORY.setFeature("http://xml.org/sax/features/external-general-entities",
      true);
- id: sg-java-documentbuilderfactory-external-parameter-entities-true
  pillar: SEC
  severity: HIGH
  language: java
  problem: External entities are allowed for $DBFACTORY. This is vulnerable to XML
    external entity attacks. Disable this by setting the feature "http://xml.org/sax/features/external-parameter-entities"
    to false.
  fix: $DBFACTORY.setFeature("http://xml.org/sax/features/external-parameter-entities",
    false);
  rule:
    pattern: $DBFACTORY.setFeature("http://xml.org/sax/features/external-parameter-entities",
      true);
- id: sg-java-spring-csrf-disabled
  pillar: SEC
  severity: MEDIUM
  language: java
  problem: CSRF protection is disabled for this configuration. This is a security
    risk.
  fix: https://owasp.org/Top10/A01_2021-Broken_Access_Control
  rule:
    pattern: $OBJ.csrf($$$ARGS).disable($$$ARGS)
---

# Well-Architected Policy Pack: JAVA — SEC

Contains **29** verified `ast-grep` structural policies for `java` mapped to the **SEC** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-java-sec-runtime-exec` | `CRITICAL` | `Runtime.exec()` is prone to command injection and shell argument splitting bugs. | Use `new ProcessBuilder(List.of(cmd, arg))` with explicit argument array. |
| `wa-java-sec-object-input-stream` | `CRITICAL` | Java native deserialization via `ObjectInputStream` is vulnerable to remote code execution gadget chains. | Use Jackson/JSON or configure an `ObjectInputFilter` allowlist. |
| `wa-java-sec-xml-decoder` | `CRITICAL` | `XMLDecoder` executes arbitrary Java methods during XML deserialization. | Use standard JAXB or Jackson XML with XXE disabled. |
| `wa-java-sec-cipher-inst` | `HIGH` | DES uses a 56-bit key and can be brute-forced in hours. | Use `AES/GCM/NoPadding`. |
| `wa-java-sec-cipher-ecb` | `HIGH` | AES in ECB mode leaks plaintext block patterns and lacks authentication. | Use `AES/GCM/NoPadding` with a 12-byte IV. |
| `wa-java-sec-md5` | `MEDIUM` | MD5 is cryptographically broken. | Use `MessageDigest.getInstance("SHA-256")`. |
| `wa-java-sec-sha1` | `MEDIUM` | SHA-1 is vulnerable to collision attacks. | Use `MessageDigest.getInstance("SHA-256")`. |
| `wa-java-sec-util-random` | `MEDIUM` | `java.util.Random` uses a predictable linear congruential PRNG unsuitable for tokens or keys. | Use `java.security.SecureRandom`. |
| `wa-java-sec-script-engine-eval` | `CRITICAL` | `ScriptEngine.eval()` executes dynamic script payloads and enables code injection. | Avoid `ScriptEngine.eval()` on external input. |
| `wa-java-sec-stmt-execute-query` | `HIGH` | Executing raw SQL on a `Statement` risks SQL injection if `$SQL` is concatenated. | Use `PreparedStatement` with `?` parameter binding. |
| `wa-java-sec-stmt-execute-update` | `HIGH` | Executing raw SQL via `executeUpdate($SQL)` risks SQL injection. | Use `PreparedStatement` with bound parameters. |
| `wa-java-sec-file-create-temp` | `MEDIUM` | `File.createTempFile()` creates files with default world/group permissions on shared systems. | Use `Files.createTempFile()` with restrictive `PosixFilePermissions`. |
| `sg-java-cbc-padding-oracle` | `MEDIUM` | Using CBC with PKCS5Padding is susceptible to padding oracle attacks. A malicious actor could discern the difference between plaintext with valid or invalid padding. Further, CBC mode does not include any integrity checks. Use 'AES/GCM/NoPadding' instead. | "AES/GCM/NoPadding" |
| `sg-java-des-is-deprecated` | `MEDIUM` | DES is considered deprecated. AES is the recommended cipher. Upgrade to use AES. See https://www.nist.gov/news-events/news/2005/06/nist-withdraws-outdated-data-encryption-standard for more information. | "AES/GCM/NoPadding" |
| `sg-java-desede-is-deprecated` | `MEDIUM` | Triple DES (3DES or DESede) is considered deprecated. AES is the recommended cipher. Upgrade to use AES. | https://csrc.nist.gov/News/2017/Update-to-Current-Use-and-Deprecation-of-TDEA |
| `sg-java-gcm-detection` | `LOW` | GCM detected, please check that IV/nonce is not reused, an Initialization Vector (IV) is a nonce used to randomize the encryption, so that even if multiple messages with identical plaintext are encrypted, the generated corresponding ciphertexts are different. Unlike the Key, the | https://cwe.mitre.org/data/definitions/323.html |
| `sg-java-no-null-cipher` | `MEDIUM` | NullCipher was detected. This will not encrypt anything; the cipher text will be the same as the plain text. Use a valid, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions for more information. | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-rsa-no-padding` | `MEDIUM` | Using RSA without OAEP mode weakens the encryption. | https://rdist.root.org/2009/10/06/why-rsa-encryption-padding-is-critical/ |
| `sg-java-defaulthttpclient-is-deprecated` | `MEDIUM` | DefaultHttpClient is deprecated. Further, it does not support connections using TLS1.2, which makes using DefaultHttpClient a security hazard. Use HttpClientBuilder instead. | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-unencrypted-socket` | `MEDIUM` | Detected use of a Java socket that is not encrypted. As a result, the traffic could be read by an attacker intercepting the network traffic. Use an SSLSocket created by 'SSLSocketFactory' or 'SSLServerSocketFactory' instead. | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-use-of-aes-ecb` | `MEDIUM` | Use of AES with ECB mode detected. ECB doesn't provide message confidentiality and is not semantically secure so should not be used. Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_ | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-use-of-blowfish` | `MEDIUM` | Use of Blowfish was detected. Blowfish uses a 64-bit block size that makes it vulnerable to birthday attacks, and is therefore considered non-compliant. Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-use-of-rc2` | `MEDIUM` | Use of RC2 was detected. RC2 is vulnerable to related-key attacks, and is therefore considered non-compliant. Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions for more inf | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-use-of-rc4` | `MEDIUM` | Use of RC4 was detected. RC4 is vulnerable to several attacks, including stream cipher attacks and bit flipping attacks. Instead, use a strong, secure cipher: Cipher.getInstance("AES/CBC/PKCS7PADDING"). See https://owasp.org/www-community/Using_the_Java_Cryptographic_Extensions f | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-weak-random` | `MEDIUM` | Detected use of the functions `Math.random()` or `java.util.Random()`. These are both not cryptographically strong random number generators (RNGs). If you are using these RNGs to create passwords or secret tokens, use `java.security.SecureRandom` instead. | https://owasp.org/Top10/A02_2021-Cryptographic_Failures |
| `sg-java-object-deserialization` | `MEDIUM` | Found object deserialization using ObjectInputStream. Deserializing entire Java objects is dangerous because malicious actors can create Java object streams with unintended consequences. Ensure that the objects being deserialized are not user-controlled. If this must be done, con | https://www.owasp.org/index.php/Deserialization_of_untrusted_data |
| `sg-java-documentbuilderfactory-external-general-entities-true` | `HIGH` | External entities are allowed for $DBFACTORY. This is vulnerable to XML external entity attacks. Disable this by setting the feature "http://xml.org/sax/features/external-general-entities" to false. | $DBFACTORY.setFeature("http://xml.org/sax/features/external-general-entities", false); |
| `sg-java-documentbuilderfactory-external-parameter-entities-true` | `HIGH` | External entities are allowed for $DBFACTORY. This is vulnerable to XML external entity attacks. Disable this by setting the feature "http://xml.org/sax/features/external-parameter-entities" to false. | $DBFACTORY.setFeature("http://xml.org/sax/features/external-parameter-entities", false); |
| `sg-java-spring-csrf-disabled` | `MEDIUM` | CSRF protection is disabled for this configuration. This is a security risk. | https://owasp.org/Top10/A01_2021-Broken_Access_Control |
