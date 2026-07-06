"""InferenceJob: the aggregate root for a single batch inference request."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidJobStateTransitionError,
)
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus


@dataclass(slots=True)
class InferenceJob:
    """A batch inference job and its lifecycle state.

    Note: the SUBMITTED -> PROCESSING transition is applied in production by
    a direct Step Functions -> DynamoDB integration (see
    statemachine/job_orchestration.asl.json's MarkProcessing state), not by
    calling mark_processing() here. That method still exists so the full
    state machine is modeled and unit-testable in one place; the ASL's own
    structure (ValidateInput always precedes MarkProcessing) is what
    actually enforces ordering in production.
    """

    job_id: JobId
    status: JobStatus
    input_s3_key: str
    created_at: datetime
    updated_at: datetime
    ttl: int
    output_s3_key: str | None = None
    error_message: str | None = None

    @classmethod
    def submit(cls, job_id: JobId, input_s3_key: str, ttl_days: int) -> InferenceJob:
        """Create a new job in the SUBMITTED state."""
        now = datetime.now(UTC)
        return cls(
            job_id=job_id,
            status=JobStatus.SUBMITTED,
            input_s3_key=input_s3_key,
            created_at=now,
            updated_at=now,
            ttl=int((now + timedelta(days=ttl_days)).timestamp()),
        )

    def mark_processing(self) -> None:
        self._transition_to(JobStatus.PROCESSING, allowed_from=(JobStatus.SUBMITTED,))

    def mark_completed(self, output_s3_key: str) -> None:
        self._transition_to(JobStatus.COMPLETED, allowed_from=(JobStatus.PROCESSING,))
        self.output_s3_key = output_s3_key

    def mark_failed(self, error_message: str) -> None:
        self._transition_to(
            JobStatus.FAILED, allowed_from=(JobStatus.SUBMITTED, JobStatus.PROCESSING)
        )
        self.error_message = error_message

    def _transition_to(self, new_status: JobStatus, *, allowed_from: tuple[JobStatus, ...]) -> None:
        if self.status not in allowed_from:
            raise InvalidJobStateTransitionError(
                job_id=str(self.job_id),
                current_status=self.status.value,
                attempted_status=new_status.value,
            )
        self.status = new_status
        self.updated_at = datetime.now(UTC)
