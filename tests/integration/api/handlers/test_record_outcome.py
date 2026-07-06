from __future__ import annotations

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


def _seed_processing_job(jobs_table: Table) -> None:
    job = InferenceJob.submit(JobId(JOB_ID), f"uploads/{JOB_ID}/input.csv", ttl_days=30)
    job.mark_processing()
    DynamoDbJobRepository(jobs_table).create(job)


class TestRecordOutcomeHandler:
    def test_records_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        _seed_processing_job(jobs_table)
        monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
        monkeypatch.setenv("DATASETS_BUCKET_NAME", "unused-by-this-handler")
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.record_outcome")
        response = module.handler({"job_id": JOB_ID, "status": "COMPLETED"}, MagicMock())

        assert response == {"acknowledged": True}
        job = DynamoDbJobRepository(jobs_table).get(JobId(JOB_ID))
        assert job is not None
        assert job.status.value == "COMPLETED"

    def test_records_failure_with_error_details(
        self,
        monkeypatch: pytest.MonkeyPatch,
        jobs_table: Table,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        _seed_processing_job(jobs_table)
        monkeypatch.setenv("JOBS_TABLE_NAME", jobs_table.name)
        monkeypatch.setenv("DATASETS_BUCKET_NAME", "unused-by-this-handler")
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.record_outcome")
        event = {
            "job_id": JOB_ID,
            "status": "FAILED",
            "error_code": "TransformError",
            "error_cause": "boom",
        }
        module.handler(event, MagicMock())

        job = DynamoDbJobRepository(jobs_table).get(JobId(JOB_ID))
        assert job is not None
        assert job.status.value == "FAILED"
        assert job.error_message == "TransformError: boom"
