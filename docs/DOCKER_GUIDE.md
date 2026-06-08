# Docker and Local Testing Guide

**Version**: 2.0.0  
**Status**: Production Ready

---

## Overview

This guide explains how to use Docker for:
1. **Local Lambda Testing** - Test Lambda functions before deploying to AWS
2. **Integration Testing** - Full pipeline testing with LocalStack
3. **Dashboard Development** - Local development server with hot-reload

---

## Prerequisites

```bash
# Install Docker Desktop
# https://www.docker.com/products/docker-desktop

# Verify installation
docker --version      # Docker version 20+
docker-compose --version  # 2.0+

# Verify Docker daemon is running
docker ps
```

---

## Quick Start

### Option 1: Full Local Environment (Recommended)

This starts LocalStack + Lambda + Tests + Dashboard

```bash
# Start all services
docker-compose up

# In another terminal, run tests
docker-compose --profile test up

# Access dashboard
open http://localhost:3000
```

### Option 2: Just LocalStack (For S3/SNS/etc)

```bash
# Start only LocalStack
docker-compose up localstack s3-setup

# LocalStack is now at http://localhost:4566
aws s3 ls --endpoint-url http://localhost:4566
```

### Option 3: Just Lambda Testing

```bash
# Start Lambda runtime
docker-compose --profile lambda up lambda-test

# Test locally via HTTP
curl -X POST http://localhost:9001/2015-03-31/functions/function/invocations \
  -d '{}'
```

### Option 4: Just Integration Tests

```bash
# Run tests against LocalStack
docker-compose --profile test up
```

### Option 5: Just Dashboard

```bash
# Start dashboard dev server
docker-compose --profile dashboard up dashboard

# Access at http://localhost:3000
# Auto-reloads on file changes
```

---

## Detailed Usage

### Lambda Local Testing

#### What It Does
- Runs Lambda code in AWS-identical Python 3.11 environment
- No need to deploy to AWS to test
- Perfect for pre-deployment validation

#### Start Lambda Container

```bash
# Start LocalStack first
docker-compose up localstack s3-setup

# In another terminal, start Lambda
docker-compose --profile lambda up lambda-test

# Lambda is now running at http://localhost:9001
```

#### Invoke Lambda via HTTP

```bash
# Test NEA ingestion
curl -X POST http://localhost:9001/2015-03-31/functions/function/invocations \
  -H "Content-Type: application/json" \
  -d '{}'

# Response will show success/error
```

#### Check Lambda Logs

```bash
# View Docker logs
docker logs air-quality-lambda-test

# Follow logs in real-time
docker logs -f air-quality-lambda-test
```

#### Common Issues

**Issue: "Connection refused"**
```bash
# Lambda container can't connect to LocalStack
# Make sure both are on same network and LocalStack is healthy
docker-compose up localstack s3-setup  # Wait for health check
```

**Issue: "Module not found"**
```bash
# Dependencies not installed
# Rebuild the image
docker-compose build --no-cache lambda-test
```

---

### Integration Testing

#### What It Does
- Tests entire pipeline: S3 → Lambda → Athena
- Uses LocalStack to simulate AWS without credentials
- Runs pytest suite in isolated environment

#### Run Tests

```bash
# Option 1: Run tests via Docker Compose
docker-compose --profile test up

# Option 2: Run specific test file
docker-compose --profile test run integration-tests pytest tests/integration/test_s3_workflow.py -v

# Option 3: Run with coverage
docker-compose --profile test run integration-tests pytest tests/ --cov=lambdas --cov-report=html
```

#### View Test Results

```bash
# After tests complete
# Coverage report is in: htmlcov/index.html
open htmlcov/index.html

# View container logs
docker logs air-quality-tests
```

#### Test Structure

```
tests/
├── unit/                          # Unit tests (no AWS calls)
│   ├── test_nea_ingestion.py
│   ├── test_transformation.py
│   └── test_anomaly_detection.py
└── integration/                   # Integration tests (with LocalStack)
    ├── test_s3_workflow.py       # S3 operations
    ├── test_lambda_invocation.py # Lambda execution
    └── test_end_to_end.py        # Full pipeline
```

#### Create New Tests

```python
# tests/integration/test_custom.py
import boto3
import pytest


@pytest.fixture
def s3_client():
    """S3 client pointing to LocalStack"""
    return boto3.client(
        's3',
        endpoint_url='http://localstack:4566',
        region_name='ap-southeast-1'
    )


def test_s3_bucket_creation(s3_client):
    """Test S3 bucket operations"""
    # Create bucket
    s3_client.create_bucket(
        Bucket='test-bucket',
        CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-1'}
    )
    
    # Put object
    s3_client.put_object(
        Bucket='test-bucket',
        Key='test-file.json',
        Body=b'{"test": "data"}'
    )
    
    # Get object
    response = s3_client.get_object(Bucket='test-bucket', Key='test-file.json')
    assert response['Body'].read() == b'{"test": "data"}'
```

---

### Dashboard Development

#### What It Does
- Runs Chart.js dashboard in development mode
- Auto-reloads on file changes
- Mock API integration ready

#### Start Dashboard

```bash
# Start dashboard dev server
docker-compose --profile dashboard up dashboard

# Access at http://localhost:3000
```

#### Development Workflow

```bash
# 1. Edit dashboard files in editor
# vim dashboard/index.html

# 2. Changes auto-reload in browser
# Browser automatically refreshes

# 3. View hot-reload logs
docker logs -f air-quality-dashboard-dev
```

#### Connect to Local API

```javascript
// dashboard/js/api.js
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:9000';

async function fetchAirQuality() {
  const response = await fetch(`${API_URL}/air-quality/latest`);
  return response.json();
}
```

#### Common Issues

**Issue: "Port 3000 already in use"**
```bash
# Change port in docker-compose.yml
# ports:
#   - "3001:3000"  # Changed from 3000:3000

docker-compose --profile dashboard up
open http://localhost:3001
```

---

## Complete Development Workflow

### Day-to-Day Development

```bash
# 1. Start all services
docker-compose up

# Wait for LocalStack health check (look for "✓ Ready")

# 2. In new terminal, run tests while developing
docker-compose --profile test run integration-tests pytest tests/ -v --tb=short

# 3. Start dashboard
docker-compose --profile dashboard up dashboard

# 4. Edit Lambda code in your editor
vim lambdas/ingestion/nea_ingestion/handler.py

# 5. Rebuild and test
docker-compose build lambda-test
docker-compose --profile lambda up lambda-test

# 6. Test via curl
curl -X POST http://localhost:9001/2015-03-31/functions/function/invocations \
  -d '{}'

# 7. View logs
docker logs -f air-quality-lambda-test

# 8. When ready, deploy to AWS
cd terraform/environments/dev
terraform apply -var-file=terraform.dev.tfvars
```

---

## Cleaning Up

### Stop All Containers

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes LocalStack data)
docker-compose down -v

# Stop only specific service
docker-compose stop lambda-test
```

### Remove Docker Images

```bash
# Remove specific image
docker rmi air-quality-lambda-test

# Remove all unused images
docker image prune -a

# Remove specific container
docker rm air-quality-lambda-test
```

### Free Up Space

```bash
# Remove all stopped containers
docker container prune

# Remove all dangling volumes
docker volume prune

# Complete cleanup (careful!)
docker system prune -a
```

---

## LocalStack AWS CLI Usage

### Configure AWS CLI for LocalStack

```bash
# Create AWS profile for LocalStack
aws configure --profile localstack

# Enter:
# AWS Access Key ID: testing
# AWS Secret Access Key: testing
# Default region: ap-southeast-1
# Default output format: json
```

### Use AWS CLI with LocalStack

```bash
# S3 operations
aws s3 ls --endpoint-url http://localhost:4566 --profile localstack
aws s3 mb s3://my-bucket --endpoint-url http://localhost:4566 --profile localstack

# SNS operations
aws sns list-topics --endpoint-url http://localhost:4566 --profile localstack

# SQS operations
aws sqs list-queues --endpoint-url http://localhost:4566 --profile localstack

# Lambda operations
aws lambda list-functions --endpoint-url http://localhost:4566 --profile localstack

# DynamoDB operations
aws dynamodb list-tables --endpoint-url http://localhost:4566 --profile localstack
```

---

## Performance Tips

### Optimize Docker for Speed

```bash
# 1. Allocate more resources to Docker Desktop
# Settings → Resources
# CPUs: 4+
# Memory: 4GB+
# Disk: 50GB+

# 2. Use named volumes for LocalStack
docker volume create localstack-data

# 3. Rebuild images only when needed
docker-compose build --no-cache  # Full rebuild
docker-compose build             # Use cache (faster)
```

### Reduce Container Startup Time

```bash
# Pre-pull images
docker-compose pull

# Create containers without starting
docker-compose create

# Start pre-created containers
docker-compose start
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs localstack

# Rebuild everything
docker-compose down -v
docker-compose build --no-cache
docker-compose up
```

### Network connectivity issues

```bash
# Check network
docker network ls
docker network inspect air-quality-network

# Test connectivity between containers
docker-compose exec localstack ping s3-setup
```

### Port already in use

```bash
# Find what's using port 4566
lsof -i :4566  # macOS/Linux
netstat -ano | findstr :4566  # Windows

# Kill process or change Docker port
# Edit docker-compose.yml ports section
```

### High disk usage

```bash
# Clean up Docker
docker system prune -a --volumes

# Remove LocalStack data
rm -rf localstack/

# Rebuild
docker-compose up
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
# .github/workflows/docker-tests.yml
name: Docker Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      localstack:
        image: localstack/localstack:latest
        ports:
          - 4566:4566
        env:
          SERVICES: s3,lambda,events
    steps:
      - uses: actions/checkout@v2
      - name: Build test image
        run: docker-compose build integration-tests
      - name: Run tests
        run: docker-compose --profile test up --abort-on-container-exit
```

---

## Production Deployment

### From Docker to AWS Lambda

```bash
# 1. Build and test locally
docker-compose build lambda-test
docker-compose --profile lambda up lambda-test

# 2. Create ECR repository
aws ecr create-repository --repository-name air-quality-nea-ingestion

# 3. Push to ECR
aws ecr get-login-password --region ap-southeast-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com

docker tag air-quality-lambda-test ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/air-quality-nea-ingestion:latest

docker push ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/air-quality-nea-ingestion:latest

# 4. Create Lambda from container image
aws lambda create-function \
  --function-name air-quality-nea-ingestion \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-role \
  --code ImageUri=ACCOUNT_ID.dkr.ecr.ap-southeast-1.amazonaws.com/air-quality-nea-ingestion:latest \
  --package-type Image
```

---

**End of Docker Guide**
