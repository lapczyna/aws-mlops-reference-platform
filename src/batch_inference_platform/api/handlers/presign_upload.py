"""POST /datasets/upload-url -- Lambda handler.

See docs/architecture/sequence-diagrams.md#1-dataset-upload.
"""

from __future__ import annotations

from typing import Any

import boto3
from aws_lambda_powertools.utilities.typing import LambdaContext

from batch_inference_platform.application.use_cases.presign_dataset_upload import (
    PresignDatasetUpload,
)
from batch_inference_platform.infrastructure.storage.s3_dataset_storage import S3DatasetStorage
from batch_inference_platform.shared.config import get_settings
from batch_inference_platform.shared.http import json_response
from batch_inference_platform.shared.logging import get_logger

logger = get_logger(service="presign-upload")

# Constructed once per execution environment (cold start) and reused across
# warm invocations -- see docs/standards/coding-standards.md.
_settings = get_settings()
_dataset_storage = S3DatasetStorage(boto3.client("s3"), _settings.datasets_bucket_name)
_use_case = PresignDatasetUpload(_dataset_storage)


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """API Gateway proxy entry point for POST /datasets/upload-url."""
    response = _use_case.execute()
    logger.append_keys(job_id=response.job_id)
    logger.info("Presigned upload URL generated")
    return json_response(200, response)
