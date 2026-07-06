# Scripts

Operational and developer-convenience scripts that don't belong in application
code or CI workflow YAML.

## Contents

| Script                     | Purpose                                                              | Status |
| --------------------------- | ----------------------------------------------------------------------- | ----- |
| `package_model.sh`           | Trains the Iris model (`ml/train.py`) and uploads `model.tar.gz` to a deployed environment's model artifacts bucket. | Delivered (Phase 3) |
| `smoke_test.sh`               | Post-deploy smoke test: submits a small batch job end-to-end and checks the result. | Planned (Phase 4) |
| `estimate_cost.py`            | Renders a cost estimate for a given monthly request volume using the pricing model in the cost guide. | Planned (Phase 4) |
| `teardown.sh`                 | Safely tears down a named environment stack, emptying buckets first. | Planned (Phase 4) |

`sam build` / `sam deploy --config-env <env>` need no wrapper script --
`samconfig.toml` already carries the per-environment configuration (see the
[deployment guide](../docs/guides/deployment-guide.md)).

Every script must be idempotent and safe to re-run, and must never assume it
is running in an interactive shell (CI compatibility).
