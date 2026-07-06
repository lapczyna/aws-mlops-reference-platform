# Naming Conventions

Consistent naming makes a multi-service AWS stack navigable in the console
under incident pressure, keeps CloudFormation logical IDs and physical
resource names predictable, and prevents collisions across environments
deployed from the same templates. This document is the single source of
truth for naming across the project; IaC (Phase 2) must conform to it.

## Resource naming pattern

Physical AWS resource names follow:

```
{project}-{environment}-{resource-type}-{purpose}
```

| Segment       | Values                                   | Notes                                                        |
| -------------- | ------------------------------------------ | ------------------------------------------------------------- |
| `project`       | `batch-inference`                         | Fixed for this platform.                                      |
| `environment`   | `dev`, `staging`, `prod`                  | Matches the SAM/CloudFormation deployment parameter.           |
| `resource-type` | `api`, `fn`, `sm`, `table`, `bucket`, `role` | Short, consistent abbreviation per AWS service.              |
| `purpose`       | e.g. `submit-job`, `jobs`, `datasets`     | Free-text, kebab-case, describes what the resource is for.    |

Examples:

| Resource                          | Name                                             |
| ----------------------------------- | --------------------------------------------------- |
| REST API                             | `batch-inference-dev-api`                          |
| Lambda function (submit job)         | `batch-inference-dev-fn-submit-job`                |
| Lambda function (get status)         | `batch-inference-dev-fn-get-job-status`             |
| Step Functions state machine         | `batch-inference-dev-sm-job-orchestration`          |
| DynamoDB table                       | `batch-inference-dev-table-jobs`                    |
| S3 bucket (datasets)                  | `batch-inference-dev-datasets-{account-id}`         |
| S3 bucket (results)                   | `batch-inference-dev-results-{account-id}`          |
| IAM role (submit job function)        | `batch-inference-dev-role-fn-submit-job`            |

S3 bucket names include the AWS account ID because bucket names must be
**globally** unique across all AWS accounts, not just within this stack.

## CloudFormation / SAM logical IDs

Logical IDs use **PascalCase** with no separators, and should read as a
sentence fragment describing the resource, not restate its type redundantly:

```
SubmitJobFunction
JobsTable
JobOrchestrationStateMachine
DatasetsBucket
```

Avoid generic logical IDs like `Function1` or `MyTable`.

## Tagging strategy

Every taggable resource in the SAM template carries these tags (applied via
the template's global `Tags` property, not per-resource, so tagging cannot
be forgotten on a new resource):

| Tag           | Example value            | Purpose                                             |
| -------------- | --------------------------- | ------------------------------------------------------ |
| `Project`       | `batch-inference-platform` | Cost allocation and resource grouping.                |
| `Environment`   | `dev` / `staging` / `prod`  | Environment-scoped cost reports and access policies.  |
| `ManagedBy`     | `aws-sam`                  | Signals the resource is IaC-owned; discourages manual console edits. |
| `Owner`         | `platform-team`            | Points at the team accountable for the resource.       |

## Python code

| Element              | Convention                          | Example                          |
| --------------------- | -------------------------------------- | ----------------------------------- |
| Modules / packages      | `snake_case`                          | `job_repository.py`                |
| Classes                 | `PascalCase`                          | `InferenceJob`, `JobRepository`     |
| Functions / methods      | `snake_case`                          | `submit_job()`, `get_job_status()`  |
| Constants                | `UPPER_SNAKE_CASE`                    | `DEFAULT_JOB_TTL_DAYS`              |
| Type variables            | `PascalCase` with `T` suffix optional | `JobT`                             |
| Private members           | leading underscore                    | `_serialize_item()`                |

Domain entities are named after the business concept they represent
(`InferenceJob`, not `JobModel` or `JobDTO` -- the layer is already implied
by the package it lives in; see
[coding standards](coding-standards.md#clean-architecture-layering)).

## Environment variables

Lambda environment variables use `UPPER_SNAKE_CASE` and are namespaced by
concern, not by function, so the same variable name means the same thing
everywhere it appears:

```
JOBS_TABLE_NAME
DATASETS_BUCKET_NAME
RESULTS_BUCKET_NAME
STATE_MACHINE_ARN
LOG_LEVEL
POWERTOOLS_SERVICE_NAME
```

## Git conventions

- **Branches:** `phase/{n}-{short-description}` for phase work (e.g.
  `phase/2-infrastructure-as-code`), `fix/{short-description}` for bug fixes.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`), imperative
  mood, explaining *why* in the body when the change isn't self-evident.
- **Tags:** `v{major}.{minor}.{patch}` (semantic versioning), one tag per
  completed phase per the project's incremental delivery model (see the
  [roadmap](../roadmap.md)).
