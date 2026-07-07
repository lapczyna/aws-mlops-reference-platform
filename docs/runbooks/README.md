# Runbooks

Operational playbooks for the alarms defined in `template.yaml`
([ADR-0015](../adr/0015-cloudwatch-alarms-and-dashboard.md)) and other
scenarios an on-call engineer is likely to hit.

## Before you start: orientation

- **Correlation ID:** every job has one `job_id` (a ULID) that appears as
  the DynamoDB partition key, the Step Functions execution name, the
  SageMaker Transform job name, and a structured-log field on every Lambda
  invocation involved. Start every investigation by finding the `job_id`.
- **Dashboard:** `batch-inference-<environment>` in the CloudWatch console
  (URL in the stack's `DashboardUrl` output) -- API traffic/errors/latency,
  Lambda invocations/errors/duration, Step Functions executions, DynamoDB
  capacity/throttles, and the business-level `JobCompleted`/`JobFailed`
  metrics.
- **Logs:** structured JSON in `/aws/lambda/batch-inference-<env>-fn-*` per
  function, `/aws/vendedlogs/states/batch-inference-<env>-sm-job-orchestration`
  for the state machine, `/aws/sagemaker/TransformJobs` for Batch Transform
  container output, `/aws/apigateway/batch-inference-<env>-api-access` for
  API access logs.
- **Alarms notify** the `batch-inference-<env>-alarms` SNS topic. If no
  email was configured (`AlarmNotificationEmail` parameter), subscribe your
  team's paging tool to that topic ARN (stack output
  `AlarmNotificationTopicArn`).

## Playbooks

| Symptom                                | Runbook                                              |
| ------------------------------------------ | --------------------------------------------------------- |
| A specific job never leaves `PROCESSING`     | [job-stuck-in-processing.md](job-stuck-in-processing.md) |
| `batch-inference-<env>-job-failure-rate` alarm fires | [high-failure-rate.md](high-failure-rate.md) |
| `batch-inference-<env>-api-5xx` alarm fires    | [api-5xx-errors.md](api-5xx-errors.md) |
| A deploy needs to be undone                      | [deployment-rollback.md](deployment-rollback.md) |

See also the [disaster recovery guide](../guides/disaster-recovery.md) for
scenarios beyond a single bad deploy or a single stuck job (region-level
failure, data loss, full stack loss).
