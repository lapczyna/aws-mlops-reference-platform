from __future__ import annotations

import json
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

pytestmark = pytest.mark.integration


class TestPresignUploadHandler:
    def test_returns_200_with_job_id_and_upload_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        s3_client: S3Client,
        datasets_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        monkeypatch.setenv("JOBS_TABLE_NAME", "unused-by-this-handler")
        monkeypatch.setenv("DATASETS_BUCKET_NAME", datasets_bucket)
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.presign_upload")
        response = module.handler({}, MagicMock())

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body["job_id"]) == 26
        assert datasets_bucket in body["upload_url"]
        assert body["job_id"] in body["upload_url"]
