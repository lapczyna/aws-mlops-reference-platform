"""Typed, environment-driven configuration (12-factor: config lives in the environment).

Values are populated by `template.yaml`'s Globals/per-function Environment
blocks -- never hard-coded and never read from a checked-in per-environment
file. See docs/standards/coding-standards.md#configuration.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    """Configuration available to Lambda handlers, sourced from environment variables."""

    jobs_table_name: str
    datasets_bucket_name: str
    results_bucket_name: str
    log_level: str = "INFO"
    # Only set on SubmitJobFunction -- see template.yaml.
    state_machine_arn: str | None = None
    job_ttl_days: int = 30


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings once per Lambda execution environment (cached across warm invocations)."""
    return Settings(
        jobs_table_name=_require_env("JOBS_TABLE_NAME"),
        datasets_bucket_name=_require_env("DATASETS_BUCKET_NAME"),
        results_bucket_name=_require_env("RESULTS_BUCKET_NAME"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        state_machine_arn=os.environ.get("STATE_MACHINE_ARN"),
        job_ttl_days=int(os.environ.get("JOB_TTL_DAYS", "30")),
    )
