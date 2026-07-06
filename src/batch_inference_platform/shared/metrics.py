"""Custom CloudWatch metrics (EMF) for business-relevant job outcomes.

The `BatchInferencePlatform` namespace matches the `cloudwatch:namespace`
condition on RecordOutcomeFunction's IAM policy in template.yaml -- the one
function permitted to emit metrics can only ever emit them into this
namespace.
"""

from __future__ import annotations

from aws_lambda_powertools import Metrics

_NAMESPACE = "BatchInferencePlatform"


def get_metrics(service: str) -> Metrics:
    """Create a Powertools Metrics instance scoped to the platform's namespace."""
    return Metrics(namespace=_NAMESPACE, service=service)
