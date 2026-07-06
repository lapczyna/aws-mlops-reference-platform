"""Step Functions task: ValidateInput -- placeholder handler.

Real implementation (checking the uploaded dataset exists in S3 and is
well-formed) lands in Phase 3. This stub always reports the input as valid
so the Phase 2 state machine can be exercised end to end without a real
dataset present.

Invoked directly by Step Functions (not through API Gateway), so the return
value is a plain dict matching the shape the state machine's
`ResultSelector` expects: ``{"valid": bool, "reason": str | None}``. See
``statemachine/job_orchestration.asl.json``.
"""

from __future__ import annotations

from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="validate-input")


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Step Functions task entry point for the ValidateInput state."""
    logger.info("Validation stubbed as always-valid until Phase 3", extra={"event": event})
    return {"valid": True, "reason": None}
