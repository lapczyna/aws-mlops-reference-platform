"""Step Functions adapter implementing the JobOrchestrator port."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from batch_inference_platform.domain.ports.job_orchestrator import JobOrchestrator
from batch_inference_platform.domain.value_objects.job_id import JobId

if TYPE_CHECKING:
    from mypy_boto3_stepfunctions.client import SFNClient

_EXECUTION_ALREADY_EXISTS = "ExecutionAlreadyExists"


class StepFunctionsJobOrchestrator(JobOrchestrator):
    """Starts a job orchestration execution, named after the job id.

    Using the job id as the execution name (see
    docs/architecture/sequence-diagrams.md#2-batch-job-submission) doubles as
    a natural idempotency key: a retried submission for the same job simply
    finds its execution already started rather than launching a duplicate.
    """

    def __init__(self, sfn_client: SFNClient, state_machine_arn: str) -> None:
        self._sfn = sfn_client
        self._state_machine_arn = state_machine_arn

    def start_execution(self, job_id: JobId, input_s3_key: str) -> None:
        try:
            self._sfn.start_execution(
                stateMachineArn=self._state_machine_arn,
                name=str(job_id),
                input=json.dumps({"job_id": str(job_id), "input_s3_key": input_s3_key}),
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == _EXECUTION_ALREADY_EXISTS:
                return
            raise
