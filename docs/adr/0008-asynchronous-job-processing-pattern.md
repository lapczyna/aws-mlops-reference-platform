# ADR-0008: Asynchronous Submit-and-Poll Job Processing

## Status

Accepted

## Context

API Gateway (both REST and HTTP API) enforces a hard **29-second maximum
integration timeout** that cannot be raised. Batch inference over an
arbitrarily sized dataset, running on SageMaker Batch Transform, can easily
take longer than that -- from tens of seconds to many minutes depending on
dataset size and instance type. A synchronous "submit job and wait for the
response to contain predictions" API is therefore not just suboptimal, it is
structurally impossible to build correctly on this stack.

## Decision

We will implement **asynchronous, submit-and-poll job processing**:

1. `POST /jobs` starts the Step Functions execution and returns
   **`202 Accepted`** immediately with a `job_id` and `status: SUBMITTED`.
   It does not wait for the job to finish.
2. Clients poll `GET /jobs/{job_id}` until `status` is `COMPLETED` or
   `FAILED`.
3. Clients call `GET /jobs/{job_id}/results` only after observing
   `COMPLETED`, receiving a presigned S3 URL to download predictions.

Recommended client polling behavior (exponential backoff starting at ~2
seconds, capped at ~30 seconds) is documented in the
[deployment strategy guide](../guides/deployment-strategy.md).

## Consequences

- **No API Gateway timeout risk regardless of dataset size or model
  runtime** -- the API layer's job is only ever to start or read state, never
  to wait on compute.
- **Clients must implement polling**, which is a real integration cost
  compared to a synchronous call. This is called out explicitly in API
  documentation and is the accepted trade-off for correctness at any job
  size.
- **This pattern opens a natural extension point**: a future phase could
  add an optional webhook/EventBridge notification on job completion so
  well-behaved clients don't need to poll at all (see the
  [roadmap](../roadmap.md)), without changing the core submit/poll contract.
- The `job_id` returned at submission time is the single correlation key
  used across API responses, Step Functions execution names, and CloudWatch
  log fields, so a client (or an operator) can trace one job across every
  system component from a single value.
