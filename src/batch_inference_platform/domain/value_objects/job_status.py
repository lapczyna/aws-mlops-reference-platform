"""JobStatus: the lifecycle states an InferenceJob can be in."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Mirrors the `status` values documented in docs/architecture/overview.md."""

    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.COMPLETED, JobStatus.FAILED)
