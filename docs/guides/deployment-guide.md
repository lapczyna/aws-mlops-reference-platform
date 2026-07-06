# Deployment Guide

Concrete, copy-pasteable steps to deploy this platform's infrastructure. For
*why* the deployment model looks like this (environments, promotion flow,
parameterization philosophy), see the
[deployment strategy guide](deployment-strategy.md) written in Phase 1 --
this document is the "how," that one is the "why."

As of Phase 3, deploying the stack stands up the full architecture with
real application behavior end to end. The one piece that still needs a
manual step after deployment is the trained model artifact -- SageMaker's
`CreateModel` API registers the model's metadata without validating that
the artifact actually exists yet (see
[ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md)), so
run [`scripts/package_model.sh`](../../scripts/package_model.sh) after your
first deploy to a given environment before submitting a real job.

## Prerequisites

- Completed the [development environment setup](development-environment.md).
- **Docker Desktop running.** `sam build` must use `--use-container`
  (already the default via `samconfig.toml`'s `[default.build.parameters]`)
  because the shared Lambda Layer includes `pydantic`, which has a compiled
  (Rust) extension. Building without a container on a non-Linux host, or on
  a host whose CPU architecture doesn't match the Lambda function's
  `arm64` target, silently produces a layer that fails to import at
  runtime. There is no safe way to skip the container build for this
  template.
- An AWS account and credentials with sufficient permissions to create the
  resources in `template.yaml` (IAM roles, Lambda, API Gateway, Step
  Functions, S3, DynamoDB, SageMaker, CloudWatch, KMS if enabled).
- AWS CLI configured (`aws configure` or an SSO profile) for the target
  account/region.

## One-time per account/region: API Gateway CloudWatch role

Deploy the bootstrap stack **once per AWS account and region** before the
first environment deployment (see [ADR-0012](../adr/0012-api-gateway-account-settings-bootstrap.md)
for why this is separate from the main template):

```bash
sam deploy \
  --template-file bootstrap/api-gateway-account-settings.yaml \
  --stack-name apigateway-account-settings \
  --capabilities CAPABILITY_IAM \
  --resolve-s3
```

Skip this if the target account already has an API Gateway CloudWatch Logs
role configured (check the API Gateway console under Settings > Logs; if a
role ARN is already shown, it's already done).

## Deploying an environment

```bash
sam build                              # containerized build, per samconfig.toml
sam deploy --config-env dev            # or: staging / prod
```

The first deploy to a fresh stack name will prompt to save these as future
defaults if you omit `--config-env`; since `samconfig.toml` already defines
`dev`, `staging`, and `prod` config environments with the right stack name,
tags, and parameter overrides for each, `--config-env <name>` is all you
need.

`prod` deploys should go through CI once Phase 4 lands (manual approval
gate); deploying `prod` by hand from a laptop is meant for the reference
architecture's demonstration purposes only.

### What gets created

Review the changeset SAM shows before confirming -- for a first deploy to
`dev` you should see roughly:

- 1 REST API + 1 stage
- 6 Lambda functions + 1 shared Lambda Layer version
- 8 IAM roles (6 functions + the state machine + the SageMaker execution role)
- 1 Step Functions state machine
- 3 S3 buckets + 3 bucket policies
- 1 DynamoDB table
- 1 SageMaker Model
- ~9 CloudWatch Log Groups

### Verifying the deployment

```bash
# Grab the API base URL from stack outputs
aws cloudformation describe-stacks \
  --stack-name batch-inference-dev \
  --query "Stacks[0].Outputs"

# 1. Get a presigned upload URL and job id
curl -s -X POST "<ApiBaseUrl>/datasets/upload-url" | tee /tmp/presign.json

# 2. Upload a small CSV of Iris feature rows (no header) to the returned URL
JOB_ID=$(jq -r .job_id /tmp/presign.json)
UPLOAD_URL=$(jq -r .upload_url /tmp/presign.json)
printf '5.1,3.5,1.4,0.2\n6.7,3.1,4.7,1.5\n' | curl -s -X PUT --data-binary @- "$UPLOAD_URL"

# 3. Submit the job
curl -s -X POST "<ApiBaseUrl>/jobs" -d "{\"job_id\": \"$JOB_ID\"}"

# 4. Poll status, then fetch results once COMPLETED
curl -s "<ApiBaseUrl>/jobs/$JOB_ID"
curl -s "<ApiBaseUrl>/jobs/$JOB_ID/results"
```

Until [`scripts/package_model.sh`](../../scripts/package_model.sh) has been
run at least once against this environment, step 3's Step Functions
execution will reach `RunBatchTransformJob` and fail there -- the model
artifact doesn't exist yet. Everything up to and including `ValidateInput`
and the `MarkProcessing` DynamoDB transition should still succeed, which is
enough to confirm the API/Lambda/Step Functions/DynamoDB wiring is correct
before the model is in place.

## Region other than us-east-1

Override `SklearnContainerImage` with the correct region's scikit-learn
container URI (see the parameter description in `template.yaml` and
[ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md)), and
update the `region` field in the relevant `samconfig.toml` environment
section.

## Tearing down an environment

```bash
sam delete --config-env dev
```

The three S3 buckets are versioned; `DatasetsBucket` and `ResultsBucket`
have `DeletionPolicy: Delete` but CloudFormation cannot delete a
non-empty bucket. If `sam delete` fails on a bucket, empty all versions
first:

```bash
aws s3api list-object-versions --bucket <bucket-name> --output json \
  | jq -r '.Versions[]?, .DeleteMarkers[]? | "\(.Key) \(.VersionId)"' \
  | while read -r key version; do
      aws s3api delete-object --bucket <bucket-name> --key "$key" --version-id "$version"
    done
sam delete --config-env dev
```

`ModelArtifactsBucket` has `DeletionPolicy: Retain` deliberately -- trained
model artifacts should survive an environment teardown. Delete it
explicitly if you really want to remove it.

Fully automated, safe-by-default cleanup (emptying buckets automatically as
part of `sam delete`) is planned as Phase 4 tooling -- see
[`scripts/README.md`](../../scripts/README.md).

## Troubleshooting

| Symptom                                                        | Likely cause                                                                 |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `Layer version ... is not compatible with function's architecture`   | Built without `--use-container`, or Docker wasn't running during the build. Rebuild with Docker up. |
| `CREATE_FAILED` on `ApiAccessLogGroup`/`JobsApi` referencing CloudWatch | The [one-time account bootstrap](#one-time-per-accountregion-api-gateway-cloudwatch-role) hasn't been deployed in this account/region yet. |
| `CREATE_FAILED` on an `AWS::IAM::Role` -- "already exists"             | A previous stack in this account used the same environment name and wasn't fully torn down; check for orphaned roles from a failed `sam delete`. |
| `RunBatchTransformJob` fails with a 404 reading the model artifact       | Run `scripts/package_model.sh <environment>` at least once against this environment -- see [ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md). |
