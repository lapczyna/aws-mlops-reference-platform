"""GET /jobs/{jobId}/results -- Lambda handler.

See docs/architecture/sequence-diagrams.md#5-result-retrieval.
"""

from __future__ import annotations

from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from batch_inference_platform.application.use_cases.get_job_results import GetJobResults
from batch_inference_platform.domain.exceptions.job_exceptions import (
    JobNotCompletedError,
    JobNotFoundError,
)
from batch_inference_platform.infrastructure.persistence.dynamodb_job_repository import (
    DynamoDbJobRepository,
)
from batch_inference_platform.infrastructure.storage.s3_results_storage import S3ResultsStorage
from batch_inference_platform.shared.config import get_settings
from batch_inference_platform.shared.http import json_response
from batch_inference_platform.shared.logging import get_logger

logger = get_logger(service="get-job-results")

_settings = get_settings()
_job_repository = DynamoDbJobRepository(boto3.resource("dynamodb").Table(_settings.jobs_table_name))
_results_storage = S3ResultsStorage(boto3.client("s3"), _settings.results_bucket_name)
_use_case = GetJobResults(_job_repository, _results_storage)


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """API Gateway proxy entry point for GET /jobs/{jobId}/results."""
    job_id_value = (event.get("pathParameters") or {}).get("jobId", "")
    logger.append_keys(job_id=job_id_value)

    try:
        response = _use_case.execute(job_id_value)
    except (JobNotFoundError, ValueError):
        logger.info("Results lookup failed: job not found")
        return json_response(404, {"message": f"Job '{job_id_value}' was not found"})
    except JobNotCompletedError as exc:
        logger.info(
            "Results lookup failed: job not completed", extra={"status": exc.current_status}
        )
        return json_response(409, {"message": str(exc), "status": exc.current_status})

    return json_response(200, response)
