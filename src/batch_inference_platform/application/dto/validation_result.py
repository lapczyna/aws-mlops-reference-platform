"""DTO returned by the ValidateInput state machine task."""

from __future__ import annotations

from pydantic import BaseModel


class ValidationResult(BaseModel):
    valid: bool
    reason: str | None = None
