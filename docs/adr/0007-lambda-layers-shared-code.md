# ADR-0007: Lambda Layer for Shared Application Code

## Status

Accepted

## Context

The platform has multiple Lambda functions (`PresignUpload`, `SubmitJob`,
`GetJobStatus`, `GetJobResults`, `ValidateInput`, and the terminal-state
handlers) that all depend on the same shared application code: the domain
layer, the DynamoDB/S3 infrastructure adapters, structured logging setup,
and configuration loading (see the `src/batch_inference_platform` package
layout). Duplicating this code per function -- or worse, letting each
function's deployment package drift independently -- would violate DRY and
make the Clean Architecture boundaries meaningless in practice.

## Decision

We will package `src/batch_inference_platform` (the domain, application, and
infrastructure layers, plus third-party dependencies like `boto3`,
`aws-lambda-powertools`, and `pydantic`) as a single **Lambda Layer**,
attached to every function in the stack. Each function's own deployment
package (`CodeUri`) contains only its thin handler module in
`api/handlers/`.

## Consequences

- **One source of truth for domain and infrastructure code.** A bug fix or
  behavior change in a repository adapter is deployed to every function
  that uses it via a single layer version bump.
- **Faster, smaller per-function deployment packages**, since handler code
  changes don't require re-uploading the shared dependency tree.
- **Layer versioning discipline is required:** every SAM deployment
  publishes a new layer version and every function must reference it
  explicitly (SAM's `!Ref` on the layer resource handles this
  automatically), so there is no risk of functions silently drifting onto
  different layer versions within a single deployment.
- **Trade-off accepted:** all functions share the same dependency versions.
  This is desirable here (consistency, simpler dependency management) but
  would become a constraint if a future function needed an incompatible
  dependency version -- at that point it would get its own layer rather
  than forcing a split of this one.
