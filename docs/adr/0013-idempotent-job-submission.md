# ADR-0013: Idempotent Job Submission via Conditional Writes

## Status

Accepted

## Context

`POST /jobs` and the Step Functions execution it starts are both
side-effecting: creating a DynamoDB record and starting an orchestration
run. Clients over HTTP retry on timeouts and connection resets as a matter
of course -- if `SubmitJob` succeeded server-side but the response was lost
in transit, a naive implementation would let a retried request create a
second job record and a second Step Functions execution for what the
client believes is one submission.

Because `job_id` is generated once (by `PresignUpload`) and reused by the
client for the matching `POST /jobs` call, it is already a natural
idempotency key -- the question is whether the rest of the system honors
that, or silently double-processes a retry.

## Decision

Every write in the submission path is a conditional, idempotent operation:

- **`JobRepository.create`** uses a DynamoDB `ConditionExpression:
  attribute_not_exists(job_id)`. A retried `create()` for the same job id
  raises `JobAlreadyExistsError`, which `SubmitBatchJob` catches and treats
  as success -- it fetches and returns the existing record instead of
  failing the request.
- **`JobOrchestrator.start_execution`** uses the job id as the Step
  Functions **execution name**. Step Functions itself rejects a second
  `StartExecution` call with the same name against the same input as
  `ExecutionAlreadyExists`, which `StepFunctionsJobOrchestrator` catches and
  treats as a no-op.
- **`JobRepository.save`** (used by `RecordJobOutcome`) uses a
  `ConditionExpression` that rejects overwriting a job already in a
  terminal state (`COMPLETED`/`FAILED`), guarding the other end of the same
  problem: a duplicate Step Functions retry of `RecordSuccess`/
  `RecordFailure` cannot flip an already-recorded outcome to something else.

## Consequences

- **`POST /jobs` is safe to retry** with the same `job_id` at any point --
  before, during, or after the first attempt's side effects landed -- and
  always returns the job's actual current state rather than an error or a
  duplicate.
- **No distributed lock or idempotency-token table is needed.** The
  idempotency key is the job id itself, and the guarantee is enforced by
  each downstream service's own native conditional-write primitive
  (DynamoDB condition expressions, Step Functions execution naming) rather
  than a bespoke mechanism this platform would have to maintain.
- **Trade-off accepted:** if a client submits a *different* `input_s3_key`
  under a `job_id` that already exists, the second submission's dataset
  reference is silently ignored in favor of the first -- this is the
  correct behavior for retry-safety, but it does mean `job_id` reuse across
  genuinely different datasets is not supported (and shouldn't be; a new
  job should always start from a new `PresignUpload` call, which mints a
  fresh `job_id`).
- Every domain and infrastructure test in `tests/unit/` and
  `tests/integration/` that exercises `create`/`save` asserts this
  behavior directly -- see
  `tests/unit/application/use_cases/test_submit_batch_job.py` and
  `tests/integration/infrastructure/persistence/test_dynamodb_job_repository.py`.
