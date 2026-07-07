#!/usr/bin/env bash
# Post-deploy smoke test: submits a real batch inference job end to end
# against a deployed environment and confirms it completes. Automates the
# manual walkthrough in the "Verifying the deployment" section of
# docs/guides/deployment-guide.md.
#
# Requires scripts/package_model.sh to have been run against this
# environment at least once (otherwise the job will reach FAILED, which
# this script correctly reports as a failure).
#
# Usage: scripts/smoke_test.sh <environment> [max-wait-seconds]
set -euo pipefail

ENVIRONMENT="${1:?Usage: scripts/smoke_test.sh <environment> [max-wait-seconds]}"
MAX_WAIT_SECONDS="${2:-300}"
STACK_NAME="batch-inference-${ENVIRONMENT}"

API_BASE_URL="$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiBaseUrl'].OutputValue" \
  --output text)"

if [[ -z "$API_BASE_URL" || "$API_BASE_URL" == "None" ]]; then
  echo "Could not resolve ApiBaseUrl from stack '${STACK_NAME}'. Has it been deployed?" >&2
  exit 1
fi

echo "Target: ${API_BASE_URL}"

echo "1. Requesting a presigned upload URL..."
PRESIGN_RESPONSE="$(curl -sf -X POST "${API_BASE_URL}/datasets/upload-url")"
JOB_ID="$(jq -r '.job_id' <<<"$PRESIGN_RESPONSE")"
UPLOAD_URL="$(jq -r '.upload_url' <<<"$PRESIGN_RESPONSE")"
echo "   job_id=${JOB_ID}"

echo "2. Uploading a sample Iris dataset (3 rows)..."
printf '5.1,3.5,1.4,0.2\n6.7,3.1,4.7,1.5\n6.3,3.3,6.0,2.5\n' \
  | curl -sf -X PUT --data-binary @- "$UPLOAD_URL"

echo "3. Submitting the job..."
SUBMIT_RESPONSE="$(curl -sf -X POST "${API_BASE_URL}/jobs" -d "{\"job_id\": \"${JOB_ID}\"}")"
echo "   ${SUBMIT_RESPONSE}"

echo "4. Polling status (up to ${MAX_WAIT_SECONDS}s)..."
elapsed=0
interval=5
status="UNKNOWN"
while (( elapsed < MAX_WAIT_SECONDS )); do
  status="$(curl -sf "${API_BASE_URL}/jobs/${JOB_ID}" | jq -r '.status')"
  echo "   [${elapsed}s] status=${status}"
  if [[ "$status" == "COMPLETED" || "$status" == "FAILED" ]]; then
    break
  fi
  sleep "$interval"
  elapsed=$((elapsed + interval))
done

if [[ "$status" != "COMPLETED" ]]; then
  echo "FAIL: job did not complete successfully (final status: ${status})." >&2
  echo "If this is a fresh environment, confirm scripts/package_model.sh has been run." >&2
  exit 1
fi

echo "5. Fetching results..."
RESULTS_RESPONSE="$(curl -sf "${API_BASE_URL}/jobs/${JOB_ID}/results")"
echo "   ${RESULTS_RESPONSE}"

echo "PASS: job ${JOB_ID} completed and results are retrievable."
