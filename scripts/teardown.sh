#!/usr/bin/env bash
# Tears down an environment stack, automating the one manual step that
# otherwise blocks `sam delete`: emptying the versioned S3 buckets
# CloudFormation refuses to delete non-empty. See the "Tearing down an
# environment" section of docs/guides/deployment-guide.md, which this
# script automates.
#
# Usage: scripts/teardown.sh <environment> [--purge-model-artifacts]
#   environment                dev | staging | prod
#   --purge-model-artifacts    also empty and delete the model artifacts
#                              bucket (DeletionPolicy: Retain -- kept by
#                              default so a teardown can never silently
#                              destroy a trained model).
#
# `sam delete` itself still prompts for confirmation before deleting
# anything -- this script does not suppress that.
set -euo pipefail

ENVIRONMENT="${1:?Usage: scripts/teardown.sh <environment> [--purge-model-artifacts]}"
PURGE_MODEL_ARTIFACTS=false
if [[ "${2:-}" == "--purge-model-artifacts" ]]; then
  PURGE_MODEL_ARTIFACTS=true
fi

STACK_NAME="batch-inference-${ENVIRONMENT}"

stack_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

empty_bucket() {
  local bucket="$1"
  echo "Emptying all versions and delete markers from s3://${bucket} ..."
  aws s3api list-object-versions --bucket "$bucket" --output json \
    | jq -c '(.Versions // []) + (.DeleteMarkers // []) | .[] | {Key, VersionId}' \
    | while read -r obj; do
        key=$(jq -r '.Key' <<<"$obj")
        version=$(jq -r '.VersionId' <<<"$obj")
        aws s3api delete-object --bucket "$bucket" --key "$key" --version-id "$version" >/dev/null
      done
}

echo "Resolving bucket names for stack '${STACK_NAME}'..."
DATASETS_BUCKET="$(stack_output DatasetsBucketName)"
RESULTS_BUCKET="$(stack_output ResultsBucketName)"

if [[ -z "$DATASETS_BUCKET" || "$DATASETS_BUCKET" == "None" ]]; then
  echo "Could not resolve stack outputs for '${STACK_NAME}'. Already deleted, or never deployed?" >&2
  exit 1
fi

empty_bucket "$DATASETS_BUCKET"
empty_bucket "$RESULTS_BUCKET"

if [[ "$PURGE_MODEL_ARTIFACTS" == true ]]; then
  MODEL_ARTIFACTS_BUCKET="$(stack_output ModelArtifactsBucketName)"
  echo "--purge-model-artifacts set: emptying s3://${MODEL_ARTIFACTS_BUCKET} too."
  empty_bucket "$MODEL_ARTIFACTS_BUCKET"
  aws s3api delete-bucket --bucket "$MODEL_ARTIFACTS_BUCKET" || true
else
  echo "Leaving the model artifacts bucket in place (DeletionPolicy: Retain)."
  echo "Pass --purge-model-artifacts to also remove it."
fi

echo "Buckets emptied. Deleting the stack (sam will still ask for confirmation)..."
sam delete --config-env "$ENVIRONMENT"
