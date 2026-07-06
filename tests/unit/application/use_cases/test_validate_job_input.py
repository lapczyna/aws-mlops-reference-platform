import pytest

from batch_inference_platform.application.use_cases.validate_job_input import ValidateJobInput
from tests.unit.fakes import FakeDatasetStorage

pytestmark = pytest.mark.unit

KEY = "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"


class TestValidateJobInput:
    def test_valid_when_dataset_exists_and_nonempty(self) -> None:
        use_case = ValidateJobInput(FakeDatasetStorage(sizes={KEY: 100}))

        result = use_case.execute(KEY)

        assert result.valid is True
        assert result.reason is None

    def test_invalid_when_dataset_missing(self) -> None:
        use_case = ValidateJobInput(FakeDatasetStorage())

        result = use_case.execute(KEY)

        assert result.valid is False
        assert result.reason is not None
        assert "not found" in result.reason

    def test_invalid_when_dataset_empty(self) -> None:
        use_case = ValidateJobInput(FakeDatasetStorage(sizes={KEY: 0}))

        result = use_case.execute(KEY)

        assert result.valid is False
        assert result.reason is not None
        assert "empty" in result.reason
