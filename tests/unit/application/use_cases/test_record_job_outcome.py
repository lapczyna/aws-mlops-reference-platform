import pytest
from aws_lambda_powertools.metrics import Metrics

from batch_inference_platform.application.use_cases.record_job_outcome import RecordJobOutcome
from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import JobNotFoundError
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_paths import prediction_key
from batch_inference_platform.domain.value_objects.job_status import JobStatus
from tests.unit.fakes import FakeJobRepository

pytestmark = pytest.mark.unit

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


def _processing_job() -> InferenceJob:
    job = InferenceJob.submit(JobId(JOB_ID), "uploads/x/input.csv", ttl_days=30)
    job.mark_processing()
    return job


class TestRecordJobOutcomeSuccess:
    def test_marks_job_completed_and_emits_metric(self) -> None:
        repository = FakeJobRepository()
        repository.create(_processing_job())
        metrics = Metrics(namespace="Test", service="test")
        use_case = RecordJobOutcome(repository, metrics)

        use_case.execute(job_id_value=JOB_ID, status=JobStatus.COMPLETED.value)

        job = repository.get(JobId(JOB_ID))
        assert job is not None
        assert job.status == JobStatus.COMPLETED
        assert job.output_s3_key == prediction_key(JobId(JOB_ID))
        assert "JobCompleted" in metrics.metric_set


class TestRecordJobOutcomeFailure:
    def test_marks_job_failed_with_error_details_and_emits_metric(self) -> None:
        repository = FakeJobRepository()
        repository.create(_processing_job())
        metrics = Metrics(namespace="Test", service="test")
        use_case = RecordJobOutcome(repository, metrics)

        use_case.execute(
            job_id_value=JOB_ID,
            status=JobStatus.FAILED.value,
            error_code="TransformError",
            error_cause="instance ran out of memory",
        )

        job = repository.get(JobId(JOB_ID))
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error_message == "TransformError: instance ran out of memory"
        assert "JobFailed" in metrics.metric_set
        assert metrics.metadata_set["failure_reason"] == "TransformError"

    def test_defaults_reason_and_cause_when_not_provided(self) -> None:
        repository = FakeJobRepository()
        repository.create(_processing_job())
        use_case = RecordJobOutcome(repository, Metrics(namespace="Test", service="test"))

        use_case.execute(job_id_value=JOB_ID, status=JobStatus.FAILED.value)

        job = repository.get(JobId(JOB_ID))
        assert job is not None
        assert job.error_message == "UnknownError: Job failed for an unknown reason"


class TestRecordJobOutcomeNotFound:
    def test_raises_when_job_does_not_exist(self) -> None:
        use_case = RecordJobOutcome(FakeJobRepository(), Metrics(namespace="Test", service="test"))
        with pytest.raises(JobNotFoundError):
            use_case.execute(job_id_value=JOB_ID, status=JobStatus.COMPLETED.value)
