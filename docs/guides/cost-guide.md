# Cost Guide

> **Status:** Planned for Phase 4. This stub exists so other Phase 1
> documents can link to a stable path; it will be filled in once real
> infrastructure (Phase 2) and observed usage patterns exist to estimate
> against.

## Planned contents

- Per-service cost breakdown at representative volumes (e.g. 100 / 1,000 /
  10,000 jobs per month) covering API Gateway, Lambda, Step Functions,
  SageMaker Batch Transform, S3, DynamoDB, and CloudWatch.
- Idle-cost analysis confirming the near-zero-idle-cost constraint from the
  [architecture overview](../architecture/overview.md) holds in practice.
- Cost levers available to operators: log retention periods, S3 lifecycle
  policies, DynamoDB TTL, SageMaker instance type selection.
- A worked example using AWS Pricing Calculator or `scripts/estimate_cost.py`
  (see [`scripts/README.md`](../../scripts/README.md)).

See [ADR-0002](../adr/0002-serverless-first-architecture.md) for the
architectural decisions this cost model is built on.
