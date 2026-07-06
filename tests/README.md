# Tests

This directory hosts the automated test suite: 70 tests, 97% coverage of
`src/batch_inference_platform` (`make test-cov`).

## Layout

| Directory           | Purpose                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `unit/`               | Fast, isolated tests with no I/O. Domain entities/value objects and application use cases, exercised against in-memory fakes (`tests/unit/fakes.py`) for the domain ports -- no AWS clients, no network. |
| `integration/`        | Tests exercising real infrastructure adapters and full Lambda handlers against mocked AWS services via [`moto`](https://github.com/getmoto/moto). Verifies DynamoDB item shapes, S3 interactions, Step Functions execution naming/idempotency, and the complete handler composition root (`integration/api/handlers/`) without touching real AWS accounts. |

## Conventions

- Test modules mirror the package path of the code under test:
  `src/batch_inference_platform/domain/entities/job.py` →
  `tests/unit/domain/entities/test_job.py`.
- Tests follow Arrange-Act-Assert with one behavioral assertion focus per test.
- Coverage threshold is enforced at 85% (see `[tool.coverage.report]` in
  `pyproject.toml`) and checked in CI (Phase 4).
- No test may call real AWS APIs. `moto` mocks are the only sanctioned way to
  exercise AWS SDK calls in this suite.

See [`docs/standards/coding-standards.md`](../docs/standards/coding-standards.md#testing)
for the full testing standard.
