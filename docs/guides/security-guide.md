# Security Guide

The platform's security posture rests on defense in depth: no single
control is load-bearing on its own. This guide is the index; the detailed
STRIDE walkthrough lives in [`docs/security/threat-model.md`](../security/threat-model.md).

## Identity and access management

- **No long-lived AWS credentials anywhere** -- not in this repository, not
  in GitHub secrets. CI/CD assumes a short-lived role via GitHub's OIDC
  identity provider, scoped to this exact repository and to the two refs
  the deploy workflows run from (`main`, `v*` tags). See
  [ADR-0014](../adr/0014-github-oidc-for-cicd.md).
- **Every Lambda function has its own IAM role**, hand-written with only
  the specific actions and resource ARNs that function needs -- not a
  shared execution role, not an AWS managed policy. See
  [ADR-0011](../adr/0011-explicit-per-function-iam-roles.md) for the full
  reasoning and the [naming conventions](../standards/naming-conventions.md)
  for how to find any given role by name.
- **No function can escalate its own privileges.** None of the six Lambda
  roles include `iam:*` actions; only the Step Functions execution role can
  `iam:PassRole`, and only to the one SageMaker execution role, only when
  `iam:PassedToService` is `sagemaker.amazonaws.com`.
- **The GitHub Actions deploy role itself is scoped by resource-name
  pattern** (`batch-inference-*`) everywhere AWS resource ARNs support it
  pre-creation; the exceptions (API Gateway, CloudWatch) are documented
  inline in `bootstrap/github-oidc-deploy-role.yaml`.

## Data protection

| Concern            | Control                                                                      |
| --------------------- | --------------------------------------------------------------------------------- |
| Encryption at rest       | S3 (SSE-S3 by default, customer-managed KMS opt-in), DynamoDB (AWS-owned key by default, KMS opt-in). See [ADR-0010](../adr/0010-optional-customer-managed-kms-key.md). |
| Encryption in transit     | Every S3 bucket policy denies any request where `aws:SecureTransport` is `false`. API Gateway is HTTPS-only by construction (no HTTP listener exists). |
| Public access               | All three buckets have `PublicAccessBlockConfiguration` fully enabled and `BucketOwnerEnforced` ownership (ACLs disabled entirely). |
| Data minimization             | Prediction inputs/outputs and job metadata are the only data this platform stores; no PII schema is assumed or required by the Iris use case. |

## Input validation

Defense in depth, not a single edge check:

1. **API Gateway request validation models** (JSON Schema) reject a
   malformed `POST /jobs` body before it reaches Lambda at all -- see
   [ADR-0006](../adr/0006-api-gateway-rest-api-choice.md).
2. **The domain layer re-validates independently.** `JobId` rejects
   anything that isn't a well-formed ULID regardless of which layer
   constructs one; `ValidateJobInput` re-checks the dataset actually exists
   and is non-empty inside the state machine, even though `SubmitBatchJob`
   already checked once at submission time -- a client cannot skip
   validation by invoking Step Functions or a handler directly.
3. **No use case trusts its caller.** Every use case in
   `src/batch_inference_platform/application/use_cases/` re-derives what it
   needs from ports rather than accepting pre-validated data as a
   parameter, per [coding standards](../standards/coding-standards.md#security-sensitive-code-review-checklist).

## Secrets management

This platform currently has no secrets to manage -- no database
passwords, no third-party API keys. If one is ever needed: it goes in AWS
Systems Manager Parameter Store as a `SecureString` (or Secrets Manager if
rotation is required), referenced by ARN in `template.yaml` and resolved
by the Lambda function's own IAM-scoped `ssm:GetParameter` call at
runtime -- never as a plaintext Lambda environment variable, and never
committed to the repository. `detect-private-key` in `.pre-commit-config.yaml`
is a backstop against the latter, not the primary control.

## Dependency and supply chain security

- `pip-audit` runs in CI (`ci.yml`'s `quality` job) against every PR and
  push to `main`, failing the build if a dependency has a known CVE with no
  available fix ignored. Caught and fixed two real CVEs while building this
  guide -- `black` (CVE-2026-32274) and `pytest` (CVE-2025-71176) -- by
  upgrading both in `pyproject.toml`, not by suppressing the finding.
- Dependency versions are pinned to ranges (not exact pins) in
  `pyproject.toml` and `src/requirements.txt`, balancing reproducibility
  against not silently missing security patches within a compatible range.
- GitHub's own Dependabot alerts (Settings > Code security) are a free
  complement to `pip-audit` and are recommended to be enabled on this
  repository -- they catch vulnerabilities disclosed between CI runs, not
  just at commit time.
- The SageMaker inference container is AWS's own prebuilt, maintained
  image (not a custom Dockerfile this repository builds and is responsible
  for patching) -- see [ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md).

## Logging and audit trail

- Every Lambda handler logs structured JSON via Powertools, with `job_id`
  as a correlation key propagated across every hop -- see
  [coding standards](../standards/coding-standards.md#structured-logging).
  No dataset contents, predictions, or secrets are ever logged, only
  identifiers and metadata.
- CloudWatch Logs retention is explicit and finite everywhere (parameterized
  by `LogRetentionInDays`), never "never expire" by accident.
- AWS CloudTrail is an account-level service, not something this
  application stack manages -- but every account this platform is deployed
  into should have an organization or account trail enabled, giving an
  independent audit record of every API call (including who deployed what,
  when) that CloudWatch Logs alone would not capture.

## Incident response

See [`docs/runbooks/`](../runbooks/README.md) for the operational playbooks
this platform's alarms (ADR-0015) point an on-call engineer toward.

## What this platform deliberately does not claim

This is a reference architecture, not a certified system. It has not been
through a formal penetration test, and "aligns with common baseline
controls" (least privilege, encryption, audit logging) is not the same
claim as "certified compliant with [framework]." Treat the architecture as
a strong starting point for a regulated workload, not a substitute for
that workload's actual compliance program.
