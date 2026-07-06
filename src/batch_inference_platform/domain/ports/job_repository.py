"""Port: persistence for InferenceJob aggregates."""

from __future__ import annotations

from abc import ABC, abstractmethod

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.value_objects.job_id import JobId


class JobRepository(ABC):
    """Storage-agnostic persistence boundary for InferenceJob."""

    @abstractmethod
    def create(self, job: InferenceJob) -> None:
        """Persist a brand-new job.

        Raises:
            JobAlreadyExistsError: if a job with the same id already exists.
        """

    @abstractmethod
    def get(self, job_id: JobId) -> InferenceJob | None:
        """Fetch a job by id, or None if it doesn't exist."""

    @abstractmethod
    def save(self, job: InferenceJob) -> None:
        """Persist a job's current (already-mutated) state.

        Raises:
            InvalidJobStateTransitionError: if the stored job is already in
                a terminal state, guarding against a duplicate Step
                Functions retry re-applying an outcome.
        """
