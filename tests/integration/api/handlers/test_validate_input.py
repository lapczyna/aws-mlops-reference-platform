from __future__ import annotations

from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client

pytestmark = pytest.mark.integration

JOB_ID = "01ARZ3NDEKTSV4RRFFQ69G5FAV"
INPUT_KEY = f"uploads/{JOB_ID}/input.csv"


class TestValidateInputHandler:
    def test_reports_valid_when_dataset_exists(
        self,
        monkeypatch: pytest.MonkeyPatch,
        s3_client: S3Client,
        datasets_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        s3_client.put_object(Bucket=datasets_bucket, Key=INPUT_KEY, Body=b"5.1,3.5,1.4,0.2")
        monkeypatch.setenv("JOBS_TABLE_NAME", "unused-by-this-handler")
        monkeypatch.setenv("DATASETS_BUCKET_NAME", datasets_bucket)
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.validate_input")
        result = module.handler({"job_id": JOB_ID, "input_s3_key": INPUT_KEY}, MagicMock())

        assert result == {"valid": True, "reason": None}

    def test_reports_invalid_when_dataset_missing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        s3_client: S3Client,
        datasets_bucket: str,
        import_handler: Callable[[str], ModuleType],
    ) -> None:
        monkeypatch.setenv("JOBS_TABLE_NAME", "unused-by-this-handler")
        monkeypatch.setenv("DATASETS_BUCKET_NAME", datasets_bucket)
        monkeypatch.setenv("RESULTS_BUCKET_NAME", "unused-by-this-handler")

        module = import_handler("batch_inference_platform.api.handlers.validate_input")
        result = module.handler({"job_id": JOB_ID, "input_s3_key": INPUT_KEY}, MagicMock())

        assert result["valid"] is False
        assert "not found" in result["reason"]
