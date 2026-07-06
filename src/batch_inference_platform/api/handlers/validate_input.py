"""Step Functions task: ValidateInput -- Lambda handler.

Invoked directly by Step Functions (not through API Gateway). Returns a
plain dict matching the shape `statemachine/job_orchestration.asl.json`'s
`ResultSelector` expects: ``{"valid": bool, "reason": str | None}``. Any
unexpected exception (e.g. an S3 permissions error) propagates naturally --
the ASL's `Catch: States.ALL` on this state routes it to RecordFailure.
"""

from __future__ import annotations

from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from batch_inference_platform.application.use_cases.validate_job_input import ValidateJobInput
from batch_inference_platform.infrastructure.storage.s3_dataset_storage import S3DatasetStorage
from batch_inference_platform.shared.config import get_settings
from batch_inference_platform.shared.logging import get_logger

logger = get_logger(service="validate-input")

_settings = get_settings()
_dataset_storage = S3DatasetStorage(boto3.client("s3"), _settings.datasets_bucket_name)
_use_case = ValidateJobInput(_dataset_storage)


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Step Functions task entry point for the ValidateInput state."""
    logger.append_keys(job_id=event.get("job_id"))
    result = _use_case.execute(event["input_s3_key"])
    logger.info("Input validated", extra={"valid": result.valid, "reason": result.reason})
    return result.model_dump()
