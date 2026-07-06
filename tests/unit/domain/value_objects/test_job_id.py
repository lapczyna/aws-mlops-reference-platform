import pytest

from batch_inference_platform.domain.value_objects.job_id import JobId

pytestmark = pytest.mark.unit


class TestJobIdGenerate:
    def test_generates_26_character_ulid(self) -> None:
        job_id = JobId.generate()
        assert len(str(job_id)) == 26

    def test_generates_unique_ids(self) -> None:
        assert JobId.generate() != JobId.generate()


class TestJobIdValidation:
    def test_accepts_valid_ulid_string(self) -> None:
        job_id = JobId("01ARZ3NDEKTSV4RRFFQ69G5FAV")
        assert str(job_id) == "01ARZ3NDEKTSV4RRFFQ69G5FAV"

    @pytest.mark.parametrize(
        "value",
        [
            "not-a-valid-ulid",
            "01arz3ndektsv4rrffq69g5fav",  # lowercase
            "01ARZ3NDEKTSV4RRFFQ69G5FA",  # 25 chars
            "01ARZ3NDEKTSV4RRFFQ69G5FAVX",  # 27 chars
            "",
        ],
    )
    def test_rejects_invalid_format(self, value: str) -> None:
        with pytest.raises(ValueError, match="not a valid ULID"):
            JobId(value)
