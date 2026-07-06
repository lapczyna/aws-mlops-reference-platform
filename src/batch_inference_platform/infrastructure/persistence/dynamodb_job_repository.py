"""DynamoDB adapter implementing the JobRepository port.

Item shape matches docs/architecture/overview.md#data-model-summary. The
`mypy_boto3_dynamodb` import only exists at type-check time (from the dev-only
`boto3-stubs` package); it is never present in the Lambda Layer, hence the
TYPE_CHECKING guard.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from botocore.exceptions import ClientError

from batch_inference_platform.domain.entities.inference_job import InferenceJob
from batch_inference_platform.domain.exceptions.job_exceptions import (
    InvalidJobStateTransitionError,
    JobAlreadyExistsError,
)
from batch_inference_platform.domain.ports.job_repository import JobRepository
from batch_inference_platform.domain.value_objects.job_id import JobId
from batch_inference_platform.domain.value_objects.job_status import JobStatus

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table

_CONDITIONAL_CHECK_FAILED = "ConditionalCheckFailedException"


class DynamoDbJobRepository(JobRepository):
    """Persists InferenceJob aggregates to the Jobs DynamoDB table."""

    def __init__(self, table: Table) -> None:
        self._table = table

    def create(self, job: InferenceJob) -> None:
        try:
            self._table.put_item(
                Item=_to_item(job),
                ConditionExpression="attribute_not_exists(job_id)",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == _CONDITIONAL_CHECK_FAILED:
                raise JobAlreadyExistsError(str(job.job_id)) from exc
            raise

    def get(self, job_id: JobId) -> InferenceJob | None:
        response = self._table.get_item(Key={"job_id": str(job_id)})
        item = response.get("Item")
        return None if item is None else _from_item(item)

    def save(self, job: InferenceJob) -> None:
        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_values: dict[str, Any] = {
            ":status": job.status.value,
            ":updated_at": job.updated_at.isoformat(),
            ":completed": JobStatus.COMPLETED.value,
            ":failed": JobStatus.FAILED.value,
        }
        if job.output_s3_key is not None:
            update_expression += ", output_s3_key = :output_s3_key"
            expression_values[":output_s3_key"] = job.output_s3_key
        if job.error_message is not None:
            update_expression += ", error_message = :error_message"
            expression_values[":error_message"] = job.error_message

        try:
            self._table.update_item(
                Key={"job_id": str(job.job_id)},
                UpdateExpression=update_expression,
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=expression_values,
                # Guards against a duplicate Step Functions retry re-applying
                # a terminal outcome after another invocation already did.
                ConditionExpression="#status <> :completed AND #status <> :failed",
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == _CONDITIONAL_CHECK_FAILED:
                raise InvalidJobStateTransitionError(
                    job_id=str(job.job_id),
                    current_status="COMPLETED or FAILED",
                    attempted_status=job.status.value,
                ) from exc
            raise


def _to_item(job: InferenceJob) -> dict[str, Any]:
    item: dict[str, Any] = {
        "job_id": str(job.job_id),
        "status": job.status.value,
        "input_s3_key": job.input_s3_key,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "ttl": job.ttl,
    }
    if job.output_s3_key is not None:
        item["output_s3_key"] = job.output_s3_key
    if job.error_message is not None:
        item["error_message"] = job.error_message
    return item


def _from_item(item: dict[str, Any]) -> InferenceJob:
    return InferenceJob(
        job_id=JobId(item["job_id"]),
        status=JobStatus(item["status"]),
        input_s3_key=item["input_s3_key"],
        created_at=datetime.fromisoformat(item["created_at"]),
        updated_at=datetime.fromisoformat(item["updated_at"]),
        ttl=int(item["ttl"]),
        output_s3_key=item.get("output_s3_key"),
        error_message=item.get("error_message"),
    )
