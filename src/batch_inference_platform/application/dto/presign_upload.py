"""DTOs for POST /datasets/upload-url."""

from __future__ import annotations

from pydantic import BaseModel


class PresignUploadResponse(BaseModel):
    job_id: str
    upload_url: str
    expires_in_seconds: int
