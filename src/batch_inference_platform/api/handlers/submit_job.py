"""POST /jobs -- Lambda handler.

See docs/architecture/sequence-diagrams.md#2-batch-job-submission.
"""

from __future__ import annotations

from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from batch_inference_platform.application.dto.submit_job import SubmitJobRequest
from batch_inference_platform.application.use_cases.submit_batch_job import SubmitBatchJob
from batch_inference_platform.domain.exceptions.job_exceptions import InvalidDatasetError
from batch_inference_platform.infrastructure.orchestration.stepfunctions_job_orchestrator import (
    StepFunctionsJobOrchestrator,
)
from batch_inference_platform.infrastructure.persistence.dynamodb_job_repository import (
    DynamoDbJobRepository,
)
from batch_inference_platform.infrastructure.storage.s3_dataset_storage import S3DatasetStorage
from batch_inference_platform.shared.config import get_settings
from batch_inference_platform.shared.http import json_response
from batch_inference_platform.shared.logging import get_logger

logger = get_logger(service="submit-job")

_settings = get_settings()
if not _settings.state_machine_arn:
    raise RuntimeError("STATE_MACHINE_ARN is not configured for the SubmitJob function")

_job_repository = DynamoDbJobRepository(boto3.resource("dynamodb").Table(_settings.jobs_table_name))
_dataset_storage = S3DatasetStorage(boto3.client("s3"), _settings.datasets_bucket_name)
_orchestrator = StepFunctionsJobOrchestrator(
    boto3.client("stepfunctions"), _settings.state_machine_arn
)
_use_case = SubmitBatchJob(
    job_repository=_job_repository,
    dataset_storage=_dataset_storage,
    orchestrator=_orchestrator,
    job_ttl_days=_settings.job_ttl_days,
)


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """API Gateway proxy entry point for POST /jobs."""
    try:
        request = SubmitJobRequest.model_validate_json(event.get("body") or "{}")
    except ValidationError as exc:
        logger.warning("Rejected malformed submit-job request", extra={"errors": exc.errors()})
        return json_response(400, {"message": "Invalid request body", "errors": exc.errors()})

    logger.append_keys(job_id=request.job_id)

    try:
        response = _use_case.execute(request)
    except InvalidDatasetError as exc:
        logger.warning("Rejected submit-job: dataset not ready", extra={"reason": str(exc)})
        return json_response(404, {"message": str(exc)})

    logger.info("Job submitted", extra={"status": response.status})
    return json_response(202, response)
