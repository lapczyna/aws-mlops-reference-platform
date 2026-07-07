# Changelog

All notable changes to this project are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project follows [Semantic Versioning](https://semver.org/); one tagged
release corresponds to one completed phase of the [roadmap](docs/roadmap.md).

## [Unreleased]

## [0.4.0] - 2026-07-06

### Added -- Phase 4: Enterprise Production Readiness

- `.github/workflows/ci.yml`: lint, typecheck, test (with coverage gate),
  `pip-audit` dependency scan, cfn-lint/sam validate/sam build, and a model
  train+inference-contract smoke test, on every PR and push to `main`.
- `.github/workflows/deploy-staging.yml` (auto-deploy on CI success on
  `main`) and `deploy-prod.yml` (deploy on `v*.*.*` tag, behind a `prod`
  GitHub Environment gate) -- both authenticate via short-lived OIDC
  credentials, no AWS access keys stored anywhere.
- `bootstrap/github-oidc-deploy-role.yaml`: the one-time account-level
  OIDC provider + deploy role this requires.
- `template.yaml`: a CloudWatch dashboard, 6 alarms (API 5xx, aggregate
  Lambda errors, Step Functions failures, DynamoDB throttles, business-level
  job failure rate) and an SNS notification topic with an optional email
  subscription.
- `docs/guides/security-guide.md` (filled in) and `docs/security/threat-model.md`
  (new): a STRIDE walkthrough per trust boundary, including named,
  un-mitigated gaps rather than only listing controls.
- `docs/guides/cost-guide.md` (filled in) and `scripts/estimate_cost.py`:
  worked monthly estimates at three volume tiers, confirming SageMaker
  Batch Transform instance-time dominates cost at every scale.
- `scripts/teardown.sh` and `scripts/smoke_test.sh`: cleanup automation and
  a real end-to-end post-deploy check.
- `docs/runbooks/`: stuck-job, high-failure-rate, API-5xx, and
  deployment-rollback playbooks, cross-referenced from the new alarms.
- `docs/guides/developer-guide.md`, `docs/guides/disaster-recovery.md`,
  `docs/architecture/scalability.md`, and root `CONTRIBUTING.md`.
- ADRs 0014-0016 (GitHub OIDC for CI/CD, alarm/dashboard strategy, prod
  approval gate via GitHub Environments).
- `docs/design-review.md`: a staff-engineer-style review of the finished
  repository.
- Upgraded `black` and `pytest` to patched versions after `pip-audit`
  surfaced CVE-2026-32274 and CVE-2025-71176 in the dev toolchain; fixed a
  Ruff `per-file-ignores` scoping gap for `scripts/`.

This completes the originally planned four-phase roadmap.

## [0.3.0] - 2026-07-06

### Added -- Phase 3: Application Implementation

- Domain layer: `JobId` (ULID) and `JobStatus` value objects, S3 key-layout
  helpers, the `InferenceJob` entity with enforced lifecycle transitions,
  a domain exception hierarchy, and four ports (`JobRepository`,
  `DatasetStorage`, `ResultsStorage`, `JobOrchestrator`).
- Application layer: six use cases (`PresignDatasetUpload`,
  `SubmitBatchJob`, `GetJobStatus`, `GetJobResults`, `ValidateJobInput`,
  `RecordJobOutcome`) and their DTOs, with dependencies injected via
  constructor (ports, not concrete infrastructure).
- Infrastructure adapters: `DynamoDbJobRepository`, `S3DatasetStorage`,
  `S3ResultsStorage`, `StepFunctionsJobOrchestrator`.
- Shared layer: typed environment-driven `Settings` (`shared/config.py`),
  a Powertools `Logger` factory, a Powertools `Metrics` factory
  (`BatchInferencePlatform` namespace), and a uniform API Gateway JSON
  response helper.
- All six Lambda handlers now contain real logic wired at the composition
  root (cold-start client construction), replacing the Phase 2 stubs.
- `ml/train.py` and `ml/inference.py`: trains a scikit-learn
  `RandomForestClassifier` on Iris and packages it for the SageMaker
  scikit-learn container's inference contract; `scripts/package_model.sh`
  uploads the result to a deployed environment. `template.yaml`'s
  `InferenceModel` gained the `SAGEMAKER_PROGRAM`/`SAGEMAKER_SUBMIT_DIRECTORY`
  environment variables this requires.
- ADR-0013: idempotent job submission via DynamoDB/Step Functions
  conditional writes.
- 70 tests (45 unit against in-memory port fakes, 25 integration against
  `moto`-mocked DynamoDB/S3/Step Functions, including full handler-level
  tests) at 97% coverage. Fixed a `pyproject.toml` linting gap where
  `assert`-in-production-code (`S101`) was ignored repo-wide instead of
  only in tests.

Validated with `ruff`, `black`, `mypy --strict`, `pytest --cov`,
`cfn-lint`, and `sam validate`/`sam build`.

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
