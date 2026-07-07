# Runbook: High Job Failure Rate

## Trigger

`batch-inference-<env>-job-failure-rate` alarm: the `BatchInferencePlatform`
namespace's `JobFailed` metric (emitted by `RecordJobOutcome`) hit 3 or
more in a 5-minute window.

This is a **business-level** signal, not an infrastructure one --
individual jobs are completing (Step Functions executions aren't erroring
out; `StepFunctionsFailedExecutionsAlarm` would fire for that), but they're
resolving to `FAILED`.

## Investigation

1. **Check the dashboard's business metrics widget** for `JobFailed` vs
   `JobCompleted` -- is this a spike, or has the failure rate been
   elevated for a while?

2. **Find the failure reasons.** Every `RecordJobOutcome` failure call logs
   `failure_reason` as EMF metadata and the use case emits a structured log
   line. Query CloudWatch Logs Insights across the RecordOutcome function's
   log group:
   ```
   fields @timestamp, job_id, error_code, error_cause
   | filter status = "FAILED"
   | sort @timestamp desc
   | limit 50
   ```
   (Log group: `/aws/lambda/batch-inference-<env>-fn-record-outcome`)

3. **Group by `error_code`** to find the dominant cause:

   - **`InvalidInput`** -- `ValidateInput` rejected the dataset (missing or
     empty). This is almost always a client-side integration issue, not a
     platform bug: confirm with whoever is calling `POST /jobs` that they
     are actually uploading to the presigned URL *before* submitting, and
     that the upload actually reached S3 (check
     `/aws/lambda/batch-inference-<env>-fn-validate-input` logs for the
     specific `input_s3_key` it looked for).
   - **`TransformError`** -- the SageMaker Batch Transform job itself
     failed. Check `/aws/sagemaker/TransformJobs` for the container's own
     error output. Common causes:
     - **Model artifact missing or stale** -- confirm
       `scripts/package_model.sh <env>` has been run against this
       environment; see [ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md).
     - **Malformed dataset rows** -- a row that doesn't parse as 4 numeric
       CSV columns will fail `ml/inference.py`'s `input_fn`; the container
       log will show the pandas/parsing exception.
     - **Instance capacity** -- rare for `ml.m5.large`, but check for a
       `ResourceLimitExceeded` message if `TransformInstanceCount` was
       increased significantly.

4. **If the cause is a genuine platform bug** (not a client integration
   issue), treat it as an incident: consider whether to pause new
   submissions (there's no kill switch for this today -- the fastest lever
   is disabling the `POST /jobs` API Gateway method or setting its
   throttle to 0) while the fix is deployed, then follow
   [deployment-rollback.md](deployment-rollback.md) if a recent deploy is
   implicated.
