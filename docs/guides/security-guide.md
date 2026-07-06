# Security Guide

> **Status:** Planned for Phase 4. This stub exists so other Phase 1
> documents can link to a stable path; the full guide will be written once
> IAM roles, encryption configuration, and network boundaries exist in the
> SAM template (Phase 2) to document and review.

## Planned contents

- Threat model for the platform (STRIDE-based walkthrough of the request
  and job-processing paths).
- Least-privilege IAM policy documentation per function/role, with the
  reasoning behind each granted action (cross-referenced from
  `template.yaml` comments).
- Data protection: encryption at rest (S3 SSE, DynamoDB encryption) and in
  transit (TLS enforcement via bucket/API policies).
- Input validation boundaries (API Gateway request models, application-layer
  validation) per the
  [coding standards](../standards/coding-standards.md#security-sensitive-code-review-checklist).
- Secrets management approach (SSM Parameter Store / Secrets Manager, no
  plaintext secrets in the repository or environment variables).
- Dependency and container scanning approach used in CI.

See [ADR-0006](../adr/0006-api-gateway-rest-api-choice.md) for the API
security posture decided in Phase 1.
