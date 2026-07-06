# Coding Standards

These standards apply to all Python code under `src/` and `tests/`. They are
enforced automatically by `pre-commit`, `make lint`, `make typecheck`, and
CI (Phase 4) -- nothing here is aspirational or manually policed.

## Language and tooling baseline

| Concern          | Tool                | Configuration                              |
| ----------------- | --------------------- | --------------------------------------------- |
| Python version      | 3.12                | `pyproject.toml` `[project] requires-python`  |
| Linting             | Ruff                 | `pyproject.toml` `[tool.ruff]`                |
| Formatting          | Black (line length 100) | `pyproject.toml` `[tool.black]`             |
| Static typing        | mypy (strict mode)   | `pyproject.toml` `[tool.mypy]`                |
| Testing              | pytest + moto        | `pyproject.toml` `[tool.pytest.ini_options]`  |

All four run in `pre-commit` (see `.pre-commit-config.yaml`) and must pass
before a commit is accepted locally, and again in CI before a PR can merge.

## Type hints

Every function and method signature -- including test helpers -- must be
fully typed. `mypy --strict` treats an untyped `def` as an error, not a
warning. `Any` is permitted only at true external boundaries (e.g.
deserializing an API Gateway event body) and must be narrowed to a concrete
type (a Pydantic model) immediately afterward, not threaded through
business logic.

```python
# Correct: narrowed at the boundary
def parse_submit_job_request(raw_body: str) -> SubmitJobRequest:
    return SubmitJobRequest.model_validate_json(raw_body)

# Incorrect: Any leaks into application logic
def submit_job(payload: Any) -> None: ...
```

## Clean Architecture layering

The dependency arrow always points inward. Concretely, for
`src/batch_inference_platform/`:

```
api/  --------> application/ --------> domain/
                     ^                     ^
infrastructure/ -----+---------------------+
```

- **`domain/`** has zero imports from `boto3`, `aws_lambda_powertools`, or
  any other layer. It is pure Python business logic and can be unit-tested
  with no mocks.
- **`application/`** (use cases) depends on `domain/` and on **ports**
  (abstract interfaces defined in `domain/ports/`), never on concrete
  `infrastructure/` classes. Dependencies are injected by the caller.
- **`infrastructure/`** implements the ports defined in `domain/ports/`
  using real AWS SDK calls, and may import `domain/` and third-party SDKs
  freely.
- **`api/`** (Lambda handlers) is the composition root: it constructs
  concrete infrastructure adapters, injects them into use cases, and
  translates between the AWS event shape and application DTOs. Handlers
  contain no business logic themselves.

A linter rule of thumb during review: if a file under `domain/` imports
`boto3`, that is a layering violation, not a style nitpick.

## SOLID in this codebase

- **Single Responsibility:** one use case class per application capability
  (`SubmitBatchJob`, `GetJobStatus`), not one god-service handling all job
  operations.
- **Open/Closed:** new job failure reasons extend the `JobStatus`/exception
  hierarchy rather than adding conditionals to existing use cases.
- **Liskov Substitution:** any class implementing `JobRepository` (the port)
  must be substitutable in tests and production without the use case caring
  which concrete adapter it received.
- **Interface Segregation:** ports are narrow and capability-scoped
  (`JobRepository`, `DatasetStorage`, `InferenceOrchestrator`) rather than
  one large `AwsGateway` interface.
- **Dependency Inversion:** use cases depend on the `domain/ports/`
  abstractions; concrete `infrastructure/` adapters are wired in at the
  Lambda handler (composition root), never imported directly by a use case.

## Error handling

- Domain and application code raises a typed exception from
  `domain/exceptions/` (e.g. `JobNotFoundError`, `InvalidDatasetError`) --
  never a bare `Exception` or an AWS SDK exception leaked upward.
- Lambda handlers are the only place AWS SDK exceptions
  (`botocore.exceptions.ClientError`, etc.) are caught and translated, at
  the boundary, into either a domain exception or an HTTP response.
- No bare `except:` clauses. Catch the narrowest exception type that can
  actually occur.
- Fail fast on invalid input; do not silently coerce or default around bad
  data.

## Structured logging

All logging goes through `aws_lambda_powertools.Logger`, configured once in
`shared/` and reused by every handler, emitting structured JSON with:

- `job_id` (or equivalent correlation ID) injected on every log line related
  to a job, via Powertools' logger context, not string-formatted manually.
- No secrets, credentials, or full dataset contents ever logged -- log
  identifiers and metadata (row counts, S3 keys), not payloads.
- `LOG_LEVEL` is configurable per environment via a Lambda environment
  variable (`INFO` in prod, `DEBUG` available for troubleshooting in
  dev/staging).

## Configuration

Configuration follows [12-factor](https://12factor.net/config): all
environment-specific values (table names, bucket names, ARNs) are injected
via Lambda environment variables set by the SAM template -- never
hard-coded, never read from a checked-in config file per environment.
Application code accesses configuration through a single typed
`shared/config.py` module (implemented in Phase 3), not scattered
`os.environ[...]` calls.

## Docstrings

Google-style docstrings, and only where the *why* isn't already obvious from
the type signature and name. A well-named, fully-typed function needs no
docstring restating its signature in prose; a function with a non-obvious
invariant or side effect does.

## Testing

- **Unit tests** (`tests/unit/`) cover `domain/` and `application/` with no
  AWS calls at all -- ports are faked with in-memory test doubles.
- **Integration tests** (`tests/integration/`) exercise `infrastructure/`
  adapters against `moto`-mocked AWS services, verifying actual DynamoDB
  item shapes, S3 interactions, and IAM-permission-shaped behavior.
- Coverage threshold: **85%**, enforced via `pyproject.toml`
  `[tool.coverage.report]` and CI.
- Arrange-Act-Assert structure; one behavior asserted per test; test names
  describe the behavior (`test_submit_job_rejects_missing_dataset`), not the
  implementation detail.
- No test may reach a real AWS account. This is enforced by convention now
  and will be enforced by CI network policy in Phase 4.

## Security-sensitive code review checklist

- No secrets, credentials, or API keys committed, ever -- use environment
  variables and, for anything genuinely sensitive, AWS Secrets Manager /
  SSM Parameter Store (SecureString).
- Every new IAM permission added to a role is the *specific* action on the
  *specific* resource ARN needed -- no `Action: "*"`, no `Resource: "*"`
  without a documented reason (see the
  [security guide](../guides/security-guide.md), added in Phase 4).
- All user-supplied input (API request bodies, S3 object keys derived from
  requests) is validated before use -- both at the API Gateway request
  validation layer and again in application code, since defense in depth
  matters more than trusting the edge alone.
