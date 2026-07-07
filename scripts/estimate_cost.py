"""Rough monthly cost estimate for a given batch inference job volume.

Usage:
    python scripts/estimate_cost.py --jobs-per-month 1000

This is an illustrative planning tool, not a quote: it uses approximate,
hand-maintained list prices (US East (N. Virginia), on-demand, no committed-
use discounts, no free-tier credits) and simplifying assumptions about
request/invocation counts per job, documented inline below. For an
authoritative number, use the AWS Pricing Calculator or your account's
Cost Explorer against real usage. See docs/guides/cost-guide.md, which
this script's output feeds directly into.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Assumptions -- all approximate, all easy to override on the command line
# or by editing the constants below. Keep this in sync with
# docs/guides/cost-guide.md if you change them.
# ---------------------------------------------------------------------------

API_REQUESTS_PER_JOB = 5  # presign + submit + 2 status polls + results
LAMBDA_INVOCATIONS_PER_JOB = (
    5  # presign, submit, validate_input, record_outcome, +1 status/results poll
)
LAMBDA_AVG_DURATION_MS = 300
LAMBDA_MEMORY_MB = 256
STATE_TRANSITIONS_PER_JOB = (
    5  # ValidateInput, CheckInputValid, MarkProcessing, RunBatchTransformJob, RecordSuccess
)
TRANSFORM_JOB_MINUTES = 4.0  # small dataset on a single ml.m5.large instance
DYNAMODB_WRITES_PER_JOB = 3  # create, MarkProcessing, RecordOutcome
DYNAMODB_READS_PER_JOB = 2  # 2 status polls

# US East (N. Virginia) on-demand list prices, approximate as of this
# writing -- re-verify against current AWS pricing before relying on this
# for a real budget decision.
PRICE_API_GATEWAY_PER_MILLION_REQUESTS = 3.50
PRICE_LAMBDA_PER_MILLION_REQUESTS = 0.20
PRICE_LAMBDA_PER_GB_SECOND_ARM64 = 0.0000133334
PRICE_STEP_FUNCTIONS_PER_1K_TRANSITIONS = 0.025
PRICE_SAGEMAKER_ML_M5_LARGE_PER_HOUR = 0.115
PRICE_DYNAMODB_PER_MILLION_WRITE_REQUEST_UNITS = 1.25
PRICE_DYNAMODB_PER_MILLION_READ_REQUEST_UNITS = 0.25
PRICE_CLOUDWATCH_ALARM_PER_MONTH = 0.10
NUM_ALARMS = 6
PRICE_CLOUDWATCH_LOGS_PER_GB_INGESTED = 0.50
ASSUMED_LOG_GB_PER_1K_JOBS = 0.05  # structured JSON logs across 6 functions + Step Functions


@dataclass
class LineItem:
    service: str
    monthly_cost: float
    basis: str


def estimate(jobs_per_month: int) -> list[LineItem]:
    million = 1_000_000
    thousand = 1_000

    api_requests = jobs_per_month * API_REQUESTS_PER_JOB
    api_cost = (api_requests / million) * PRICE_API_GATEWAY_PER_MILLION_REQUESTS

    lambda_invocations = jobs_per_month * LAMBDA_INVOCATIONS_PER_JOB
    lambda_request_cost = (lambda_invocations / million) * PRICE_LAMBDA_PER_MILLION_REQUESTS
    gb_seconds = lambda_invocations * (LAMBDA_MEMORY_MB / 1024) * (LAMBDA_AVG_DURATION_MS / 1000)
    lambda_compute_cost = gb_seconds * PRICE_LAMBDA_PER_GB_SECOND_ARM64
    lambda_cost = lambda_request_cost + lambda_compute_cost

    transitions = jobs_per_month * STATE_TRANSITIONS_PER_JOB
    step_functions_cost = (transitions / thousand) * PRICE_STEP_FUNCTIONS_PER_1K_TRANSITIONS

    transform_hours = jobs_per_month * (TRANSFORM_JOB_MINUTES / 60)
    sagemaker_cost = transform_hours * PRICE_SAGEMAKER_ML_M5_LARGE_PER_HOUR

    writes = jobs_per_month * DYNAMODB_WRITES_PER_JOB
    reads = jobs_per_month * DYNAMODB_READS_PER_JOB
    dynamodb_cost = (writes / million) * PRICE_DYNAMODB_PER_MILLION_WRITE_REQUEST_UNITS + (
        reads / million
    ) * PRICE_DYNAMODB_PER_MILLION_READ_REQUEST_UNITS

    log_gb = (jobs_per_month / thousand) * ASSUMED_LOG_GB_PER_1K_JOBS
    cloudwatch_logs_cost = log_gb * PRICE_CLOUDWATCH_LOGS_PER_GB_INGESTED
    cloudwatch_alarms_cost = NUM_ALARMS * PRICE_CLOUDWATCH_ALARM_PER_MONTH
    cloudwatch_cost = cloudwatch_logs_cost + cloudwatch_alarms_cost

    return [
        LineItem("API Gateway", api_cost, f"{api_requests:,} requests"),
        LineItem(
            "Lambda", lambda_cost, f"{lambda_invocations:,} invocations, {gb_seconds:,.1f} GB-s"
        ),
        LineItem("Step Functions", step_functions_cost, f"{transitions:,} state transitions"),
        LineItem(
            "SageMaker Batch Transform", sagemaker_cost, f"{transform_hours:,.2f} ml.m5.large hours"
        ),
        LineItem("DynamoDB", dynamodb_cost, f"{writes:,} writes, {reads:,} reads"),
        LineItem("CloudWatch", cloudwatch_cost, f"{NUM_ALARMS} alarms + {log_gb:,.3f} GB logs"),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jobs-per-month",
        type=int,
        default=1000,
        help="Number of batch inference jobs submitted per month (default: 1000)",
    )
    args = parser.parse_args()

    line_items = estimate(args.jobs_per_month)
    total = sum(item.monthly_cost for item in line_items)

    print(f"Estimated monthly cost for {args.jobs_per_month:,} jobs/month")
    print("(US East, on-demand list price):")
    print(f"{'Service':<28}{'Basis':<40}{'Monthly ($)':>12}")
    print("-" * 80)
    for item in line_items:
        print(f"{item.service:<28}{item.basis:<40}{item.monthly_cost:>12.4f}")
    print("-" * 80)
    print(f"{'TOTAL':<68}{total:>12.4f}")
    print()
    print("S3 storage/request costs and KMS costs (if enabled) are omitted -- both")
    print("are negligible at these volumes for small CSV datasets. This is a planning")
    print("estimate, not a quote -- see docs/guides/cost-guide.md.")


if __name__ == "__main__":
    main()
