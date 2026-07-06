import pytest

from batch_inference_platform.application.use_cases.get_job_status import GetJobStatus
from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import JobNotFoundError
from batch_inference_platform.domain.value_objects.job_id import JobId
from tests.unit.fakes import FakeJobRepository

pytestmark = pytest.mark.unit

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"


class TestGetJobStatus:
    def test_returns_status_for_existing_job(self) -> None:
        repository = FakeJobRepository()
        repository.create(InferenceJob.submit(JobId(JOB_ID), "uploads/x/input.csv", ttl_days=30))
        use_case = GetJobStatus(repository)

        response = use_case.execute(JOB_ID)

        assert response.job_id == JOB_ID
        assert response.status == "SUBMITTED"
        assert response.error_message is None

    def test_raises_when_job_not_found(self) -> None:
        use_case = GetJobStatus(FakeJobRepository())
        with pytest.raises(JobNotFoundError):
            use_case.execute(JOB_ID)

    def test_raises_on_malformed_job_id(self) -> None:
        use_case = GetJobStatus(FakeJobRepository())
        with pytest.raises(ValueError, match="not a valid ULID"):
            use_case.execute("not-a-ulid")
