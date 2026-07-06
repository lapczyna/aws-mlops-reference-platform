"""Use case: PresignDatasetUpload (backs POST /datasets/upload-url)."""

from __future__ import annotations

from batch_inference_platform.application.dto.presign_upload import PresignUploadResponse
from batch_inference_platform.domain.ports.dataset_storage import DatasetStorage
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_paths import dataset_key

_DEFAULT_URL_EXPIRY_SECONDS = 900


class PresignDatasetUpload:
    """Generates a new job id and a presigned URL to upload its dataset to."""

    def __init__(
        self,
        dataset_storage: DatasetStorage,
        url_expiry_seconds: int = _DEFAULT_URL_EXPIRY_SECONDS,
    ) -> None:
        self._dataset_storage = dataset_storage
        self._url_expiry_seconds = url_expiry_seconds

    def execute(self) -> PresignUploadResponse:
        job_id = JobId.generate()
        key = dataset_key(job_id)
        upload_url = self._dataset_storage.generate_upload_url(
            key, expires_in_seconds=self._url_expiry_seconds
        )
        return PresignUploadResponse(
            job_id=str(job_id),
            upload_url=upload_url,
            expires_in_seconds=self._url_expiry_seconds,
        )
