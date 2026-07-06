"""POST /jobs -- placeholder handler.

Real implementation (dataset existence check, DynamoDB job creation, and
Step Functions StartExecution) lands in Phase 3. This stub exists so the
Phase 2 infrastructure can be deployed and smoke-tested end to end.
"""

from __future__ import annotations

import json
from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="submit-job")


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """API Gateway proxy entry point for POST /jobs."""
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "message": "Not implemented -- lands in Phase 3.",
                "route": "POST /jobs",
            }
        ),
    }
