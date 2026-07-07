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
| [0009](0009-sagemaker-model-artifact-parameterization.md) | SageMaker Model and container image as deploy-time parameters | Accepted |
| [0010](0010-optional-customer-managed-kms-key.md) | Customer-managed KMS key as an opt-in parameter        | Accepted |
| [0011](0011-explicit-per-function-iam-roles.md) | Explicit per-function IAM roles instead of SAM auto-generated roles | Accepted |
| [0012](0012-api-gateway-account-settings-bootstrap.md) | API Gateway account settings as a separate bootstrap stack | Accepted |
| [0013](0013-idempotent-job-submission.md) | Idempotent job submission via conditional writes            | Accepted |
| [0014](0014-github-oidc-for-cicd.md) | GitHub OIDC for CI/CD, no long-lived AWS credentials              | Accepted |
| [0015](0015-cloudwatch-alarms-and-dashboard.md) | CloudWatch alarms strategy -- aggregate over per-resource      | Accepted |
| [0016](0016-prod-approval-gate-via-github-environments.md) | Production approval gate via GitHub Environments  | Accepted (partially blocked by plan) |

This is the final phase of the initial roadmap; further ADRs will be added
as the platform continues to evolve post-launch (e.g. alarm threshold
tuning against real traffic, a multi-region DR decision if pursued).
