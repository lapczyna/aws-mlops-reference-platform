"""POST /datasets/upload-url -- placeholder handler.

Real implementation (ULID generation, presigned S3 PUT URL, and the request/
response DTOs it depends on) lands in Phase 3. This stub exists so the
Phase 2 infrastructure -- API Gateway, this function, its IAM role, and the
shared Lambda Layer -- can be deployed and smoke-tested end to end.
"""

from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="presign-upload")


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """API Gateway proxy entry point for POST /datasets/upload-url."""
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Not implemented -- lands in Phase 3.",
                "route": "POST /datasets/upload-url",
            }
        ),
    }
