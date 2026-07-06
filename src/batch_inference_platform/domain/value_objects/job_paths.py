"""S3 key layout for a job's dataset and prediction output.

Centralized here because three different components (PresignUpload,
SubmitJob/ValidateInput, and RecordOutcome) all need to derive the same
keys from a job id and must never drift out of sync with each other -- see
docs/architecture/overview.md#s3-layout.
"""

from __future__ import annotations

from batch_inference_platform.domain.value_objects.job_id import JobId

_INPUT_FILENAME = "input.csv"


def dataset_key(job_id: JobId) -> str:
    """Key of the uploaded dataset in the datasets bucket."""
    return f"uploads/{job_id}/{_INPUT_FILENAME}"


def prediction_key(job_id: JobId) -> str:
    """Key of the prediction output in the results bucket.

    SageMaker Batch Transform names its output ``<input-filename>.out``, so
    this is deterministic from the job id alone without needing to inspect
    the completed transform job's response.
    """
    return f"predictions/{job_id}/{_INPUT_FILENAME}.out"
