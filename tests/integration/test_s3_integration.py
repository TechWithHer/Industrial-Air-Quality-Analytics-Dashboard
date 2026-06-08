# Sample integration test with LocalStack

import json
import pytest
import boto3
from botocore.exceptions import ClientError


class TestS3Integration:
    """Integration tests for S3 operations"""

    @pytest.mark.integration
    @pytest.mark.s3
    def test_s3_bucket_creation_and_write(self, s3_client, s3_bucket):
        """Test S3 bucket creation and file writing"""
        # Create test data
        test_data = {
            "source": "nea",
            "metric": "psi",
            "timestamp": "2026-06-08T14:00:00",
            "data": {"central": 85, "east": 72},
        }

        # Write to S3
        s3_client.put_object(
            Bucket=s3_bucket,
            Key="year=2026/month=06/day=08/hour=14/nea_psi.json",
            Body=json.dumps(test_data),
        )

        # Read from S3
        response = s3_client.get_object(
            Bucket=s3_bucket,
            Key="year=2026/month=06/day=08/hour=14/nea_psi.json",
        )
        content = json.loads(response["Body"].read().decode())

        assert content["source"] == "nea"
        assert content["metric"] == "psi"
        assert content["data"]["central"] == 85

    @pytest.mark.integration
    @pytest.mark.s3
    def test_s3_partition_structure(self, s3_client, s3_bucket):
        """Test S3 partition directory structure"""
        # Create files in partition structure
        partitions = [
            "year=2026/month=06/day=08/hour=14/nea_psi.json",
            "year=2026/month=06/day=08/hour=15/nea_psi.json",
            "year=2026/month=06/day=09/hour=14/nea_psi.json",
        ]

        for partition in partitions:
            s3_client.put_object(
                Bucket=s3_bucket, Key=partition, Body=json.dumps({"test": "data"})
            )

        # List objects with prefix
        response = s3_client.list_objects_v2(
            Bucket=s3_bucket, Prefix="year=2026/month=06/day=08/"
        )

        assert response["KeyCount"] == 2  # Two files in this partition

    @pytest.mark.integration
    @pytest.mark.s3
    def test_s3_list_objects_pagination(self, s3_client, s3_bucket):
        """Test S3 pagination for large datasets"""
        # Create many objects
        for i in range(15):
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=f"year=2026/month=06/day=08/hour={i:02d}/data_{i}.json",
                Body=json.dumps({"index": i}),
            )

        # Paginate through results
        paginator = s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=s3_bucket, PaginationConfig={"PageSize": 5})

        total_objects = 0
        for page in pages:
            total_objects += page.get("KeyCount", 0)

        assert total_objects == 15


class TestSNSIntegration:
    """Integration tests for SNS alerting"""

    @pytest.mark.integration
    def test_sns_topic_creation(self, sns_client):
        """Test SNS topic creation"""
        response = sns_client.create_topic(Name="air-quality-alerts")
        topic_arn = response["TopicArn"]

        assert "air-quality-alerts" in topic_arn
        assert "arn:aws:sns:" in topic_arn

    @pytest.mark.integration
    def test_sns_publish_message(self, sns_client):
        """Test publishing SNS message"""
        # Create topic
        response = sns_client.create_topic(Name="test-alerts")
        topic_arn = response["TopicArn"]

        # Publish message
        message_response = sns_client.publish(
            TopicArn=topic_arn,
            Subject="Haze Alert",
            Message="PSI > 100 detected",
        )

        assert "MessageId" in message_response
        assert message_response["ResponseMetadata"]["HTTPStatusCode"] == 200


class TestSQSIntegration:
    """Integration tests for SQS DLQ"""

    @pytest.mark.integration
    def test_sqs_queue_creation(self, sqs_client):
        """Test SQS queue creation"""
        response = sqs_client.create_queue(QueueName="air-quality-dlq")
        queue_url = response["QueueUrl"]

        assert "air-quality-dlq" in queue_url

    @pytest.mark.integration
    def test_sqs_send_receive_message(self, sqs_client):
        """Test sending and receiving SQS messages"""
        # Create queue
        response = sqs_client.create_queue(QueueName="test-queue")
        queue_url = response["QueueUrl"]

        # Send message
        sqs_client.send_message(
            QueueUrl=queue_url, MessageBody=json.dumps({"error": "test error"})
        )

        # Receive message
        messages = sqs_client.receive_message(QueueUrl=queue_url)
        assert "Messages" in messages
        assert len(messages["Messages"]) == 1

        message_body = json.loads(messages["Messages"][0]["Body"])
        assert message_body["error"] == "test error"
