"""Port: starting the batch inference orchestration workflow."""

from __future__ import annotations

from abc import ABC, abstractmethod

from batch_inference_platform.domain.value_objects.job_id import JobId


class JobOrchestrator(ABC):
    """Storage-agnostic boundary for kicking off a job's Step Functions execution."""

    @abstractmethod
    def start_execution(self, job_id: JobId, input_s3_key: str) -> None:
        """Start orchestration for a newly submitted job."""
