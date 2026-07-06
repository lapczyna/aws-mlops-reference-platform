import pytest

from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_paths import dataset_key, prediction_key

pytestmark = pytest.mark.unit

JOB_ID = JobId("01ARZ3NDEKTSV4RRFFQ69G5FAV")


class TestJobPaths:
    def test_dataset_key(self) -> None:
        assert dataset_key(JOB_ID) == "uploads/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv"

    def test_prediction_key_matches_sagemaker_batch_transform_naming(self) -> None:
        # Batch Transform names output "<input filename>.out" -- see ADR-0009.
        assert prediction_key(JOB_ID) == "predictions/01ARZ3NDEKTSV4RRFFQ69G5FAV/input.csv.out"
