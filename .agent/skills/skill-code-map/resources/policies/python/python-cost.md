---
pack_id: wa-pack-python-cost
language: python
pillar: COST
rule_count: 5
rules:
- id: wa-py-cost-boto3-client-in-loop
  pillar: COST
  severity: HIGH
  language: python
  problem: Instantiating `boto3.client()` inside a loop re-parses botocore service
    JSON and resets HTTP connection pools.
  fix: Create the `boto3.client` once at module/class init and reuse it.
  rule:
    pattern: boto3.client($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-cost-boto3-resource-in-loop
  pillar: COST
  severity: HIGH
  language: python
  problem: Instantiating `boto3.resource()` inside a loop disables connection pooling
    and increases AWS API latency/cost.
  fix: Reuse a shared `boto3.resource` instance.
  rule:
    pattern: boto3.resource($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-cost-httpx-client-in-loop
  pillar: COST
  severity: MEDIUM
  language: python
  problem: Creating `httpx.Client()` inside a loop forces a new TCP+TLS handshake
    per iteration.
  fix: Hoist `with httpx.Client() as client:` outside the loop.
  rule:
    pattern: httpx.Client($$$ARGS)
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-cost-requests-session-in-loop
  pillar: COST
  severity: MEDIUM
  language: python
  problem: Creating `requests.Session()` inside a loop defeats HTTP keep-alive connection
    pooling.
  fix: Instantiate `requests.Session()` once outside the loop.
  rule:
    pattern: requests.Session()
    inside:
      any:
      - kind: for_statement
      - kind: while_statement
      stopBy: end
- id: wa-py-cost-dynamodb-scan
  pillar: COST
  severity: HIGH
  language: python
  problem: DynamoDB `.scan()` reads every item in the table, consuming massive RCU
    quota.
  fix: Use `.query()` with a partition key or GSI.
  rule:
    pattern: $TABLE.scan($$$ARGS)
---

# Well-Architected Policy Pack: PYTHON — COST

Contains **5** verified `ast-grep` structural policies for `python` mapped to the **COST** pillar.

| Rule ID | Severity | Problem | Remediation |
| :--- | :--- | :--- | :--- |
| `wa-py-cost-boto3-client-in-loop` | `HIGH` | Instantiating `boto3.client()` inside a loop re-parses botocore service JSON and resets HTTP connection pools. | Create the `boto3.client` once at module/class init and reuse it. |
| `wa-py-cost-boto3-resource-in-loop` | `HIGH` | Instantiating `boto3.resource()` inside a loop disables connection pooling and increases AWS API latency/cost. | Reuse a shared `boto3.resource` instance. |
| `wa-py-cost-httpx-client-in-loop` | `MEDIUM` | Creating `httpx.Client()` inside a loop forces a new TCP+TLS handshake per iteration. | Hoist `with httpx.Client() as client:` outside the loop. |
| `wa-py-cost-requests-session-in-loop` | `MEDIUM` | Creating `requests.Session()` inside a loop defeats HTTP keep-alive connection pooling. | Instantiate `requests.Session()` once outside the loop. |
| `wa-py-cost-dynamodb-scan` | `HIGH` | DynamoDB `.scan()` reads every item in the table, consuming massive RCU quota. | Use `.query()` with a partition key or GSI. |
