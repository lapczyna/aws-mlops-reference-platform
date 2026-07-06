import pytest

from batch_inference_platform.application.use_cases.get_job_results import GetJobResults
from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    JobNotCompletedError,
    JobNotFoundError,
)
from batch_inference_platform.domain.value_objects.job_id import JobId
from tests.unit.fakes import FakeJobRepository, FakeResultsStorage

pytestmark = pytest.mark.unit

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
OUTPUT_KEY = f"predictions/{JOB_ID}/input.csv.out"


class TestGetJobResults:
    def test_returns_download_url_when_completed(self) -> None:
        repository = FakeJobRepository()
        job = InferenceJob.submit(JobId(JOB_ID), "uploads/x/input.csv", ttl_days=30)
        job.mark_processing()
        job.mark_completed(OUTPUT_KEY)
        repository.create(job)
        use_case = GetJobResults(repository, FakeResultsStorage())

        response = use_case.execute(JOB_ID)

        assert OUTPUT_KEY in response.download_url

    def test_raises_when_job_not_found(self) -> None:
        use_case = GetJobResults(FakeJobRepository(), FakeResultsStorage())
        with pytest.raises(JobNotFoundError):
            use_case.execute(JOB_ID)

    @pytest.mark.parametrize("mark_processing", [True, False])
    def test_raises_when_job_not_completed(self, mark_processing: bool) -> None:
        repository = FakeJobRepository()
        job = InferenceJob.submit(JobId(JOB_ID), "uploads/x/input.csv", ttl_days=30)
        if mark_processing:
            job.mark_processing()
        repository.create(job)
        use_case = GetJobResults(repository, FakeResultsStorage())

        with pytest.raises(JobNotCompletedError):
            use_case.execute(JOB_ID)
