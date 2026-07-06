# ADR-0002: Serverless-First Compute, No EC2 / ECS / EKS / Aurora

## Status

Accepted

## Context

Batch inference workloads are bursty by nature: a platform might process
zero jobs for hours and then several concurrently. Provisioning
always-on compute (EC2 instances, ECS/Fargate services kept warm, an EKS
control plane, or an Aurora cluster) to handle that burst means paying for
idle capacity the overwhelming majority of the time. The project's explicit
cost constraint is "idle cost should be almost zero."

We also want the architecture to demonstrate current AWS serverless best
practice to a technical reviewer, not a lift-and-shift of a traditional
always-on service.

## Decision

We will build the entire platform on managed, pay-per-use AWS services:

- **API Gateway** (REST API) for the HTTP surface.
- **AWS Lambda** for all request handling and orchestration glue.
- **AWS Step Functions** for stateful workflow orchestration.
- **Amazon SageMaker Batch Transform** for the ML execution step (a managed,
  ephemeral compute environment that AWS provisions and tears down per job).
- **Amazon S3** for all object storage.
- **Amazon DynamoDB** (on-demand capacity mode) for job state.

We explicitly rule out EC2, ECS, EKS, and Aurora for this system. If a
future requirement genuinely needs long-running or stateful compute that
Lambda cannot satisfy (e.g. sustained sub-100ms real-time inference at high
throughput), that would warrant a new ADR re-evaluating this decision rather
than a silent architecture drift.

## Consequences

- **Idle cost approaches zero.** Every resource in the request path bills
  per invocation, per GB-second, or per GB-stored -- there is no fixed
  monthly floor.
- **Operational burden shifts to AWS** for patching, scaling, and
  availability of the underlying compute, which is a net win for a small
  platform team.
- **Cold starts and Lambda's 15-minute maximum duration become real
  constraints.** This is why orchestration is delegated to Step Functions
  (which has no such duration limit) rather than a single long-running
  Lambda function.
- **SageMaker Batch Transform** provisions its own transient instances per
  job; this is still "serverless" in the sense that matters here (the
  platform team manages no persistent servers), even though SageMaker's
  control plane runs on EC2 under the hood -- that management burden is
  AWS's, not ours.
- Local development and testing must simulate these managed services
  (`moto`, SAM Local) rather than running lightweight local equivalents,
  which is an accepted trade-off documented in the
  [development environment guide](../guides/development-environment.md).
