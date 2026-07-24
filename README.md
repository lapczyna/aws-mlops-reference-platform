# Batch Inference Platform

[![CI](https://github.com/lapczyna/aws-mlops-reference-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/lapczyna/aws-mlops-reference-platform/actions/workflows/ci.yml)

A serverless, production-oriented reference platform for asynchronous ML
batch inference on AWS: upload a dataset, submit an inference job, track its
progress, and retrieve predictions -- all on managed, pay-per-use AWS
services with near-zero idle cost.

The platform is built and maintained the way an internal infrastructure
team would run it: infrastructure as code, architecture decisions recorded
as they're made, least-privilege IAM throughout, and a delivery model where
every change lands as a reviewable, independently functional increment.

The ML model behind the API is intentionally simple -- a `scikit-learn`
classifier trained on the Iris dataset. The point of this repository is the
platform around the model: how a batch inference request is accepted,
orchestrated, executed, observed, and made reliable in production, not
model sophistication.

## Architecture at a glance

```mermaid
flowchart LR
    C(["API Consumer"]) -->|"HTTPS / REST"| APIGW["API Gateway"]
    APIGW --> L["Lambda\n(request handlers)"]
    L --> SFN["Step Functions\n(orchestration)"]
    SFN --> SM["SageMaker\nBatch Transform"]
    SM --> S3["Amazon S3\n(datasets & results)"]
    SFN --> DDB["DynamoDB\n(job status)"]
    L --> DDB
    L -.->|"logs & metrics"| CW["CloudWatch"]
    SFN -.-> CW
    SM -.-> CW
```

Client → API Gateway → Lambda → Step Functions → Batch Inference Job → S3 →
Status Update → DynamoDB → Result Retrieval API.

Job submission is **asynchronous**: `POST /jobs` returns a `job_id`
immediately, clients poll for status, and retrieve results once complete.
This is a deliberate design choice, not a limitation -- see
[ADR-0008](docs/adr/0008-asynchronous-job-processing-pattern.md).

Full system context, container, and component diagrams, the data model, and
the Well-Architected Framework mapping live in
[`docs/architecture/overview.md`](docs/architecture/overview.md). Every
individual request/job flow is diagrammed in
[`docs/architecture/sequence-diagrams.md`](docs/architecture/sequence-diagrams.md).

## Why this architecture

| Decision                                          | Rationale (full reasoning in the linked ADR)                     |
| ---------------------------------------------------- | ---------------------------------------------------------------------- |
| Serverless-only: no EC2, ECS, EKS, or Aurora            | [ADR-0002](docs/adr/0002-serverless-first-architecture.md) -- near-zero idle cost, matches bursty batch workload shape |
| SageMaker Batch Transform, not Processing               | [ADR-0003](docs/adr/0003-sagemaker-batch-transform-vs-processing.md) -- purpose-built for batch inference, native `.sync` Step Functions integration |
| Step Functions for orchestration                        | [ADR-0004](docs/adr/0004-step-functions-for-orchestration.md) -- no Lambda polling loops, built-in retry/catch, full execution visibility |
| DynamoDB single-table, on-demand, with TTL               | [ADR-0005](docs/adr/0005-dynamodb-single-table-job-state.md) -- matches the platform's one real access pattern, zero capacity planning |
| API Gateway REST API, not HTTP API                       | [ADR-0006](docs/adr/0006-api-gateway-rest-api-choice.md) -- request validation, usage plans, WAF and private-endpoint support |
| Shared code as a Lambda Layer                            | [ADR-0007](docs/adr/0007-lambda-layers-shared-code.md) -- one source of truth for domain/infrastructure code across functions |
| Asynchronous submit-and-poll, not synchronous inference    | [ADR-0008](docs/adr/0008-asynchronous-job-processing-pattern.md) -- API Gateway's 29s integration timeout makes synchronous batch inference structurally impossible |
| SageMaker Model/container image as deploy-time parameters   | [ADR-0009](docs/adr/0009-sagemaker-model-artifact-parameterization.md) -- lets infrastructure deploy before the model is trained and uploaded |
| Customer-managed KMS key is opt-in, not default             | [ADR-0010](docs/adr/0010-optional-customer-managed-kms-key.md) -- avoids KMS cost/complexity in `dev` while staying available for `staging`/`prod` |
| Explicit per-function IAM roles, not SAM auto-generated       | [ADR-0011](docs/adr/0011-explicit-per-function-iam-roles.md) -- predictable role names, tighter-than-default logging permissions |
| API Gateway account settings live in a separate bootstrap stack | [ADR-0012](docs/adr/0012-api-gateway-account-settings-bootstrap.md) -- avoids one environment's teardown clobbering an account-wide singleton |
| Idempotent job submission via conditional writes              | [ADR-0013](docs/adr/0013-idempotent-job-submission.md) -- retrying `POST /jobs` with the same `job_id` never double-creates a job or a Step Functions execution |
| GitHub OIDC for CI/CD, no long-lived AWS credentials            | [ADR-0014](docs/adr/0014-github-oidc-for-cicd.md) -- each deploy assumes a short-lived, repo-scoped role via a signed identity token |
| CloudWatch alarms: aggregate over per-resource                    | [ADR-0015](docs/adr/0015-cloudwatch-alarms-and-dashboard.md) -- 6 meaningful alarms (incl. a business-level failure-rate signal) instead of dozens of near-duplicate ones |
| Prod approval gate via GitHub Environments                          | [ADR-0016](docs/adr/0016-prod-approval-gate-via-github-environments.md) -- wired correctly today; the reviewer-approval enforcement itself needs a plan upgrade on a private repo |

## Technology stack

| Layer              | Technology                                            |
| -------------------- | ---------------------------------------------------------- |
| Language              | Python 3.12                                                |
| Infrastructure as Code | AWS SAM                                                    |
| API                    | Amazon API Gateway (REST API)                              |
| Compute                | AWS Lambda                                                 |
| Orchestration          | AWS Step Functions                                          |
| ML execution           | Amazon SageMaker Batch Transform                            |
| Storage                | Amazon S3                                                   |
| Job state               | Amazon DynamoDB                                             |
| Observability           | Amazon CloudWatch (Logs, Metrics, Alarms, Dashboards)        |
| Access control           | AWS IAM (least privilege, per-function roles)               |
| CI/CD                    | GitHub Actions (OIDC deploy role, no long-lived credentials) |
| Testing                   | pytest, moto                                                |
| Code quality               | Ruff, Black, mypy (strict), pre-commit, pip-audit           |

## Repository structure

```
├── .github/workflows/                # CI (lint/typecheck/test/validate) + CD (staging auto-deploy, prod on tag)
├── src/batch_inference_platform/   # Application code (Clean Architecture layers)
│   ├── api/handlers/                 # Lambda handlers (interface layer / composition roots)
│   ├── application/                  # Use cases and DTOs
│   ├── domain/                        # Entities, value objects, ports, exceptions
│   ├── infrastructure/                 # AWS adapters (DynamoDB, S3, Step Functions, SageMaker)
│   └── shared/                          # Logging, configuration, metrics, cross-cutting concerns
├── src/requirements.txt              # Third-party deps packaged into the shared Lambda Layer
├── tests/                            # 70 tests, 97% coverage (unit + moto-mocked integration)
├── ml/                                # Model training script and packaging (Iris classifier)
├── scripts/                           # package_model, smoke_test, teardown, estimate_cost
├── statemachine/
│   └── job_orchestration.asl.json      # Step Functions state machine definition
├── bootstrap/
│   ├── api-gateway-account-settings.yaml # One-time account-level CloudWatch role for API Gateway
│   └── github-oidc-deploy-role.yaml       # One-time account-level GitHub Actions deploy role (OIDC)
├── docs/
│   ├── architecture/                    # Overview, sequence diagrams, scalability
│   ├── adr/                              # Architecture Decision Records
│   ├── security/                          # Threat model
│   ├── runbooks/                           # Operational playbooks
│   ├── standards/                          # Naming conventions, coding standards
│   ├── guides/                               # Development, deployment, cost, security, DR, developer guides
│   ├── roadmap.md                             # Phased delivery plan
│   └── design-review.md                        # Staff-engineer-style review of this repository
├── template.yaml                       # AWS SAM template: API Gateway, Lambda, Step Functions,
│                                          # S3, DynamoDB, IAM, SageMaker, CloudWatch, alarms, dashboard
├── samconfig.toml                      # Per-environment (dev/staging/prod) deploy configuration
├── pyproject.toml                      # Project metadata, Ruff/Black/mypy/pytest config
├── CONTRIBUTING.md                     # PR process, definition of done
└── Makefile                            # Common developer commands
```

## Getting started

```bash
git clone <repo-url> && cd aws-mlops-reference-platform
make install         # create venv, install package + dev dependencies
make install-hooks   # install pre-commit git hooks
make test            # run the test suite
```

Full setup instructions, troubleshooting, and the local AWS-mocking
approach (`moto`) are in the
[development environment guide](docs/guides/development-environment.md).
To deploy the infrastructure itself, see the
[deployment guide](docs/guides/deployment-guide.md) for concrete steps
(the [deployment strategy guide](docs/guides/deployment-strategy.md)
covers the *why* behind environments and promotion). After deploying, train
and upload the model artifact once per environment:

```bash
pip install -e ".[ml]"
scripts/package_model.sh dev
```

See [`ml/README.md`](ml/README.md) for details.

## Documentation

Start at the [documentation index](docs/README.md) for the full map. Key
entry points:

- [Architecture overview](docs/architecture/overview.md) ·
  [Sequence diagrams](docs/architecture/sequence-diagrams.md) ·
  [Scalability & performance](docs/architecture/scalability.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Security guide](docs/guides/security-guide.md) ·
  [Threat model](docs/security/threat-model.md)
- [Naming conventions](docs/standards/naming-conventions.md) ·
  [Coding standards](docs/standards/coding-standards.md)
- [Development environment](docs/guides/development-environment.md) ·
  [Developer guide](docs/guides/developer-guide.md)
- [Deployment strategy](docs/guides/deployment-strategy.md) ·
  [Deployment guide](docs/guides/deployment-guide.md) ·
  [Disaster recovery](docs/guides/disaster-recovery.md)
- [Cost guide](docs/guides/cost-guide.md) ·
  [Runbooks](docs/runbooks/README.md)
- [Project roadmap](docs/roadmap.md) ·
  [Design review](docs/design-review.md)

## Design principles

This platform is built against the AWS Well-Architected Framework and the
AWS Machine Learning Lens; the detailed mapping of each pillar to concrete
architectural choices is in
[`docs/architecture/overview.md`](docs/architecture/overview.md#aws-well-architected-framework-mapping).
Beyond the AWS-specific frameworks, the codebase follows Clean Architecture
layering, SOLID principles, and 12-factor configuration -- detailed in the
[coding standards](docs/standards/coding-standards.md).

## Delivery model

This repository is built incrementally: each phase is scoped to be a
complete, independently functional, mergeable unit of work, tagged as a
release once complete. See the [roadmap](docs/roadmap.md) for the full
phase plan and what's deferred beyond it.

| Phase | Scope                                     | Status         |
| ----- | -------------------------------------------- | ------------------ |
| 1     | Repository foundation, architecture, docs      | Complete (`v0.1.0`) |
| 2     | Infrastructure as Code (AWS SAM)                | Complete (`v0.2.0`) |
| 3     | Application implementation                       | Complete (`v0.3.0`) |
| 4     | Enterprise production readiness (CI/CD, observability, security review) | Complete (`v0.4.0`) |

This completes the originally planned roadmap. See the
[design review](docs/design-review.md) for an outside-in assessment of the
result and what a next iteration should prioritize, and
["Beyond Phase 4"](docs/roadmap.md#beyond-phase-4--candidate-future-enhancements)
for the specific deferred items.

## License

[MIT](LICENSE)
