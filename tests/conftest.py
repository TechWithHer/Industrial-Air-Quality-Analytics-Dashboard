# conftest.py - Shared pytest fixtures for all tests

import os
import boto3
import pytest
from moto import mock_s3, mock_lambda, mock_sns, mock_sqs


@pytest.fixture(scope="session")
def aws_credentials():
    """Fixture to set AWS credentials for testing"""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-1"


@pytest.fixture
def s3_client(aws_credentials):
    """Fixture for mocked S3 client"""
    with mock_s3():
        client = boto3.client("s3", region_name="ap-southeast-1")
        yield client


@pytest.fixture
def s3_bucket(s3_client):
    """Fixture for S3 bucket"""
    bucket_name = "test-air-quality-raw"
    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"},
    )
    yield bucket_name


@pytest.fixture
def sns_client(aws_credentials):
    """Fixture for mocked SNS client"""
    with mock_sns():
        client = boto3.client("sns", region_name="ap-southeast-1")
        yield client


@pytest.fixture
def sqs_client(aws_credentials):
    """Fixture for mocked SQS client"""
    with mock_sqs():
        client = boto3.client("sqs", region_name="ap-southeast-1")
        yield client


@pytest.fixture
def lambda_client(aws_credentials):
    """Fixture for mocked Lambda client"""
    with mock_lambda():
        client = boto3.client("lambda", region_name="ap-southeast-1")
        yield client


@pytest.fixture
def sample_nea_response():
    """Fixture for sample NEA API response"""
    return {
        "items": [
            {
                "timestamp": "2026-06-08T14:00:00+08:00",
                "readings": {
                    "psi_twenty_four_hourly": [
                        {"region": "central", "value": 85},
                        {"region": "east", "value": 72},
                    ]
                },
            }
        ],
        "api_info": {"status": "Success"},
    }


@pytest.fixture
def sample_openaq_response():
    """Fixture for sample OpenAQ API response"""
    return {
        "results": [
            {
                "location": "Jakarta Central",
                "measurements": [
                    {"parameter": "pm25", "value": 120, "unit": "µg/m³"},
                    {"parameter": "o3", "value": 45, "unit": "µg/m³"},
                ],
                "lastUpdated": "2026-06-08T14:00:00Z",
            }
        ],
        "meta": {"page": 1, "limit": 100},
    }


@pytest.fixture
def temp_env():
    """Fixture to safely modify environment variables"""
    original_env = os.environ.copy()
    yield os.environ
    os.environ.clear()
    os.environ.update(original_env)
