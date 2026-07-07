# Runbook: Rolling Back a Deployment

## Two different situations, two different responses

**The deployment itself failed** (CloudFormation `UPDATE_ROLLBACK_COMPLETE`
or similar): CloudFormation already auto-rolled back to the last known-good
state by default -- there is usually nothing left to do except read the
stack events (`aws cloudformation describe-stack-events --stack-name
batch-inference-<env>`) to understand *why* the update failed before
retrying.

**The deployment succeeded but the new code is behaviorally wrong**
(elevated error rate, wrong predictions, etc.): this is the harder case,
covered below. CloudFormation has no "undo my last successful deploy"
button -- rolling back means *deploying the previous good version forward*,
same as any other deploy.

## Rolling forward to a previous good version

1. **Identify the last good tag** (for prod) or commit (for staging):
   ```bash
   git tag --sort=-creatordate | head -5
   git log --oneline -10 main
   ```

2. **Staging** (deploys automatically from `main`): revert the bad commit
   on `main` and push -- `deploy-staging.yml` picks it up automatically
   once `ci.yml` passes on the revert:
   ```bash
   git revert <bad-commit-sha>
   git push origin main
   ```
   For an urgent rollback, `sam deploy --config-env staging` from a
   checkout of the last good commit works immediately without waiting for
   CI, at the cost of bypassing the normal gate -- use judgment.

3. **Prod** (deploys from a tag): tag the last good commit as a new patch
   version and push the tag -- `deploy-prod.yml` builds and deploys that
   exact commit fresh (see [ADR-0014](../adr/0014-github-oidc-for-cicd.md)
   for why prod always rebuilds from source rather than re-promoting a
   cached artifact):
   ```bash
   git tag -a v1.2.4 <last-good-commit-sha> -m "Rollback of v1.2.3"
   git push origin v1.2.4
   ```

## Data considerations

DynamoDB is schemaless -- rolling Lambda code back and forth doesn't
require a migration either direction *unless* the bad deploy also changed
the shape of items written to the `Jobs` table (e.g. renamed an attribute).
If it did:

- Check whether the bad version wrote items in a shape the rolled-back
  code can't read. `GetJobStatus`/`GetJobResults` will raise on a
  malformed item rather than silently misbehave (Pydantic/dataclass
  validation in the domain layer) -- watch for a fresh wave of 5xx/404
  errors on jobs created *during* the bad deploy window even after rolling
  back the code.
- There is no automated backfill/migration tooling in this platform for
  that scenario today -- treat it as an incident requiring a one-off
  script against the affected `job_id`s (identifiable by `created_at`
  falling in the bad-deploy window), not a routine rollback step.

## After rolling back

1. Run `scripts/smoke_test.sh <env>` to confirm the rolled-back version
   actually works end to end, not just that the deploy succeeded.
2. Do not delete the bad tag/commit -- keep it for post-incident analysis.
3. File the incident and root-cause it before re-attempting the change
   that caused the rollback.
