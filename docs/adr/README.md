# Architecture Decision Records

This log records the significant architectural decisions made for the Batch
Inference Platform, why they were made, and what alternatives were rejected.
We follow the lightweight ADR format popularized by Michael Nygard (see
[ADR-0001](0001-record-architecture-decisions.md)).

New decisions are appended, never renumbered or rewritten in place. If a
decision is later reversed, a new ADR supersedes the old one and both remain
in the log for historical context.

| ID   | Title                                                              | Status   |
| ---- | -------------------------------------------------------------------- | -------- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions                        | Accepted |
| [0002](0002-serverless-first-architecture.md) | Serverless-first compute, no EC2/ECS/EKS/Aurora       | Accepted |
| [0003](0003-sagemaker-batch-transform-vs-processing.md) | SageMaker Batch Transform over Processing   | Accepted |
| [0004](0004-step-functions-for-orchestration.md) | Step Functions for job orchestration              | Accepted |
| [0005](0005-dynamodb-single-table-job-state.md) | DynamoDB single-table design for job state         | Accepted |
| [0006](0006-api-gateway-rest-api-choice.md) | API Gateway REST API over HTTP API                     | Accepted |
| [0007](0007-lambda-layers-shared-code.md) | Lambda Layer for shared application code                 | Accepted |
| [0008](0008-asynchronous-job-processing-pattern.md) | Asynchronous submit-and-poll job processing   | Accepted |

Further ADRs will be added in later phases as infrastructure, security, and
operational decisions are made (e.g. encryption key strategy, CI/CD
promotion strategy, alarm thresholds).
