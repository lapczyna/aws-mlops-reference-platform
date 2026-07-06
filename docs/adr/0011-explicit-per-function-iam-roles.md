# ADR-0011: Explicit Per-Function IAM Roles Instead of SAM Auto-Generated Roles

## Status

Accepted

## Context

`AWS::Serverless::Function` can auto-generate an execution role from a
`Policies` property, using either AWS managed policy templates (like
`DynamoDBCrudPolicy`) or inline statements. This is convenient and still
produces a per-function role. However, it has two gaps relative to this
platform's goals:

1. **Auto-generated role names are opaque** (a CloudFormation-generated
   suffix), which conflicts with the explicit resource naming this project
   commits to in the [naming conventions](../standards/naming-conventions.md)
   (e.g. `batch-inference-dev-role-fn-submit-job`) -- a name an operator can
   find in IAM without cross-referencing a stack's resource list first.
2. **The default CloudWatch Logs permission SAM attaches** (equivalent to
   the AWS managed `AWSLambdaBasicExecutionRole`) grants
   `logs:CreateLogGroup`/`CreateLogStream`/`PutLogEvents` on
   `arn:aws:logs:*:*:*` -- every log group in the account, not just the one
   this function writes to. That is broader than this platform's
   least-privilege bar.

## Decision

Every Lambda function in `template.yaml` sets its own `Role:` property,
pointing at a hand-written `AWS::IAM::Role` resource with:

- An explicit `RoleName` following the naming convention.
- A logging statement scoped to exactly that function's pre-created
  `AWS::Logs::LogGroup` ARN (`.../log-group:/aws/lambda/<function-name>:*`),
  granting only `logs:CreateLogStream` and `logs:PutLogEvents` --
  deliberately **not** `logs:CreateLogGroup`, since CloudFormation already
  creates the log group, so the function never needs to.
- Exactly the additional actions/resources that function's stub (and its
  Phase 3 successor) needs -- e.g. `SubmitJobFunction` gets
  `s3:GetObject` scoped to `uploads/*` in the datasets bucket,
  `dynamodb:PutItem` scoped to the jobs table, and `states:StartExecution`
  scoped to the one state machine. No function has a wildcard `Resource`
  except in the handful of documented cases (X-Ray, CloudWatch metrics)
  where AWS's own APIs don't support resource-level scoping.

## Consequences

- **Every role name is predictable and greppable** in the IAM console
  during an incident, matching the naming convention exactly.
- **A compromised function's blast radius is scoped to precisely the
  resources it legitimately uses** -- `GetJobStatusFunction`, for example,
  cannot write to DynamoDB, touch S3, or start a Step Functions execution,
  because its role simply has no such permission.
- **More template verbosity.** Six functions plus the state machine and the
  SageMaker execution role means eight hand-written roles instead of
  relying on SAM's shorthand. This is a deliberate trade of template length
  for auditability -- appropriate here since the whole point of this
  repository is to demonstrate the IAM discipline explicitly, not to
  minimize YAML line count.
- Adding a new permission to any function is a one-line addition to that
  function's own policy statement list, not a change to a shared policy
  that every function would otherwise inherit.
