# Terraform Variables - Production Configuration

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-southeast-1"
}

variable "aws_account_id" {
  description = "AWS account ID"
  type        = string
}

variable "raw_bucket_name" {
  description = "S3 bucket for raw data ingestion"
  type        = string
}

variable "processed_bucket_name" {
  description = "S3 bucket for processed Parquet data"
  type        = string
}

variable "dashboard_bucket_name" {
  description = "S3 bucket for dashboard static files"
  type        = string
}

variable "athena_results_bucket_name" {
  description = "S3 bucket for Athena query results"
  type        = string
}

variable "cloudwatch_alarm_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
}

variable "lambda_memory" {
  description = "Lambda function memory allocation (MB)"
  type        = number
  default     = 256
  validation {
    condition     = var.lambda_memory >= 128 && var.lambda_memory <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Lambda function timeout (seconds)"
  type        = number
  default     = 60
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "data_retention_days" {
  description = "Number of days to retain raw data before deletion"
  type        = number
  default     = 365
}

variable "glacier_transition_days" {
  description = "Days before transitioning data to Glacier"
  type        = number
  default     = 90
}

variable "ingestion_schedule_expression" {
  description = "EventBridge cron schedule for data ingestion"
  type        = string
  default     = "cron(0/15 * * * ? *)"  # Every 15 minutes
}

variable "enable_xray_tracing" {
  description = "Enable X-Ray distributed tracing"
  type        = bool
  default     = true
}

variable "xray_sampling_rate" {
  description = "X-Ray sampling rate (0.0 to 1.0)"
  type        = number
  default     = 0.1
  validation {
    condition     = var.xray_sampling_rate >= 0.0 && var.xray_sampling_rate <= 1.0
    error_message = "X-Ray sampling rate must be between 0.0 and 1.0."
  }
}

variable "enable_multi_region_replication" {
  description = "Enable S3 cross-region replication for disaster recovery"
  type        = bool
  default     = false
}

variable "backup_region" {
  description = "AWS region for backup replication"
  type        = string
  default     = "ap-southeast-2"
}

variable "common_tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default = {
    Project     = "Air Quality Analytics Platform"
    ManagedBy   = "Terraform"
    CreatedAt   = "2026-06-08"
  }
}