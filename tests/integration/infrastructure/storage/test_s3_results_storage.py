from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from batch_inference_platform.infrastructure.storage.s3_results_storage import S3ResultsStorage

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

pytestmark = pytest.mark.integration

KEY = "predictions/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv.out"


class TestGenerateDownloadUrl:
    def test_targets_the_configured_bucket_and_key(
        self, s3_client: S3Client, results_bucket: str
    ) -> None:
        storage = S3ResultsStorage(s3_client, results_bucket)

        url = storage.generate_download_url(KEY, expires_in_seconds=300)

        assert results_bucket in url
        assert KEY in url
