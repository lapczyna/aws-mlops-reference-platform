# Runbook: Job Stuck in PROCESSING

## Symptom

A specific job's `status` (via `GET /jobs/{jobId}` or a direct DynamoDB
lookup) has been `PROCESSING` for far longer than a Batch Transform job on
a small dataset should reasonably take (minutes, not hours).

There is currently no dedicated alarm for this specific symptom -- every
*state machine* failure path is covered by `StepFunctionsFailedExecutionsAlarm`
and `JobFailureRateAlarm`, but a job that is stuck rather than failed
produces no alarm at all. This is a known gap; see
[roadmap](../roadmap.md) for a proposed "stale processing job" scheduled
check.

## Investigation

1. **Find the job record:**
   ```bash
   aws dynamodb get-item \
     --table-name batch-inference-<env>-table-jobs \
     --key '{"job_id": {"S": "<job_id>"}}'
   ```
   Note `updated_at` -- how long has it actually been in `PROCESSING`?

2. **Find the Step Functions execution** (it is named exactly after the
   job id):
   ```bash
   aws stepfunctions describe-execution \
     --execution-arn "arn:aws:states:<region>:<account>:execution:batch-inference-<env>-sm-job-orchestration:<job_id>"
   ```
   - `status: RUNNING` -- the execution itself is still going, almost
     certainly waiting on the `RunBatchTransformJob` state. Proceed to step 3.
   - `status: FAILED`/`TIMED_OUT`/`ABORTED` but DynamoDB still says
     `PROCESSING` -- this means `RecordFailure` never ran or its DynamoDB
     write didn't land. That's a genuine bug (every reachable ASL path is
     designed to route through `RecordSuccess`/`RecordFailure` before the
     execution ends) -- capture the execution's event history
     (`aws stepfunctions get-execution-history`) and treat as an incident,
     not routine operations. Manually correct the DynamoDB record afterward
     (step 4) so the client isn't stuck polling forever.

3. **Check the SageMaker Transform job directly:**
   ```bash
   aws sagemaker describe-transform-job --transform-job-name <job_id>
   ```
   - `InProgress` -- genuinely still running. Check `TransformStartTime`
     against the dataset size; if it's been running far longer than a
     dataset this size should take, check
     `/aws/sagemaker/TransformJobs` logs for the container's own errors
     (a job can be `InProgress` right up until it fails).
   - `Failed` -- the Step Functions execution should reach `RecordFailure`
     on its own shortly (Step Functions polls the transform job via the
     `.sync` integration); if DynamoDB still shows `PROCESSING` several
     minutes after `TransformEndTime`, that points back to the same bug
     scenario as step 2.

4. **Manual correction (only after confirming via steps 2-3 that the job
   genuinely cannot complete on its own):**
   ```bash
   aws dynamodb update-item \
     --table-name batch-inference-<env>-table-jobs \
     --key '{"job_id": {"S": "<job_id>"}}' \
     --update-expression 'SET #status = :failed, error_message = :msg, updated_at = :now' \
     --expression-attribute-names '{"#status": "status"}' \
     --expression-attribute-values '{":failed": {"S": "FAILED"}, ":msg": {"S": "Manually corrected -- see incident notes"}, ":now": {"S": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"}}'
   ```
   File a follow-up to fix the root cause -- this command is a customer-facing
   fix, not a resolution.
