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
OUTPUT_KEY = f"predictions/{JOB_ID}/input.csv.out"


def _set_env(monkeypatch: pytest.MonkeyPatch, jobs_table: Table, results_bucket: str) -> None:
    monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
    monkeypatch.setenv("DATASETS_BUCKET_NAME", "unused-by-this-handler")
    monkeypatch.setenv("RESULTS_BUCKET_NAME", results_bucket)


class TestGetJobResultsHandler:
    def test_returns_200_with_download_url_when_completed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        results_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        job = InferenceJob.submit(JobId(JOB_ID), f"uploads/{JOB_ID}/input.csv", ttl_days=30)
        job.mark_processing()
        job.mark_completed(OUTPUT_KEY)
        DynamoDbJobRepository(jobs_table).create(job)
        _set_env(monkeypatch, jobs_table, results_bucket)

        module = import_handler("batch_inference_platform.api.handlers.get_job_results")
        response = module.handler({"pathParameters": {"jobId": JOB_ID}}, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert OUTPUT_KEY in body["download_url"]

    def test_returns_404_when_job_not_found(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        results_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        _set_env(monkeypatch, jobs_table, results_bucket)

        module = import_handler("batch_inference_platform.api.handlers.get_job_results")
        response = module.handler({"pathParameters": {"jobId": JOB_ID}}, MagicMock())

        assert response["statusCode"] == 404

    def test_returns_409_when_job_not_completed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        results_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        DynamoDbJobRepository(jobs_table).create(
            InferenceJob.submit(JobId(JOB_ID), f"uploads/{JOB_ID}/input.csv", ttl_days=30)
        )
        _set_env(monkeypatch, jobs_table, results_bucket)

        module = import_handler("batch_inference_platform.api.handlers.get_job_results")
        response = module.handler({"pathParameters": {"jobId": JOB_ID}}, MagicMock())

        assert response["statusCode"] == 409
