"""S3 adapter implementing the ResultsStorage port (the results bucket)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from batch_inference_platform.domain.ports.results_storage import ResultsStorage

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client


class S3ResultsStorage(ResultsStorage):
    """Generates presigned download URLs for prediction outputs."""

    def __init__(self, s3_client: S3Client, bucket_name: str) -> None:
        self._s3 = s3_client
        self._bucket_name = bucket_name

    def generate_download_url(self, key: str, *, expires_in_seconds: int) -> str:
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket_name, "Key": key},
            ExpiresIn=expires_in_seconds,
        )
