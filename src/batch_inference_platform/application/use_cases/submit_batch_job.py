"""Use case: SubmitBatchJob (backs POST /jobs).

Idempotent by design (see ADR-0013): resubmitting the same job id neither
creates a duplicate DynamoDB record nor starts a duplicate Step Functions
execution -- it simply reports the job's current state.
"""

from __future__ import annotations

from batch_inference_platform.application.dto.submit_job import (
    SubmitJobRequest,
    SubmitJobResponse,
)
from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidDatasetError,
    JobAlreadyExistsError,
)
from batch_inference_platform.domain.ports.dataset_storage import DatasetStorage
from batch_inference_platform.domain.ports.job_orchestrator import JobOrchestrator
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_paths import dataset_key


class SubmitBatchJob:
    """Validates the uploaded dataset exists, then creates and orchestrates a job."""

    def __init__(
        self,
        job_repository: JobRepository,
        dataset_storage: DatasetStorage,
        orchestrator: JobOrchestrator,
        job_ttl_days: int,
    ) -> None:
        self._job_repository = job_repository
        self._dataset_storage = dataset_storage
        self._orchestrator = orchestrator
        self._job_ttl_days = job_ttl_days

    def execute(self, request: SubmitJobRequest) -> SubmitJobResponse:
        job_id = JobId(request.job_id)
        input_s3_key = dataset_key(job_id)

        size = self._dataset_storage.get_size(input_s3_key)
        if not size:
            raise InvalidDatasetError(
                f"No dataset found at '{input_s3_key}'; upload it before submitting a job"
            )

        job = InferenceJob.submit(job_id, input_s3_key, ttl_days=self._job_ttl_days)
        try:
            self._job_repository.create(job)
        except JobAlreadyExistsError:
            job = self._job_repository.get(job_id) or job

        # Idempotent: StepFunctionsJobOrchestrator treats an already-started
        # execution for this job id as a no-op.
        self._orchestrator.start_execution(job_id, input_s3_key)

        return SubmitJobResponse(job_id=str(job.job_id), status=job.status.value)
