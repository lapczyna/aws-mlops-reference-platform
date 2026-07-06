import pytest

from batch_inference_platform.domain.value_objects.job_status import JobStatus

pytestmark = pytest.mark.unit


class TestJobStatusIsTerminal:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (JobStatus.SUBMITTED, False),
            (JobStatus.PROCESSING, False),
            (JobStatus.COMPLETED, True),
            (JobStatus.FAILED, True),
        ],
    )
    def test_is_terminal(self, status: JobStatus, expected: bool) -> None:
        assert status.is_terminal is expected
