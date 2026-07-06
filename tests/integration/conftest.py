"""Shared fixtures for integration tests: moto-mocked AWS services.

No integration test in this suite is permitted to call real AWS APIs --
see docs/standards/coding-standards.md#testing.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

import boto3
import pytest
from moto import mock_aws

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import Table
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_stepfunctions.client import SFNClient

AWS_REGION = "us-east-1"
JOBS_TABLE_NAME = "test-batch-inference-jobs"
DATASETS_BUCKET_NAME = "test-batch-inference-datasets"
RESULTS_BUCKET_NAME = "test-batch-inference-results"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fake credentials so a misconfigured test can't accidentally reach real AWS."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", AWS_REGION)


@pytest.fixture
def jobs_table() -> Iterator[Table]:
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.create_table(
            TableName=JOBS_TABLE_NAME,
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        yield table


@pytest.fixture
def s3_client() -> Iterator[S3Client]:
    with mock_aws():
        yield boto3.client("s3", region_name=AWS_REGION)


@pytest.fixture
def datasets_bucket(s3_client: S3Client) -> str:
    s3_client.create_bucket(Bucket=DATASETS_BUCKET_NAME)
    return DATASETS_BUCKET_NAME


@pytest.fixture
def results_bucket(s3_client: S3Client) -> str:
    s3_client.create_bucket(Bucket=RESULTS_BUCKET_NAME)
    return RESULTS_BUCKET_NAME


@pytest.fixture
def sfn_client() -> Iterator[SFNClient]:
    with mock_aws():
        yield boto3.client("stepfunctions", region_name=AWS_REGION)


@pytest.fixture
def state_machine_arn(sfn_client: SFNClient) -> str:
    definition = '{"StartAt": "Pass", "States": {"Pass": {"Type": "Pass", "End": true}}}'
    response = sfn_client.create_state_machine(
        name="test-job-orchestration",
        definition=definition,
        roleArn="arn:aws:iam::123456789012:role/test-role",
    )
    return response["stateMachineArn"]
