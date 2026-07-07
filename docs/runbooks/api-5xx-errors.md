# Runbook: API Gateway 5xx Errors

## Trigger

`batch-inference-<env>-api-5xx` alarm: API Gateway's `5XXError` metric hit
1 or more in a 5-minute window. Unlike the 4xx family (which mostly means a
caller sent something invalid and is expected background noise), any 5xx
means the platform itself failed to handle a valid request.

## Investigation

1. **Check the API access logs** for the specific failing requests
   (log group: `/aws/apigateway/batch-inference-<env>-api-access`):
   ```
   fields @timestamp, requestId, httpMethod, routeKey, status, integrationErrorMessage
   | filter status >= 500
   | sort @timestamp desc
   | limit 50
   ```
   `integrationErrorMessage` often names the failure mode directly (e.g. a
   Lambda timeout, a permissions error).

2. **Check whether `batch-inference-<env>-lambda-errors` also fired.** If
   both alarms are active together, the 5xx is very likely a Lambda
   exception surfacing as a 500 -- go straight to that function's log
   group (`/aws/lambda/batch-inference-<env>-fn-<name>`) and search for the
   stack trace using the `requestId` from step 1 (Powertools'
   `inject_lambda_context` puts `request_id`/`cold_start` on every log
   line).

3. **If neither the Lambda logs nor access logs show an application-level
   exception**, suspect infrastructure:
   - **A recent deploy.** Check `git log` on `main` and recent
     `deploy-staging.yml`/`deploy-prod.yml` runs in GitHub Actions --
     did a change to IAM policies, environment variables, or the API
     Gateway configuration itself land right before the alarm fired?
   - **An IAM permission regression.** A `403`/`AccessDenied` from a
     downstream AWS call inside a handler surfaces to the client as a
     500. Check the specific function's CloudWatch Logs for
     `AccessDeniedException` and cross-reference its IAM role's policy
     in `template.yaml` against what it's now trying to do.
   - **An AWS service-level issue.** Check the
     [AWS Health Dashboard](https://health.aws.amazon.com/health/status)
     for the account's region before assuming it's this platform's bug.

4. **If a bad deploy is confirmed**, follow
   [deployment-rollback.md](deployment-rollback.md).

5. **Confirm resolution** with `scripts/smoke_test.sh <env>` once a fix is
   deployed, not just by watching the alarm return to OK (OK only means no
   *new* 5xx in the last evaluation period, not that the root cause is
   fixed).
