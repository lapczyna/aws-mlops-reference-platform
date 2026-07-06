from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.infrastructure.orchestration.stepfunctions_job_orchestrator import (
    StepFunctionsJobOrchestrator,
)

if TYPE_CHECKING:
    from mypy_boto3_stepfunctions.client import SFNClient

pytestmark = pytest.mark.integration

JOB_ID = JobId("01ARZ3NDEKTSV4RRFFQ69G5FAV")
INPUT_KEY = "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"


class TestStartExecution:
    def test_starts_a_new_execution_named_after_the_job_id(
        self, sfn_client: SFNClient, state_machine_arn: str
    ) -> None:
        orchestrator = StepFunctionsJobOrchestrator(sfn_client, state_machine_arn)

        orchestrator.start_execution(JOB_ID, INPUT_KEY)

        executions = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
        assert len(executions) == 1
        assert executions[0]["name"] == str(JOB_ID)

    def test_is_idempotent_for_a_repeated_job_id(
        self, sfn_client: SFNClient, state_machine_arn: str
    ) -> None:
        orchestrator = StepFunctionsJobOrchestrator(sfn_client, state_machine_arn)

        orchestrator.start_execution(JOB_ID, INPUT_KEY)
        orchestrator.start_execution(JOB_ID, INPUT_KEY)  # must not raise

        executions = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
        assert len(executions) == 1
