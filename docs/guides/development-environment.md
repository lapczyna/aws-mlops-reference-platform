# Development Environment

This guide gets a new contributor from a clean checkout to a passing test
suite and working pre-commit hooks. It does not cover deploying to AWS --
see the [deployment strategy](deployment-strategy.md) for that (concrete
deployment steps land with the SAM template in Phase 2).

## Prerequisites

| Tool                | Minimum version | Why                                                              |
| --------------------- | ---------------- | ------------------------------------------------------------------- |
| Python                 | 3.12            | Language runtime; matches the Lambda runtime version exactly.       |
| Docker                 | latest          | Required by `sam build` (container builds) and `sam local invoke`.  |
| AWS SAM CLI             | 1.120+          | Local build/invoke/test and deployment (Phase 2 onward).            |
| AWS CLI                 | v2              | Credentials and ad-hoc AWS interaction.                             |
| git                     | 2.40+           | Version control.                                                     |
| make                    | any             | Convenience task runner (`Makefile`); optional if you run tool commands directly. |

Python version pinning matters here specifically because Lambda's
`python3.12` managed runtime must match the interpreter used locally --
a mismatch is a common source of "works on my machine" bugs with native
extensions (e.g. compiled dependencies in `boto3`/`pydantic`).

## Setup

```bash
git clone <repo-url>
cd aws-mlops-reference-platform

# Create a virtual environment and install the package with dev extras
make install

# Install git hooks (Ruff, Black, mypy, and hygiene checks run pre-commit)
make install-hooks
```

Equivalent manual steps (what `make install` does), useful on machines
without `make` (e.g. plain Windows PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\pre-commit install
```

## Everyday commands

| Command             | What it does                                              |
| --------------------- | -------------------------------------------------------------- |
| `make format`          | Auto-formats `src/` and `tests/` with Black and Ruff's fixer.  |
| `make lint`             | Checks formatting and lint rules without modifying files (what CI runs). |
| `make typecheck`        | Runs `mypy --strict` against `src/`.                          |
| `make test`             | Runs the pytest suite.                                         |
| `make test-cov`         | Runs tests with a coverage report (fails under 85%).            |
| `make clean`            | Removes cache/coverage artifacts.                                |

Run `make help` for the full, self-documenting list.

## Editor configuration

`.editorconfig` at the repo root pins indentation and line-ending rules
recognized by all major editors. If your editor doesn't auto-detect it,
install an EditorConfig plugin rather than overriding these settings
manually -- consistency here avoids noisy whitespace-only diffs.

Recommended (not required) VS Code extensions: Python, Ruff, Mypy Type
Checker, and the AWS Toolkit (for SAM template authoring support once Phase
2 lands).

## Working with AWS services locally

This project has no local emulation of DynamoDB/S3/Step Functions running
by default -- it uses **`moto`** to mock AWS APIs in-process for both unit
and integration tests, which is faster and more deterministic than running
LocalStack or DynamoDB Local containers, and requires no Docker for the test
suite itself (Docker is still needed for `sam build`/`sam local invoke`).

```python
# tests/integration/infrastructure/persistence/test_dynamodb_job_repository.py
def test_create_then_get_round_trips_all_fields(self, jobs_table: Table) -> None:
    repository = DynamoDbJobRepository(jobs_table)
    ...  # real boto3 calls hit moto's in-memory AWS, not a real account
```

No test in this repository is permitted to call real AWS APIs. If a test
needs credentials to even instantiate a boto3 client, that is a signal it
is missing its `@mock_aws` decorator, not a signal to configure real
credentials for CI.

## Pre-commit hooks

`.pre-commit-config.yaml` runs on every `git commit`:

1. Whitespace/EOF/YAML/JSON/TOML hygiene checks.
2. Secret-key detection (`detect-private-key`).
3. Ruff (lint + autofix).
4. Black (format check).
5. mypy (strict type check, excluding `tests/`).

A commit that fails any hook is blocked locally, before it ever reaches CI
-- CI (Phase 4) re-runs the same checks as a backstop, not as the first
line of defense.

## Troubleshooting

| Symptom                                     | Likely cause                                                        |
| ---------------------------------------------- | ----------------------------------------------------------------------- |
| `mypy` reports errors only in CI, not locally   | Local `.venv` has a stale `boto3-stubs` version; re-run `make install`. |
| `pre-commit` hook not running                    | `make install-hooks` was never run, or you cloned into a directory without `.git` hooks support (e.g. some network drives). |
| `sam build` fails with a Docker error             | Docker Desktop isn't running, or (on Windows) file sharing isn't enabled for the repo's drive. |
