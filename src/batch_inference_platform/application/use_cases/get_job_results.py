"""Use case: GetJobResults (backs GET /jobs/{jobId}/results)."""

from __future__ import annotations

from batch_inference_platform.application.dto.job_results import JobResultsResponse
from batch_inference_platform.domain.exceptions.job_exceptions import (
    JobNotCompletedError,
    JobNotFoundError,
)
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.ports.results_storage import ResultsStorage
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus

_DEFAULT_URL_EXPIRY_SECONDS = 900


class GetJobResults:
    """Returns a presigned download URL once a job has completed."""

    def __init__(
        self,
        job_repository: JobRepository,
        results_storage: ResultsStorage,
        url_expiry_seconds: int = _DEFAULT_URL_EXPIRY_SECONDS,
    ) -> None:
        self._job_repository = job_repository
        self._results_storage = results_storage
        self._url_expiry_seconds = url_expiry_seconds

    def execute(self, job_id_value: str) -> JobResultsResponse:
        job_id = JobId(job_id_value)
        job = self._job_repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id_value)
        if job.status is not JobStatus.COMPLETED or job.output_s3_key is None:
            raise JobNotCompletedError(job_id_value, job.status.value)

        download_url = self._results_storage.generate_download_url(
            job.output_s3_key, expires_in_seconds=self._url_expiry_seconds
        )
        return JobResultsResponse(
            download_url=download_url,
            expires_in_seconds=self._url_expiry_seconds,
        )
