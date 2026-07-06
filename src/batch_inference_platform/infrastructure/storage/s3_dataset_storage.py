"""S3 adapter implementing the DatasetStorage port (the datasets bucket)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from botocore.exceptions import ClientError

from batch_inference_platform.domain.ports.dataset_storage import DatasetStorage

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

_NOT_FOUND_CODES = {"404", "NoSuchKey"}


class S3DatasetStorage(DatasetStorage):
    """Generates presigned upload URLs and checks dataset existence in S3."""

    def __init__(self, s3_client: S3Client, bucket_name: str) -> None:
        self._s3 = s3_client
        self._bucket_name = bucket_name

    def generate_upload_url(self, key: str, *, expires_in_seconds: int) -> str:
        return self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket_name, "Key": key},
            ExpiresIn=expires_in_seconds,
        )

    def get_size(self, key: str) -> int | None:
        try:
            response = self._s3.head_object(Bucket=self._bucket_name, Key=key)
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code in _NOT_FOUND_CODES:
                return None
            raise
        return int(response["ContentLength"])
