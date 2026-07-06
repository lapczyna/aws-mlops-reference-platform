"""Use case: ValidateJobInput (backs the ValidateInput state machine task)."""

from __future__ import annotations

from batch_inference_platform.application.dto.validation_result import ValidationResult
from batch_inference_platform.domain.ports.dataset_storage import DatasetStorage


class ValidateJobInput:
    """Confirms the uploaded dataset exists and is non-empty before processing."""

    def __init__(self, dataset_storage: DatasetStorage) -> None:
        self._dataset_storage = dataset_storage

    def execute(self, input_s3_key: str) -> ValidationResult:
        size = self._dataset_storage.get_size(input_s3_key)
        if size is None:
            return ValidationResult(valid=False, reason=f"Dataset not found at '{input_s3_key}'")
        if size == 0:
            return ValidationResult(valid=False, reason=f"Dataset at '{input_s3_key}' is empty")
        return ValidationResult(valid=True)
