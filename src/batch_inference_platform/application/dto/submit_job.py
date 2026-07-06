"""DTOs for POST /jobs.

`job_id` is deliberately a plain `str` here, not re-validated against the
ULID pattern -- API Gateway's request model already rejects malformed
bodies at the edge, and the domain `JobId` value object is the single
source of truth for that validation when the use case constructs one.
Duplicating the pattern in a second layer would just be two places to keep
in sync.
"""

from __future__ import annotations

from pydantic import BaseModel


class SubmitJobRequest(BaseModel):
    job_id: str


class SubmitJobResponse(BaseModel):
    job_id: str
    status: str
