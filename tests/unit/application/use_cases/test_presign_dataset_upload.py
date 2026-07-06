import pytest

from batch_inference_platform.application.use_cases.presign_dataset_upload import (
    PresignDatasetUpload,
)
from tests.unit.fakes import FakeDatasetStorage

pytestmark = pytest.mark.unit


class TestPresignDatasetUpload:
    def test_generates_job_id_and_upload_url(self) -> None:
        storage = FakeDatasetStorage()
        use_case = PresignDatasetUpload(storage, url_expiry_seconds=600)

        response = use_case.execute()

        assert len(response.job_id) == 26
        assert response.expires_in_seconds == 600
        assert response.job_id in response.upload_url
        assert storage.upload_url_calls == [f"uploads/{response.job_id}/input.csv"]

    def test_each_call_generates_a_distinct_job_id(self) -> None:
        use_case = PresignDatasetUpload(FakeDatasetStorage())

        first = use_case.execute()
        second = use_case.execute()

        assert first.job_id != second.job_id
