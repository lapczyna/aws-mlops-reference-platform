# Roadmap

This platform is built incrementally, one merge-able phase at a time. Each
phase leaves the repository in a fully functional, reviewable state; there
is no phase that depends on a future phase to "make sense."

## Phase 1 -- Repository Foundation (this phase)

Directory structure, architecture and sequence diagrams, ADR log, coding
and naming standards, development environment, and this roadmap. No
business logic or infrastructure yet.

**Status:** In progress.

## Phase 2 -- Infrastructure as Code

The full AWS SAM template: API Gateway REST API, Lambda functions (empty
handlers or thin stubs sufficient to deploy), Step Functions state machine,
S3 buckets, DynamoDB table, IAM roles, CloudWatch log groups, parameters,
outputs, tagging, encryption, and lifecycle policies. Deployable end-to-end
with placeholder application logic.

**Status:** Not started.

## Phase 3 -- Application Implementation

Full application logic behind the infrastructure from Phase 2: REST
endpoint handlers, dataset upload flow, job submission, state machine task
handlers, result persistence and retrieval, structured logging,
configuration management, validation, dependency injection at the
composition root, unit tests, and integration tests against `moto`-mocked
AWS services.

**Status:** Not started.

## Phase 4 -- Enterprise Production Readiness

CI/CD via GitHub Actions, CloudWatch dashboards and alarms on custom
metrics, a documented threat model and security review, a cost guide with
worked estimates, operational runbooks, a developer/contribution guide,
additional ADRs for decisions made during this phase, a disaster recovery
guide, and a staff-engineer-style design review of the finished repository
with concrete improvement recommendations.

**Status:** Not started.

## Beyond Phase 4 -- candidate future enhancements

These are explicitly out of scope for the four planned phases, and are
recorded here so they're deliberately deferred rather than forgotten:

- **Event-driven completion notification** (EventBridge/SNS/webhook) so
  clients don't have to poll for job completion (extends
  [ADR-0008](adr/0008-asynchronous-job-processing-pattern.md)).
- **A `status`-based DynamoDB GSI** if an admin/dashboard view needs to list
  jobs by state rather than by ID (extends
  [ADR-0005](adr/0005-dynamodb-single-table-job-state.md)).
- **Multi-tenant support** (per-tenant IAM scoping, per-tenant data
  partitioning) if the platform needs to serve more than one logical
  consumer.
- **Model versioning / A-B rollout** for the SageMaker model artifact,
  building on the immutable-artifact approach from the
  [ML Lens mapping](architecture/overview.md#aws-ml-lens-considerations).
- **Private API Gateway + VPC endpoints** for an internal-only deployment
  posture, enabled by the REST API choice in
  [ADR-0006](adr/0006-api-gateway-rest-api-choice.md).
- **Multi-region disaster recovery**, beyond the single-region DR guide
  planned for Phase 4.
