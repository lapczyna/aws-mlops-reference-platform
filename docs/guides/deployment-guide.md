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

## One-time per account: GitHub Actions OIDC deploy role

Also a singleton, also deployed once, also separate from the environment
stacks for the same reason (see
[ADR-0012](../adr/0012-api-gateway-account-settings-bootstrap.md) and
[ADR-0014](../adr/0014-github-oidc-for-cicd.md)):

```bash
sam deploy \
  --template-file bootstrap/github-oidc-deploy-role.yaml \
  --stack-name github-oidc-deploy-role \
  --parameter-overrides GitHubOrg=<your-github-org-or-user> \
  --capabilities CAPABILITY_NAMED_IAM \
  --resolve-s3
```

Take the `DeployRoleArn` output and set it as the `AWS_DEPLOY_ROLE_ARN`
variable on the `staging` and `prod` GitHub Environments (Settings >
Environments > *environment name* > Environment variables). No AWS access
keys are ever stored in GitHub -- each workflow run assumes this role via a
short-lived OIDC token scoped to this exact repository and ref (`main` for
staging, `v*` tags for prod).

## Continuous deployment

Three workflows in `.github/workflows/` automate the flow described in the
[deployment strategy guide](deployment-strategy.md):

| Workflow               | Trigger                          | Does                                                    |
| ------------------------ | ----------------------------------- | ------------------------------------------------------------ |
| `ci.yml`                  | Every PR, every push to `main`        | Lint, typecheck, test, validate/build the SAM template, train + smoke-test the model. |
| `deploy-staging.yml`       | `ci.yml` succeeding on `main`          | `sam deploy --config-env staging`. |
| `deploy-prod.yml`          | Pushing a `v*.*.*` tag                 | Re-verifies the tagged commit, then `sam deploy --config-env prod` behind the `prod` GitHub Environment's approval gate. |

Cutting a release is therefore: merge to `main` (staging deploys
automatically), confirm it behaves correctly, then `git tag vX.Y.Z && git
push origin vX.Y.Z` to promote the exact same commit to `prod`.

**Manual approval gate note:** `deploy-prod.yml` targets the `prod` GitHub
Environment specifically so a "required reviewers" protection rule can be
attached to it. Like branch protection, environment protection rules on a
*private* repository require GitHub Team/Enterprise (public repos and paid
private plans get it for free) -- see
[ADR-0016](../adr/0016-prod-approval-gate-via-github-environments.md). Until
that's available, `deploy-prod.yml` still only runs on an explicit tag push
(never automatically), which is itself a deliberate, human-initiated
action -- just without a second human's sign-off enforced by GitHub.

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

`prod` deploys go through the `deploy-prod.yml` workflow (tag push), not a
laptop -- see [Continuous deployment](#continuous-deployment) above.
Deploying `prod` by hand with these same commands still works and is
useful for a first manual walkthrough, but isn't the intended steady-state
path.

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

The three S3 buckets are versioned; `DatasetsBucket` and `ResultsBucket`
have `DeletionPolicy: Delete` but CloudFormation cannot delete a non-empty
bucket, so a bare `sam delete` fails on them. Use
[`scripts/teardown.sh`](../../scripts/teardown.sh), which empties both
buckets first and then runs `sam delete` (which still prompts for
confirmation -- this script doesn't suppress that):

```bash
scripts/teardown.sh dev
```

`ModelArtifactsBucket` has `DeletionPolicy: Retain` deliberately -- trained
model artifacts should survive a routine environment teardown, so the
script leaves it alone by default. Pass `--purge-model-artifacts` if you
genuinely want it gone too:

```bash
scripts/teardown.sh dev --purge-model-artifacts
```

## Troubleshooting

| Symptom                                                        | Likely cause                                                                 |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `Layer version ... is not compatible with function's architecture`   | Built without `--use-container`, or Docker wasn't running during the build. Rebuild with Docker up. |
| `CREATE_FAILED` on `ApiAccessLogGroup`/`JobsApi` referencing CloudWatch | The [one-time account bootstrap](#one-time-per-accountregion-api-gateway-cloudwatch-role) hasn't been deployed in this account/region yet. |
| `CREATE_FAILED` on an `AWS::IAM::Role` -- "already exists"             | A previous stack in this account used the same environment name and wasn't fully torn down; check for orphaned roles from a failed `sam delete`. |
| `RunBatchTransformJob` fails with a 404 reading the model artifact       | Run `scripts/package_model.sh <environment>` at least once against this environment -- see [ADR-0009](../adr/0009-sagemaker-model-artifact-parameterization.md). |
