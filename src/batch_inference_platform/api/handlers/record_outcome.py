"""Step Functions tasks: RecordSuccess / RecordFailure -- placeholder handler.

Real implementation (DynamoDB UpdateItem to a terminal status and CloudWatch
EMF metric emission) lands in Phase 3. This stub only logs the outcome so
the Phase 2 state machine can reach a terminal state end to end.

Invoked directly by Step Functions for both the ``RecordSuccess`` and
``RecordFailure`` states -- see ``statemachine/job_orchestration.asl.json``.
"""

from __future__ import annotations

from typing import Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger(service="record-outcome")


@logger.inject_lambda_context(log_event=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Step Functions task entry point for the RecordSuccess/RecordFailure states."""
    logger.info("Outcome recording stubbed until Phase 3", extra={"event": event})
    return {"acknowledged": True}
