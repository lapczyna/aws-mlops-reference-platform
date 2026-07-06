"""Structured JSON logging, standardized across every handler.

A thin factory rather than a bare `Logger(...)` call at each call site so
every handler gets the same configuration knobs in one place -- see
docs/standards/coding-standards.md#structured-logging.
"""

from __future__ import annotations

from aws_lambda_powertools import Logger


def get_logger(service: str) -> Logger:
    """Create a Powertools Logger for the given service/handler name.

    Log level is read by Powertools itself from the POWERTOOLS_LOG_LEVEL
    environment variable set in template.yaml; no need to thread it through
    here explicitly.
    """
    return Logger(service=service)
