"""DTO for GET /jobs/{jobId}."""

from __future__ import annotations

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    updated_at: str
    error_message: str | None = None
