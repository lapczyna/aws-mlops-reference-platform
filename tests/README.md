# Tests

This directory hosts the automated test suite. Test implementation begins in
**Phase 3** alongside the application code it verifies; this scaffold exists
now so tooling (`pytest`, coverage, CI) has a stable target from Phase 1
onward.

## Layout

| Directory           | Purpose                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `unit/`               | Fast, isolated tests with no I/O. Domain and application layers are tested here with plain Python -- no AWS clients, no network. |
| `integration/`        | Tests exercising infrastructure adapters against mocked AWS services via [`moto`](https://github.com/getmoto/moto). Verifies DynamoDB item shapes, S3 interactions, and Step Functions state transitions without touching real AWS accounts. |

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
