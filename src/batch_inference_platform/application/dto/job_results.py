"""DTO for GET /jobs/{jobId}/results."""

from __future__ import annotations

from pydantic import BaseModel


class JobResultsResponse(BaseModel):
    download_url: str
    expires_in_seconds: int
