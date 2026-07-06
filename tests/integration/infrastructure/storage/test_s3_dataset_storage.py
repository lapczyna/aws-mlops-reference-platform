from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from batch_inference_platform.infrastructure.storage.s3_dataset_storage import S3DatasetStorage

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

pytestmark = pytest.mark.integration

KEY = "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"


class TestGetSize:
    def test_returns_none_when_object_does_not_exist(
        self, s3_client: S3Client, datasets_bucket: str
    ) -> None:
        storage = S3DatasetStorage(s3_client, datasets_bucket)
        assert storage.get_size(KEY) is None

    def test_returns_content_length_when_object_exists(
        self, s3_client: S3Client, datasets_bucket: str
    ) -> None:
        body = b"5.1,3.5,1.4,0.2\n6.7,3.1,4.7,1.5\n"
        s3_client.put_object(Bucket=datasets_bucket, Key=KEY, Body=body)

        storage = S3DatasetStorage(s3_client, datasets_bucket)

        assert storage.get_size(KEY) == len(body)


class TestGenerateUploadUrl:
    def test_targets_the_configured_bucket_and_key(
        self, s3_client: S3Client, datasets_bucket: str
    ) -> None:
        storage = S3DatasetStorage(s3_client, datasets_bucket)

        url = storage.generate_upload_url(KEY, expires_in_seconds=300)

        assert datasets_bucket in url
        assert KEY in url
