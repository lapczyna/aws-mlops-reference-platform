from __future__ import annotations

import json
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_stepfunctions.client import SFNClient

pytestmark = pytest.mark.integration

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
INPUT_KEY = f"uploads/{JOB_ID}/input.csv"


def _set_common_env(
    monkeypatch: pytest.MonkeyPatch, jobs_table: Table, datasets_bucket: str, state_machine_arn: str
) -> None:
    monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
    monkeypatch.setenv("DATASETS_BUCKET_NAME", datasets_bucket)
    monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")
    monkeypatch.setenv("STATE_MACHINE_ARN", state_machine_arn)
    monkeypatch.setenv("JOB_TTL_DAYS", "30")


class TestSubmitJobHandler:
    def test_returns_202_and_starts_orchestration_when_dataset_exists(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        s3_client: S3Client,
        datasets_bucket: str,
        sfn_client: SFNClient,
        state_machine_arn: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        s3_client.put_object(Bucket=datasets_bucket, Key=INPUT_KEY, Body=b"5.1,3.5,1.4,0.2")
        _set_common_env(monkeypatch, jobs_table, datasets_bucket, state_machine_arn)

        module = import_handler("batch_inference_platform.api.handlers.submit_job")
        event = {"body": json.dumps({"job_id": JOB_ID})}
        response = module.handler(event, MagicMock())

        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body == {"job_id": JOB_ID, "status": "SUBMITTED"}

        executions = sfn_client.list_executions(stateMachineArn=state_machine_arn)["executions"]
        assert [e["name"] for e in executions] == [JOB_ID]

    def test_returns_404_when_dataset_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        s3_client: S3Client,
        datasets_bucket: str,
        sfn_client: SFNClient,
        state_machine_arn: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        _set_common_env(monkeypatch, jobs_table, datasets_bucket, state_machine_arn)

        module = import_handler("batch_inference_platform.api.handlers.submit_job")
        event = {"body": json.dumps({"job_id": JOB_ID})}
        response = module.handler(event, MagicMock())

        assert response["statusCode"] == 404

    def test_returns_400_on_malformed_body(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        s3_client: S3Client,
        datasets_bucket: str,
        sfn_client: SFNClient,
        state_machine_arn: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        _set_common_env(monkeypatch, jobs_table, datasets_bucket, state_machine_arn)

        module = import_handler("batch_inference_platform.api.handlers.submit_job")
        response = module.handler({"body": "{}"}, MagicMock())

        assert response["statusCode"] == 400
