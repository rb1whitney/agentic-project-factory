# AWS Serverless: Read the Signals

**Read when**: reviewing Lambda, SQS/SNS, EventBridge or Step Functions for reliability and cost. Orient with the `aws-cloud-architecture-audit` contract probes (function inventory); this page interprets results. All changes are propose-only.

## Signal -> Probe -> Decision
| Signal | Secondary probe | Decision (propose, then wait) |
| :--- | :--- | :--- |
| A function uses an old `Runtime` | Fetch the current list on the [Lambda runtimes page](https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html); do not answer from memory | Propose the runtime upgrade and a test plan. Report the deprecation date from the page. |
| `Timeout` close to observed duration | `aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration --dimensions Name=FunctionName,Value=<f> --statistics Maximum --period 3600 --start-time <t0> --end-time <t1>` | Raising memory also raises CPU. Propose a memory test before raising the timeout. |
| Async function has no failure destination | `aws lambda get-function-event-invoke-config --function-name <f>` | Propose an on-failure destination or DLQ. |
| SQS queue has no redrive policy | `aws sqs get-queue-attributes --queue-url <u> --attribute-names RedrivePolicy VisibilityTimeout` | Propose a dead-letter queue with a `maxReceiveCount`, set on the source queue. |
| Event source mapping is not `Enabled` or reports errors | `aws lambda list-event-source-mappings --function-name <f>` | Read `State` and `LastProcessingResult` before changing anything. |
| One function invokes another synchronously | `aws stepfunctions list-state-machines` | Propose a Step Functions workflow for retries and state instead of chained calls. |
| EventBridge rule has no target or a disabled state | `aws events list-rules`, `aws events list-targets-by-rule --rule <r>` | Report orphan rules; propose removal only after the owner confirms. |
| Latency-sensitive API with cold starts | `aws lambda list-provisioned-concurrency-configs --function-name <f>`; `get-function-concurrency` | Propose provisioned concurrency for that alias only, with the monthly cost stated. |

## Gotchas
- For an SQS event source, the dead-letter queue belongs on the source queue's redrive policy. A DLQ configured on the function does not catch failed SQS batches.
- Set the queue visibility timeout to at least the function timeout; AWS documents a larger multiple for event source mappings.
- Memory, CPU and network scale together in Lambda, so a higher memory setting can lower cost by shortening duration. Test both directions.
- Functions are stateless. Keep state in DynamoDB, S3 or ElastiCache, never in the local filesystem across invocations.
- Deployment tooling (SAM, CDK, Terraform) should be whatever the repo already uses. Check before suggesting a new one.
