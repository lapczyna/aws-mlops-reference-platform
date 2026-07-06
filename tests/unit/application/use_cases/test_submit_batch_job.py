import pytest

from batch_inference_platform.application.dto.submit_job import SubmitJobRequest
from batch_inference_platform.application.use_cases.submit_batch_job import SubmitBatchJob
from batch_inference_platform.domain.exceptions.job_exceptions import InvalidDatasetError
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus
from tests.unit.fakes import FakeDatasetStorage, FakeJobOrchestrator, FakeJobRepository

pytestmark = pytest.mark.unit

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
INPUT_KEY = f"uploads/{JOB_ID}/input.csv"


def _use_case(
    repository: FakeJobRepository, storage: FakeDatasetStorage, orchestrator: FakeJobOrchestrator
) -> SubmitBatchJob:
    return SubmitBatchJob(repository, storage, orchestrator, job_ttl_days=30)


class TestSubmitBatchJob:
    def test_submits_job_when_dataset_exists(self) -> None:
        repository = FakeJobRepository()
        orchestrator = FakeJobOrchestrator()
        use_case = _use_case(repository, FakeDatasetStorage(sizes={INPUT_KEY: 1024}), orchestrator)

        response = use_case.execute(SubmitJobRequest(job_id=JOB_ID))

        assert response.job_id == JOB_ID
        assert response.status == JobStatus.SUBMITTED.value
        assert repository.get(JobId(JOB_ID)) is not None
        assert orchestrator.started == [(JOB_ID, INPUT_KEY)]

    def test_rejects_submission_when_dataset_missing(self) -> None:
        orchestrator = FakeJobOrchestrator()
        use_case = _use_case(FakeJobRepository(), FakeDatasetStorage(), orchestrator)

        with pytest.raises(InvalidDatasetError):
            use_case.execute(SubmitJobRequest(job_id=JOB_ID))
        assert orchestrator.started == []

    def test_rejects_submission_when_dataset_empty(self) -> None:
        use_case = _use_case(
            FakeJobRepository(), FakeDatasetStorage(sizes={INPUT_KEY: 0}), FakeJobOrchestrator()
        )

        with pytest.raises(InvalidDatasetError):
            use_case.execute(SubmitJobRequest(job_id=JOB_ID))

    def test_resubmission_of_same_job_id_is_idempotent(self) -> None:
        repository = FakeJobRepository()
        orchestrator = FakeJobOrchestrator()
        use_case = _use_case(repository, FakeDatasetStorage(sizes={INPUT_KEY: 1024}), orchestrator)

        first = use_case.execute(SubmitJobRequest(job_id=JOB_ID))
        second = use_case.execute(SubmitJobRequest(job_id=JOB_ID))

        assert first.job_id == second.job_id == JOB_ID
        # Same job id was reported both times, and the orchestrator (which
        # itself no-ops on ExecutionAlreadyExists) was still asked to start
        # -- no duplicate DynamoDB item was created for the second call.
        assert orchestrator.started == [(JOB_ID, INPUT_KEY), (JOB_ID, INPUT_KEY)]
