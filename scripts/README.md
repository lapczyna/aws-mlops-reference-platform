# Scripts

Operational and developer-convenience scripts that don't belong in application
code or CI workflow YAML. Populated starting in Phase 2 (deployment helpers)
and Phase 4 (cleanup / cost-report automation).

## Planned contents

| Script                     | Purpose                                                              | Phase |
| --------------------------- | ----------------------------------------------------------------------- | ----- |
| `package_model.sh`           | Trains the Iris model and uploads `model.tar.gz` to the artifacts bucket. | 2 |
| `deploy.sh`                  | Wraps `sam build` / `sam deploy` with environment-specific config guards. | 2 |
| `smoke_test.sh`               | Post-deploy smoke test: submits a small batch job end-to-end and checks the result. | 3 |
| `estimate_cost.py`            | Renders a cost estimate for a given monthly request volume using the pricing model in the cost guide. | 4 |
| `teardown.sh`                 | Safely tears down a named environment stack, emptying buckets first. | 4 |

Every script must be idempotent and safe to re-run, and must never assume it
is running in an interactive shell (CI compatibility).
