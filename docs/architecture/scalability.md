# Scalability and Performance

## The one bottleneck that matters: SageMaker Batch Transform

Every other component in this architecture scales horizontally, automatically,
and independently per request. SageMaker Batch Transform is the exception,
in two ways worth distinguishing:

- **Across jobs, it scales fine.** Each job's Batch Transform run is an
  independent SageMaker job; the account can run many concurrently (bounded
  by the account's SageMaker resource quotas, which are raisable via a
  service quota increase request, not a template change).
- **Within a single job, its latency has a floor.** Instance startup +
  model load + inference + teardown takes a roughly fixed amount of time
  regardless of how small the dataset is -- this is *why* the
  [cost guide](../guides/cost-guide.md) shows SageMaker dominating cost at
  every volume tier, and it's also the dominant contributor to per-job
  *latency*. `TransformInstanceCount` only helps once a single dataset is
  large enough to benefit from parallel instances; it does nothing for the
  fixed per-job startup cost.

Everything else in this document is secondary to that fact.

## Per-component scaling behavior

| Component            | Scales via                                 | Practical ceiling at reference scale                          |
| ----------------------- | ---------------------------------------------- | ------------------------------------------------------------------- |
| API Gateway               | Fully managed; no configuration scales it        | Stage throttling (`ThrottlingBurstLimit`/`ThrottlingRateLimit` in `template.yaml`, currently 20/10) is a deliberately conservative default for a reference deployment -- raise it (or add a usage-plan-based per-client limit) before fronting real production traffic. |
| Lambda                     | Automatic, per-invocation; account concurrency limit (default 1,000 concurrent executions, raisable via quota increase) | Cold starts are the main latency lever, not throughput -- see below. No function currently uses reserved or provisioned concurrency. |
| DynamoDB (on-demand)         | Automatic; scales to several thousand RPS per table with no configuration | On-demand tables briefly throttle while scaling up to a sudden large spike (rare, and `DynamoDbThrottleAlarm` catches it); provisioned capacity with auto-scaling would trade that away for a capacity floor cost this platform's variable-and-mostly-idle traffic pattern doesn't want. See [ADR-0005](../adr/0005-dynamodb-single-table-job-state.md). |
| Step Functions (Standard)     | Automatic; ~1.25M open executions per account by default | Nowhere near a real constraint at any volume this platform's cost model (see the cost guide) is realistic for. |
| SageMaker Batch Transform         | `TransformInstanceCount` (per job), account concurrent-job quota (across jobs) | See "the one bottleneck," above. |
| S3                                   | Automatic; effectively unbounded request rate with standard key-naming | The `uploads/{job_id}/...` and `predictions/{job_id}/...` key prefixes already avoid the old S3 "sequential key" throttling pattern (irrelevant on current S3 infrastructure regardless, but good hygiene). |

## Cold starts

Every Lambda function here is a thin handler with a small dependency
footprint (the shared layer, not bundled per-function -- see
[ADR-0007](../adr/0007-lambda-layers-shared-code.md)), built for `arm64`
(Graviton), which both lowers cost and typically improves cold-start time
over `x86_64` for Python. None currently use provisioned concurrency; for
this platform's actual traffic pattern (asynchronous submission, client
polling with backoff per
[deployment-strategy.md](../guides/deployment-strategy.md)) an occasional
cold start adding a few hundred milliseconds to one poll is not
user-visible in the way it would be for a synchronous, latency-sensitive
API. If a future use case needs consistently low p99 latency on
`GetJobStatus` specifically, provisioned concurrency on that one function
is the targeted lever -- not a blanket policy across all six.

## Performance optimizations already applied

- **Graviton (`arm64`) for all Lambda functions** -- better price/performance
  for these I/O-bound handlers (network calls to DynamoDB/S3/Step
  Functions dominate their runtime, not CPU-bound work).
- **Module-level client construction** (composition root pattern, see the
  [developer guide](../guides/developer-guide.md)) -- boto3 clients and
  use case instances are built once per execution environment and reused
  across warm invocations, not reconstructed per request.
- **Fail fast at the edge.** API Gateway request validation rejects a
  malformed `POST /jobs` body before a Lambda cold start is even incurred
  (ADR-0006) -- the cheapest possible place to reject bad input.
- **Direct service integrations over Lambda glue** in the state machine
  (`MarkProcessing`'s DynamoDB `UpdateItem`, `RunBatchTransformJob`'s
  `.sync` SageMaker integration) -- fewer hops, no Lambda cold start in
  the orchestration's steady-state path at all except the two use-case
  handlers that have real logic to run (ADR-0004).

## Future scaling levers (not currently needed, but the next places to look)

- **API Gateway caching** or a read-through cache (DAX) in front of
  `GetJobStatus`, if client polling volume ever becomes the dominant cost
  driver instead of SageMaker -- not justified at any volume in the
  [cost guide](../guides/cost-guide.md)'s worked examples.
- **A `status`-based DynamoDB GSI** (already flagged in
  [ADR-0005](../adr/0005-dynamodb-single-table-job-state.md) and the
  [roadmap](../roadmap.md)) if an access pattern beyond "fetch by job id"
  emerges.
- **Provisioned concurrency** on individual functions if a specific one
  becomes latency-critical for a use case this reference architecture
  doesn't yet have.
- **Multi-region** for both DR and latency (serving users far from the
  deployed region) -- explicitly out of scope today; see the
  [disaster recovery guide](../guides/disaster-recovery.md) and roadmap.
