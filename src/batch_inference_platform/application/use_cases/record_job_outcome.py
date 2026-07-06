"""Use case: RecordJobOutcome (backs the RecordSuccess/RecordFailure state machine tasks)."""

from __future__ import annotations

from aws_lambda_powertools.metrics import Metrics, MetricUnit

from batch_inference_platform.domain.exceptions.job_exceptions import JobNotFoundError
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_paths import prediction_key
from batch_inference_platform.domain.value_objects.job_status import JobStatus

_DEFAULT_FAILURE_REASON = "UnknownError"
_DEFAULT_FAILURE_CAUSE = "Job failed for an unknown reason"


class RecordJobOutcome:
    """Persists a job's terminal outcome and emits a business metric for it."""

    def __init__(self, job_repository: JobRepository, metrics: Metrics) -> None:
        self._job_repository = job_repository
        self._metrics = metrics

    def execute(
        self,
        job_id_value: str,
        status: str,
        error_code: str | None = None,
        error_cause: str | None = None,
    ) -> None:
        job_id = JobId(job_id_value)
        job = self._job_repository.get(job_id)
        if job is None:
            raise JobNotFoundError(job_id_value)

        if status == JobStatus.COMPLETED.value:
            job.mark_completed(prediction_key(job_id))
            self._metrics.add_metric(name="JobCompleted", unit=MetricUnit.Count, value=1)
        else:
            reason = error_code or _DEFAULT_FAILURE_REASON
            cause = error_cause or _DEFAULT_FAILURE_CAUSE
            job.mark_failed(f"{reason}: {cause}")
            self._metrics.add_metric(name="JobFailed", unit=MetricUnit.Count, value=1)
            self._metrics.add_metadata(key="failure_reason", value=reason)

        self._job_repository.save(job)
