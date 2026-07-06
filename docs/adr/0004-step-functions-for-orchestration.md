# ADR-0004: Step Functions for Job Orchestration

## Status

Accepted

## Context

Running a batch inference job requires multiple ordered steps with
different failure modes: validating the request, marking the job as
processing, launching a SageMaker Batch Transform job that may run for
minutes, and recording the final outcome. This orchestration needs to:

- Survive longer than a single Lambda invocation (max 15 minutes) without
  the caller having to build its own polling/retry logic.
- Distinguish transient failures (worth retrying) from terminal failures
  (worth failing fast and recording).
- Be visible and debuggable -- a reviewer or on-call engineer should be able
  to look at one execution and see exactly which step failed and why.

The alternative considered was a single Lambda function that calls
`create_transform_job` and then polls `describe_transform_job` in a loop.

## Decision

We will use **AWS Step Functions (Standard workflow)** as the orchestrator,
with:

- A `ValidateInput` Lambda task.
- A direct DynamoDB `PutItem`/`UpdateItem` service integration for state
  transitions that don't need custom logic.
- A `RunBatchTransformJob` state using the optimized `.sync` SageMaker
  integration.
- `Retry` blocks on transient/throttling errors and `Catch` blocks routing
  terminal failures to a `MarkFailed` path, guaranteeing every execution ends
  in a recorded terminal state.

Standard (not Express) workflows are chosen because job durations
(potentially minutes) exceed Express workflows' billing model sweet spot for
short-lived executions, and because Standard workflows provide full
execution history in the console -- valuable for both debugging and for a
reviewer inspecting the system's operational behavior.

## Consequences

- **No custom polling code.** Both the DynamoDB and SageMaker integrations
  are direct service integrations or `.sync` patterns; the only Lambda
  functions in the workflow are `ValidateInput` and the terminal-state
  handlers, which contain genuine business logic.
- **Built-in observability.** Every execution has a visual, replayable
  history in the Step Functions console and emits events to CloudWatch
  and (optionally) EventBridge without extra code.
- **Cost is per-state-transition**, not per-second of idle waiting, which
  fits the near-zero-idle-cost constraint.
- **Trade-off accepted:** Standard workflows have a minimum billing
  granularity of $0.025 per 1,000 state transitions -- negligible at this
  platform's expected volume, but a deliberate choice over Express
  workflows' cheaper-at-high-volume, execution-history-limited model.
