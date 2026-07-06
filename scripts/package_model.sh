#!/usr/bin/env bash
# Trains the Iris model and uploads the packaged artifact to a deployed
# environment's model artifacts bucket. See ml/train.py and ADR-0009.
#
# Usage: scripts/package_model.sh <environment> [s3-key]
#   environment  dev | staging | prod -- must already be deployed (template.yaml)
#   s3-key       defaults to model/model.tar.gz (the ModelArtifactS3Key default)
set -euo pipefail

ENVIRONMENT="${1:?Usage: scripts/package_model.sh <environment> [s3-key]}"
S3_KEY="${2:-model/model.tar.gz}"
STACK_NAME="batch-inference-${ENVIRONMENT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/ml/build"

echo "Training and packaging the model artifact..."
python "${REPO_ROOT}/ml/train.py" --output-dir "${BUILD_DIR}"

echo "Resolving the model artifacts bucket for stack '${STACK_NAME}'..."
BUCKET_NAME="$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='ModelArtifactsBucketName'].OutputValue" \
  --output text)"

if [[ -z "${BUCKET_NAME}" || "${BUCKET_NAME}" == "None" ]]; then
  echo "Could not resolve ModelArtifactsBucketName from stack '${STACK_NAME}'. Has it been deployed? See docs/guides/deployment-guide.md." >&2
  exit 1
fi

echo "Uploading to s3://${BUCKET_NAME}/${S3_KEY}..."
aws s3 cp "${BUILD_DIR}/model.tar.gz" "s3://${BUCKET_NAME}/${S3_KEY}"

echo "Done. The next SageMaker Batch Transform job for '${STACK_NAME}' will use this artifact."
