"""Domain exception hierarchy for job-related failures.

Lambda handlers are the only place these are caught and translated into an
HTTP response or a Step Functions failure payload -- see
docs/standards/coding-standards.md#error-handling.
"""

from __future__ import annotations


class JobError(Exception):
    """Base class for all job-related domain errors."""


class JobNotFoundError(JobError):
    """Raised when a job id has no corresponding record."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' was not found")
        self.job_id = job_id


class JobAlreadyExistsError(JobError):
    """Raised when attempting to create a job id that already exists."""

    def __init__(self, job_id: str) -> None:
        super().__init__(f"Job '{job_id}' already exists")
        self.job_id = job_id


class JobNotCompletedError(JobError):
    """Raised when results are requested for a job that isn't COMPLETED yet."""

    def __init__(self, job_id: str, current_status: str) -> None:
        super().__init__(f"Job '{job_id}' is not completed (status: {current_status})")
        self.job_id = job_id
        self.current_status = current_status


class InvalidJobStateTransitionError(JobError):
    """Raised when an entity transition would violate the job status lifecycle."""

    def __init__(self, job_id: str, current_status: str, attempted_status: str) -> None:
        super().__init__(
            f"Job '{job_id}' cannot transition from {current_status} to {attempted_status}"
        )
        self.job_id = job_id
        self.current_status = current_status
        self.attempted_status = attempted_status


class InvalidDatasetError(JobError):
    """Raised when an uploaded dataset fails validation (missing or empty)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
