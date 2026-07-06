from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidJobStateTransitionError,
    JobAlreadyExistsError,
)
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus
from batch_inference_platform.infrastructure.persistence.dynamodb_job_repository import (
    DynamoDbJobRepository,
)

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

pytestmark = pytest.mark.integration

JOB_ID = JobId("01ARZ3NDEKTSV4RRFFQ69G5FAV")
INPUT_KEY = "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"
OUTPUT_KEY = "predictions/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv.out"


class TestCreate:
    def test_create_then_get_round_trips_all_fields(self, jobs_table: Table) -> None:
        repository = DynamoDbJobRepository(jobs_table)
        job = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)

        repository.create(job)
        fetched = repository.get(JOB_ID)

        assert fetched is not None
        assert fetched.job_id == JOB_ID
        assert fetched.status == JobStatus.SUBMITTED
        assert fetched.input_s3_key == INPUT_KEY
        assert fetched.ttl == job.ttl
        assert fetched.created_at == job.created_at
        assert fetched.output_s3_key is None
        assert fetched.error_message is None

    def test_create_duplicate_job_id_raises(self, jobs_table: Table) -> None:
        repository = DynamoDbJobRepository(jobs_table)
        job = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)
        repository.create(job)

        with pytest.raises(JobAlreadyExistsError):
            repository.create(job)


class TestGet:
    def test_returns_none_when_job_does_not_exist(self, jobs_table: Table) -> None:
        repository = DynamoDbJobRepository(jobs_table)
        assert repository.get(JOB_ID) is None


class TestSave:
    def test_save_persists_completed_state(self, jobs_table: Table) -> None:
        repository = DynamoDbJobRepository(jobs_table)
        job = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)
        repository.create(job)

        job.mark_processing()
        repository.save(job)
        job.mark_completed(OUTPUT_KEY)
        repository.save(job)

        fetched = repository.get(JOB_ID)
        assert fetched is not None
        assert fetched.status == JobStatus.COMPLETED
        assert fetched.output_s3_key == OUTPUT_KEY

    def test_save_persists_failed_state_with_error_message(self, jobs_table: Table) -> None:
        repository = DynamoDbJobRepository(jobs_table)
        job = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)
        repository.create(job)

        job.mark_failed("InvalidInput: dataset not found")
        repository.save(job)

        fetched = repository.get(JOB_ID)
        assert fetched is not None
        assert fetched.status == JobStatus.FAILED
        assert fetched.error_message == "InvalidInput: dataset not found"

    def test_save_rejects_overwriting_an_already_terminal_job(self, jobs_table: Table) -> None:
        """Guards against a duplicate Step Functions retry double-applying an outcome."""
        repository = DynamoDbJobRepository(jobs_table)
        job = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)
        repository.create(job)
        job.mark_failed("boom")
        repository.save(job)

        duplicate_retry = InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)
        duplicate_retry.mark_processing()
        duplicate_retry.mark_completed(OUTPUT_KEY)

        with pytest.raises(InvalidJobStateTransitionError):
            repository.save(duplicate_retry)
