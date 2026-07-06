from __future__ import annotations

import json
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.infrastructure.persistence.dynamodb_job_repository import (
    DynamoDbJobRepository,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

pytestmark = pytest.mark.integration

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


class TestGetJobStatusHandler:
    def test_returns_200_with_status_for_existing_job(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        DynamoDbJobRepository(jobs_table).create(
            InferenceJob.submit(JobId(JOB_ID), f"uploads/{JOB_ID}/input.csv", ttl_days=30)
        )
        monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
        monkeypatch.setenv("DATASETS_BUCKET_NAME", "unused-by-this-handler")
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.get_job_status")
        response = module.handler({"pathParameters": {"jobId": JOB_ID}}, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["job_id"] == JOB_ID
        assert body["status"] == "SUBMITTED"

    def test_returns_404_when_job_not_found(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
        monkeypatch.setenv("DATASETS_BUCKET_NAME", "unused-by-this-handler")
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.get_job_status")
        response = module.handler({"pathParameters": {"jobId": JOB_ID}}, MagicMock())

        assert response["statusCode"] == 404
