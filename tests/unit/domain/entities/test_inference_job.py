import pytest

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidJobStateTransitionError,
)
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus

pytestmark = pytest.mark.unit

JOB_ID = JobId("01ARZ3NDEKTSV4RRFFQ69G5FAV")
INPUT_KEY = "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"
OUTPUT_KEY = "predictions/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv.out"


def _new_job() -> InferenceJob:
    return InferenceJob.submit(JOB_ID, INPUT_KEY, ttl_days=30)


class TestSubmit:
    def test_creates_job_in_submitted_status(self) -> None:
        job = _new_job()
        assert job.status == JobStatus.SUBMITTED
        assert job.input_s3_key == INPUT_KEY
        assert job.output_s3_key is None
        assert job.error_message is None

    def test_sets_ttl_after_created_at(self) -> None:
        job = _new_job()
        assert job.ttl > int(job.created_at.timestamp())


class TestMarkProcessing:
    def test_from_submitted_succeeds(self) -> None:
        job = _new_job()
        job.mark_processing()
        assert job.status == JobStatus.PROCESSING

    def test_from_processing_raises(self) -> None:
        job = _new_job()
        job.mark_processing()
        with pytest.raises(InvalidJobStateTransitionError):
            job.mark_processing()

    def test_from_completed_raises(self) -> None:
        job = _new_job()
        job.mark_processing()
        job.mark_completed(OUTPUT_KEY)
        with pytest.raises(InvalidJobStateTransitionError):
            job.mark_processing()


class TestMarkCompleted:
    def test_from_processing_succeeds(self) -> None:
        job = _new_job()
        job.mark_processing()
        job.mark_completed(OUTPUT_KEY)
        assert job.status == JobStatus.COMPLETED
        assert job.output_s3_key == OUTPUT_KEY

    def test_from_submitted_raises(self) -> None:
        job = _new_job()
        with pytest.raises(InvalidJobStateTransitionError):
            job.mark_completed(OUTPUT_KEY)

    def test_from_failed_raises(self) -> None:
        job = _new_job()
        job.mark_failed("boom")
        with pytest.raises(InvalidJobStateTransitionError):
            job.mark_completed(OUTPUT_KEY)


class TestMarkFailed:
    def test_from_submitted_succeeds(self) -> None:
        job = _new_job()
        job.mark_failed("InvalidInput: dataset missing")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "InvalidInput: dataset missing"

    def test_from_processing_succeeds(self) -> None:
        job = _new_job()
        job.mark_processing()
        job.mark_failed("TransformError: boom")
        assert job.status == JobStatus.FAILED

    def test_from_completed_raises(self) -> None:
        job = _new_job()
        job.mark_processing()
        job.mark_completed(OUTPUT_KEY)
        with pytest.raises(InvalidJobStateTransitionError):
            job.mark_failed("too late")
