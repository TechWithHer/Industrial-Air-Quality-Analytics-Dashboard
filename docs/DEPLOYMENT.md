# Production Deployment Guide

**Version**: 2.0.0  
**Status**: Production Ready

---

## Prerequisites

### AWS Account Requirements

- [ ] AWS Account with admin access
- [ ] AWS CLI v2.13+ installed
- [ ] Terraform v1.5+ installed
- [ ] Python 3.11+ installed
- [ ] Git configured

### Service Quotas

- Lambda: 100 concurrent
- S3: 100 buckets
- Athena: 100 concurrent queries
- CloudWatch: 1000 alarms

---

## Development Environment (10 minutes)

### 1. Clone Repository

```bash
git clone https://github.com/TechWithHer/Industrial-Air-Quality-Analytics-Dashboard.git
cd Industrial-Air-Quality-Analytics-Dashboard
```

### 2. Python Setup

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate     # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. AWS Configuration

```bash
aws configure --profile air-quality-dev
# Enter: Access Key, Secret Key, Region (ap-southeast-1), Format (json)

aws sts get-caller-identity --profile air-quality-dev
```

### 4. Terraform Backend

```bash
cd terraform/environments/dev

# Create backend S3 bucket (one-time)
aws s3api create-bucket \\
  --bucket air-quality-terraform-state \\
  --region ap-southeast-1 \\
  --create-bucket-configuration LocationConstraint=ap-southeast-1 \\
  --profile air-quality-dev

# Enable versioning
aws s3api put-bucket-versioning \\
  --bucket air-quality-terraform-state \\
  --versioning-configuration Status=Enabled \\
  --profile air-quality-dev

# Initialize Terraform
terraform init
```

### 5. Create Variables File

```bash
cp ../../terraform.dev.tfvars.example terraform.dev.tfvars

# Edit with your values
cat > terraform.dev.tfvars << 'EOF'
environment              = "dev"
aws_region              = "ap-southeast-1"
aws_account_id          = "123456789012"  # Your account ID
raw_bucket_name         = "air-quality-raw-dev"
processed_bucket_name   = "air-quality-processed-dev"
dashboard_bucket_name   = "air-quality-dashboard-dev"
athena_results_bucket_name = "air-quality-athena-results-dev"
cloudwatch_alarm_email  = "your-email@example.com"
lambda_memory           = 256
data_retention_days     = 30
enable_xray_tracing     = true
xray_sampling_rate      = 1.0  # 100% in dev
EOF
```

### 6. Deploy Development Environment

```bash
# Plan
terraform plan -var-file=terraform.dev.tfvars -out=tfplan

# Apply (takes ~10 minutes)
terraform apply tfplan

# Save outputs
terraform output -json > outputs.json
```

### 7. Verify Deployment

```bash
# Check S3 buckets
aws s3 ls --profile air-quality-dev | grep air-quality

# Check Lambdas
aws lambda list-functions --profile air-quality-dev | grep air-quality

# Manual ingestion test
aws lambda invoke \\
  --function-name air-quality-nea-ingestion-dev \\
  --payload '{}' \\
  /tmp/response.json \\
  --profile air-quality-dev

# View response
cat /tmp/response.json
```

---

## Production Deployment (30 minutes)

### 1. Pre-Production Checks

```bash
# Run tests
pytest tests/unit -v
pytest tests/integration -v

# Security scans
trivy image --severity MEDIUM lambdas/
checkov --framework terraform terraform/

# Code review
git log --oneline main..HEAD
```

### 2. Production Setup

```bash
cd terraform/environments/prod

cat > terraform.prod.tfvars << 'EOF'
environment                     = "prod"
aws_region                      = "ap-southeast-1"
aws_account_id                  = "987654321098"  # Prod account
raw_bucket_name                 = "air-quality-raw-prod"
processed_bucket_name           = "air-quality-processed-prod"
dashboard_bucket_name           = "air-quality-dashboard-prod"
athena_results_bucket_name      = "air-quality-athena-results-prod"
cloudwatch_alarm_email          = "oncall@example.com"
lambda_memory                   = 512  # Higher for prod
lambda_timeout                  = 120
data_retention_days             = 365
glacier_transition_days         = 90
enable_xray_tracing             = true
xray_sampling_rate              = 0.1  # 10% sampling
enable_multi_region_replication = true
backup_region                   = "ap-southeast-2"
enable_dynamodb_alerts          = true
EOF
```

### 3. Production Deployment

```bash
terraform init

# Plan with approval
terraform plan \\
  -var-file=terraform.prod.tfvars \\
  -out=tfplan-prod

# **CRITICAL REVIEW**
# - No accidental deletions?
# - All Lambdas deployed?
# - S3 lifecycle correct?
# - CloudFront enabled?

# Apply
terraform apply tfplan-prod
```

### 4. Post-Deployment Verification

```bash
# Smoke tests
aws s3 ls s3://air-quality-raw-prod/ --recursive

# Lambda test
aws lambda invoke \\
  --function-name air-quality-nea-ingestion-prod \\
  --payload '{}' \\
  /tmp/prod-response.json

# Dashboard
open https://d123456abc.cloudfront.net

# CloudWatch
aws logs tail /aws/lambda/air-quality-nea-ingestion-prod --follow
```

---

## Rollback Procedures

### Terraform Rollback

```bash
# Revert last commit
git revert HEAD

# Refresh state
terraform refresh -var-file=terraform.prod.tfvars

# Reapply
terraform apply -var-file=terraform.prod.tfvars
```

### Lambda Rollback

```bash
# List versions
aws lambda list-versions-by-function \\
  --function-name air-quality-nea-ingestion-prod

# Update alias to previous version
aws lambda update-alias \\
  --function-name air-quality-nea-ingestion-prod \\
  --name LIVE \\
  --function-version 5
```

### Dashboard Rollback

```bash
# Invalidate CloudFront
aws cloudfront create-invalidation \\
  --distribution-id E123ABC456 \\
  --paths "/*"

# Restore from backup
aws s3 sync s3://air-quality-dashboard-backup/ \\
  s3://air-quality-dashboard-prod/ \\
  --delete
```

---

## Troubleshooting

### State Lock

```bash
terraform force-unlock LOCK_ID
```

### Lambda Timeout

```bash
aws lambda update-function-configuration \\
  --function-name air-quality-nea-ingestion-prod \\
  --timeout 120
```

### S3 Access Denied

```bash
aws iam get-role-policy \\
  --role-name air-quality-lambda-execution \\
  --policy-name inline-policy
```

### EventBridge Not Triggering

```bash
aws events describe-rule \\
  --name air-quality-ingestion-schedule

aws events list-targets-by-rule \\
  --rule air-quality-ingestion-schedule
```

---

## Pre-Production Checklist

- [ ] All tests passing
- [ ] Security scans passed
- [ ] Code review approved
- [ ] Architecture reviewed
- [ ] Runbooks updated
- [ ] On-call briefed
- [ ] Rollback plan documented
- [ ] Monitoring alarms configured
- [ ] Dashboard tested
- [ ] Team notified

---

**Emergency Support**: devops-oncall@example.com