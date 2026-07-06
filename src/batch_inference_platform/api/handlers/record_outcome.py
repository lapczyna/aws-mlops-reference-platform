"""Step Functions tasks: RecordSuccess / RecordFailure -- Lambda handler.

Invoked directly by Step Functions for both terminal states in
`statemachine/job_orchestration.asl.json`. Every reachable path in the ASL
routes through this handler before the execution ends, so it is the one
place a job's DynamoDB record is guaranteed to reach a terminal status.
"""

from __future__ import annotations

from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from batch_inference_platform.application.use_cases.record_job_outcome import RecordJobOutcome
from batch_inference_platform.infrastructure.persistence.dynamodb_job_repository import (
    DynamoDbJobRepository,
)
from batch_inference_platform.shared.config import get_settings
from batch_inference_platform.shared.logging import get_logger
from batch_inference_platform.shared.metrics import get_metrics

logger = get_logger(service="record-outcome")
metrics = get_metrics(service="record-outcome")

_settings = get_settings()
_job_repository = DynamoDbJobRepository(boto3.resource("dynamodb").Table(_settings.jobs_table_name))
_use_case = RecordJobOutcome(_job_repository, metrics)


@logger.inject_lambda_context(log_event=True)
@metrics.log_metrics(capture_cold_start_metric=True)  # type: ignore[untyped-decorator]
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Step Functions task entry point for the RecordSuccess/RecordFailure states."""
    logger.append_keys(job_id=event.get("job_id"))
    _use_case.execute(
        job_id_value=event["job_id"],
        status=event["status"],
        error_code=event.get("error_code"),
        error_cause=event.get("error_cause"),
    )
    logger.info("Job outcome recorded", extra={"status": event["status"]})
    return {"acknowledged": True}
