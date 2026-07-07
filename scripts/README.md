# Scripts

Operational and developer-convenience scripts that don't belong in application
code or CI workflow YAML.

## Contents

| Script                     | Purpose                                                              |
| --------------------------- | ----------------------------------------------------------------------- |
| `package_model.sh`           | Trains the Iris model (`ml/train.py`) and uploads `model.tar.gz` to a deployed environment's model artifacts bucket. |
| `smoke_test.sh`               | Post-deploy smoke test: submits a real batch job end-to-end (upload -> submit -> poll -> results) and fails loudly if it doesn't reach `COMPLETED`. |
| `estimate_cost.py`            | Renders a monthly cost estimate for a given job volume; see [`docs/guides/cost-guide.md`](../docs/guides/cost-guide.md), which is generated from this script's output. |
| `teardown.sh`                 | Tears down a named environment stack, emptying its versioned S3 buckets first (the one manual step that otherwise blocks `sam delete`). |

`sam build` / `sam deploy --config-env <env>` need no wrapper script --
`samconfig.toml` already carries the per-environment configuration (see the
[deployment guide](../docs/guides/deployment-guide.md)).

Every script must be idempotent and safe to re-run, and must never assume it
is running in an interactive shell (CI compatibility).
