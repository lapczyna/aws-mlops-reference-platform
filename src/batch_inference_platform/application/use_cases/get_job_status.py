"""Use case: GetJobStatus (backs GET /jobs/{jobId})."""

from __future__ import annotations

from batch_inference_platform.application.dto.job_status import JobStatusResponse
from batch_inference_platform.domain.exceptions.job_exceptions import JobNotFoundError
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.value_objects.job_id import JobId


class GetJobStatus:
    """Fetches a job's current status."""

    def __init__(self, job_repository: JobRepository) -> None:
        self._job_repository = job_repository

    def execute(self, job_id_value: str) -> JobStatusResponse:
        job_id = JobId(job_id_value)
        job = self._job_repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id_value)

        return JobStatusResponse(
            job_id=str(job.job_id),
            status=job.status.value,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat(),
            error_message=job.error_message,
        )
