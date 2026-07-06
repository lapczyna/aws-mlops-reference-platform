"""In-memory fakes for domain ports, used across application-layer unit tests.

No AWS calls, no moto -- these exist purely so use cases can be exercised
in isolation. Integration tests (tests/integration/) verify the real
infrastructure adapters against moto-mocked AWS services.
"""

from __future__ import annotations

import copy

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidJobStateTransitionError,
    JobAlreadyExistsError,
)
from batch_inference_platform.domain.ports.dataset_storage import DatasetStorage
from batch_inference_platform.domain.ports.job_orchestrator import JobOrchestrator
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.ports.results_storage import ResultsStorage
from batch_inference_platform.domain.value_objects.job_id import JobId


class FakeJobRepository(JobRepository):
    def __init__(self) -> None:
        self._jobs: dict[str, InferenceJob] = {}

    def create(self, job: InferenceJob) -> None:
        if str(job.job_id) in self._jobs:
            raise JobAlreadyExistsError(str(job.job_id))
        self._jobs[str(job.job_id)] = copy.deepcopy(job)

    def get(self, job_id: JobId) -> InferenceJob | None:
        # A real repository deserializes a fresh entity on every read; return
        # a copy here too, so mutating the result (e.g. job.mark_completed())
        # doesn't silently mutate what's "persisted" until save() is called.
        job = self._jobs.get(str(job_id))
        return None if job is None else copy.deepcopy(job)

    def save(self, job: InferenceJob) -> None:
        existing = self._jobs.get(str(job.job_id))
        if existing is not None and existing.status.is_terminal:
            raise InvalidJobStateTransitionError(
                job_id=str(job.job_id),
                current_status=existing.status.value,
                attempted_status=job.status.value,
            )
        self._jobs[str(job.job_id)] = copy.deepcopy(job)


class FakeDatasetStorage(DatasetStorage):
    def __init__(self, sizes: dict[str, int] | None = None) -> None:
        self._sizes = dict(sizes or {})
        self.upload_url_calls: list[str] = []

    def generate_upload_url(self, key: str, *, expires_in_seconds: int) -> str:
        self.upload_url_calls.append(key)
        return f"https://example-datasets-bucket.s3.amazonaws.com/{key}?presigned=true"

    def get_size(self, key: str) -> int | None:
        return self._sizes.get(key)


class FakeResultsStorage(ResultsStorage):
    def generate_download_url(self, key: str, *, expires_in_seconds: int) -> str:
        return f"https://example-results-bucket.s3.amazonaws.com/{key}?presigned=true"


class FakeJobOrchestrator(JobOrchestrator):
    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []

    def start_execution(self, job_id: JobId, input_s3_key: str) -> None:
        self.started.append((str(job_id), input_s3_key))
