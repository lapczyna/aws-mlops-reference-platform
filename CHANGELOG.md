# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/); one tagged
release corresponds to one completed phase of the [roadmap](docs/roadmap.md).

## [Unreleased]

## [0.2.0] - 2026-07-06

### Added -- Phase 2: Infrastructure as Code

- `template.yaml`: full AWS SAM template covering API Gateway (REST API,
  request validation, throttling, access logging), 6 Lambda functions, a
  shared Lambda Layer, a Step Functions state machine, 3 S3 buckets, a
  DynamoDB table, 8 explicit least-privilege IAM roles, a SageMaker Model +
  execution role, and ~9 CloudWatch log groups with configurable retention.
- `statemachine/job_orchestration.asl.json`: the real Step Functions
  definition (ValidateInput -> MarkProcessing -> RunBatchTransformJob ->
  RecordSuccess/RecordFailure), using direct DynamoDB and SageMaker `.sync`
  service integrations rather than Lambda polling loops.
- Six placeholder Lambda handlers (`presign_upload`, `submit_job`,
  `get_job_status`, `get_job_results`, `validate_input`, `record_outcome`)
  proving the API Gateway / Step Functions / Lambda Layer wiring end to end
  ahead of Phase 3's real business logic.
- `bootstrap/api-gateway-account-settings.yaml`: one-time, account-level
  API Gateway CloudWatch Logs role, deliberately kept out of the
  per-environment stack (see ADR-0012).
- `samconfig.toml` with `dev`/`staging`/`prod` deploy configurations.
- Optional customer-managed KMS encryption (`EnableCustomerManagedKey`).
- ADRs 0009-0012 covering the SageMaker model/artifact parameterization,
  opt-in KMS key, explicit per-function IAM roles, and the API Gateway
  account-settings bootstrap split.
- Concrete deployment guide (`docs/guides/deployment-guide.md`).
- A third S3 bucket for model artifacts, and corrected sequence/component
  diagrams (`RecordOutcome` Lambda and `UpdateItem` semantics) discovered
  while implementing the real infrastructure.

Validated with `cfn-lint`, `sam validate --lint`, and `sam build`
(structural build; `--use-container` required for a Lambda-runnable
artifact, see the deployment guide).

## [0.1.0] - 2026-07-06

### Added -- Phase 1: Repository Foundation

- Repository skeleton following Clean Architecture layering
  (`api` / `application` / `domain` / `infrastructure` / `shared`), no
  business logic yet.
- Architecture documentation: system context, container, component, and
  Step Functions state diagrams
  (`docs/architecture/overview.md`).
- Sequence diagrams for every request/job flow
  (`docs/architecture/sequence-diagrams.md`).
- Architecture Decision Records 0001-0008 covering the serverless-first
  approach, SageMaker Batch Transform selection, Step Functions
  orchestration, DynamoDB data model, API Gateway REST API choice, Lambda
  Layer packaging, and the asynchronous job processing pattern.
- Naming conventions and coding standards documentation.
- Development environment guide and deployment strategy guide.
- Project roadmap covering Phases 1-4 and deferred future enhancements.
- Tooling baseline: `pyproject.toml` (Ruff, Black, mypy strict, pytest,
  coverage), `.pre-commit-config.yaml`, `Makefile`.
