# Disaster Recovery Guide

## Scope

This platform is deployed to a **single AWS region** per environment
(`dev`/`staging`/`prod` are separate stacks, but each lives in one region --
see [deployment strategy](deployment-strategy.md)). This guide covers
recovery from data loss, accidental deletion, and a bad deploy within that
region. It explicitly does **not** cover a full AWS region outage --
multi-region DR is a deliberately deferred future enhancement (see the
[roadmap](../roadmap.md)), not an oversight.

## Recovery objectives

| Scenario                              | RTO (time to recover)          | RPO (acceptable data loss)                |
| ------------------------------------------ | ---------------------------------- | ------------------------------------------------ |
| Infrastructure lost/corrupted (stack deleted, misconfigured) | ~15-30 minutes (redeploy `template.yaml` from source; it's the same command as any deploy) | Zero for infrastructure itself -- it's fully defined in source control. |
| Job metadata (DynamoDB) corrupted or accidentally deleted     | Minutes to restore a point-in-time table | Up to a few seconds (DynamoDB PITR is continuous, restorable to any second in the last 35 days). |
| Dataset/results objects (S3) accidentally deleted               | Minutes (undelete a version)     | Zero -- versioning means a "delete" is reversible; only a bucket-level deletion combined with lifecycle expiry could actually lose data, and lifecycle rules only expire *old* objects, not recent ones. |
| Model artifact lost                                                | Minutes (re-run `scripts/package_model.sh`) | Zero from a business standpoint -- the artifact is reproducible from `ml/train.py` (fixed random seed) and the artifacts bucket has `DeletionPolicy: Retain`. |
| A job actively `PROCESSING` at the moment of an incident              | N/A -- see below                  | That specific job's in-flight execution state is not recoverable; the client resubmits. |

## What's already built in (no action needed to enable)

- **DynamoDB point-in-time recovery** is enabled on the `Jobs` table
  (`PointInTimeRecoverySpecification` in `template.yaml`) -- continuous
  backups, restorable to any point in the last 35 days.
- **S3 versioning** is enabled on all three buckets -- an accidental
  `DeleteObject` adds a delete marker, it doesn't destroy the underlying
  version; a bad overwrite is recoverable the same way.
- **The model artifacts bucket has `DeletionPolicy: Retain`** -- deleting
  the CloudFormation stack does not delete this bucket (see
  [ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md)).
- **Infrastructure is fully reproducible from source.** There is no
  console-managed resource this platform depends on (per the "no ClickOps"
  principle in [deployment-strategy.md](deployment-strategy.md)) other than
  the two one-time account-level bootstrap stacks
  (`bootstrap/api-gateway-account-settings.yaml`,
  `bootstrap/github-oidc-deploy-role.yaml`), which are equally reproducible.

## Restore procedures

### Full environment stack lost or corrupted

```bash
sam build --use-container
sam deploy --config-env <env>
scripts/package_model.sh <env>          # model artifact bucket survives (Retain), but re-run is cheap and safe
scripts/smoke_test.sh <env>              # confirm it actually works before declaring recovery complete
```

### DynamoDB table needs restoring to a prior point in time

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name batch-inference-<env>-table-jobs \
  --target-table-name batch-inference-<env>-table-jobs-restored \
  --restore-date-time <ISO-8601-timestamp>
```

Restoring in place isn't possible (DynamoDB PITR always restores to a *new*
table name) -- after validating the restored table's contents, you would
need to either point the stack's Lambda functions at the restored table
name (a template parameter change) or `BatchWriteItem` the recovered data
back into the live table. Neither is scripted today; treat this as a
deliberate, supervised incident-response action.

### A specific S3 object was deleted or overwritten

```bash
# List versions to find the one you want back
aws s3api list-object-versions --bucket <bucket> --prefix <key>

# Removing the delete marker restores the previous version as current
aws s3api delete-object --bucket <bucket> --key <key> --version-id <delete-marker-version-id>
```

### The model artifact is lost or wrong

```bash
scripts/package_model.sh <env>
```

Deterministic given the fixed random seed in `ml/train.py` -- this is a
full recovery, not a best-effort one.

## What is not recoverable

A job that was actively `PROCESSING` (its SageMaker Batch Transform job
mid-flight) at the moment of an incident cannot be resumed -- Step
Functions executions and Batch Transform jobs are not checkpointed
mid-run. Its `job_id` will either complete normally if the incident didn't
affect its specific execution, or the client should treat a job that
never reaches a terminal state within a reasonable window as failed and
resubmit (see
[job-stuck-in-processing.md](../runbooks/job-stuck-in-processing.md)).
This is an accepted trade-off of the architecture's async, stateless-retry
design (per [ADR-0008](../adr/0008-asynchronous-job-processing-pattern.md))
rather than a gap specific to disaster scenarios.

## Testing this guide

None of the above has been exercised as a scheduled "game day" drill in
this repository -- these are documented, plausible procedures based on the
AWS APIs involved, not battle-tested runbooks. Before relying on this guide
for a real production workload, actually run each restore procedure once
against a disposable `dev`-like stack and correct anything that doesn't
match reality. Treat this section itself as a backlog item, not a
completed control.
