"""Uniform API Gateway proxy-integration JSON responses."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def json_response(status_code: int, body: dict[str, Any] | BaseModel) -> dict[str, Any]:
    """Build an API Gateway proxy-integration response with a JSON body."""
    payload = body.model_dump_json() if isinstance(body, BaseModel) else json.dumps(body)
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": payload,
    }
