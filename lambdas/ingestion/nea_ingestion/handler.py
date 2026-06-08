#!/usr/bin/env python3
"""
NEA Data Ingestion Lambda Handler

Fetches air quality data from Singapore's National Environment Agency (NEA)
via data.gov.sg API and writes to S3 for processing.

API Endpoints:
  - PSI: https://api.data.gov.sg/v1/environment/psi
  - PM2.5: https://api.data.gov.sg/v1/environment/pm25
  - Temperature: https://api.data.gov.sg/v1/environment/air-temperature

No API key required, no rate limiting for reasonable use.
"""

import json
import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any

import boto3
from aws_lambda_powertools import Logger, Tracer, Metrics
from aws_lambda_powertools.utilities.typing import LambdaContext

# Initialize AWS clients
s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')

# Initialize observability
logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Configuration from environment
S3_RAW_BUCKET = os.environ.get('S3_RAW_BUCKET', 'air-quality-raw')
NEA_PSI_API = os.environ.get('NEA_PSI_API', 'https://api.data.gov.sg/v1/environment/psi')
NEA_PM25_API = os.environ.get('NEA_PM25_API', 'https://api.data.gov.sg/v1/environment/pm25')
NEA_TEMP_API = os.environ.get('NEA_TEMP_API', 'https://api.data.gov.sg/v1/environment/air-temperature')
REQUEST_TIMEOUT = 10


class NEADataFetcher:
    """Fetches air quality data from Singapore NEA API"""
    
    def __init__(self):
        self.logger = logger
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'air-quality-platform/2.0',
            'Accept': 'application/json'
        }
    
    @tracer.capture_method
    def fetch_psi(self) -> Dict[str, Any]:
        """Fetch PSI data from NEA"""
        try:
            response = self.session.get(
                NEA_PSI_API,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            self.logger.info("PSI fetch successful", extra={
                "api": "nea_psi",
                "records": len(data.get('items', []))
            })
            
            return {
                'source': 'nea',
                'metric': 'psi',
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"PSI fetch failed: {str(e)}", extra={
                "api": "nea_psi"
            })
            raise
    
    @tracer.capture_method
    def fetch_pm25(self) -> Dict[str, Any]:
        """Fetch PM2.5 data from NEA"""
        try:
            response = self.session.get(
                NEA_PM25_API,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            self.logger.info("PM2.5 fetch successful", extra={
                "api": "nea_pm25",
                "records": len(data.get('items', []))
            })
            
            return {
                'source': 'nea',
                'metric': 'pm25',
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"PM2.5 fetch failed: {str(e)}", extra={
                "api": "nea_pm25"
            })
            raise
    
    @tracer.capture_method
    def fetch_temperature(self) -> Dict[str, Any]:
        """Fetch temperature data from NEA"""
        try:
            response = self.session.get(
                NEA_TEMP_API,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            self.logger.info("Temperature fetch successful", extra={
                "api": "nea_temperature",
                "records": len(data.get('items', []))
            })
            
            return {
                'source': 'nea',
                'metric': 'temperature',
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Temperature fetch failed: {str(e)}", extra={
                "api": "nea_temperature"
            })
            raise


class S3DataWriter:
    """Writes data to S3 with partition structure"""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.logger = logger
    
    @staticmethod
    def _get_partition_path(timestamp: str) -> str:
        """Generate S3 partition path: year/month/day/hour"""
        dt = datetime.fromisoformat(timestamp)
        return f"year={dt.year}/month={dt.month:02d}/day={dt.day:02d}/hour={dt.hour:02d}"
    
    @tracer.capture_method
    def write_data(self, metric: str, data: Dict[str, Any]) -> str:
        """Write data to S3 and return object key"""
        timestamp = data.get('timestamp', datetime.utcnow().isoformat())
        partition = self._get_partition_path(timestamp)
        
        # Generate unique S3 key
        s3_key = f"{partition}/nea_{metric}_{int(datetime.utcnow().timestamp() * 1000)}.json"
        
        try:
            # Write to S3
            s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=json.dumps(data, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256',
                Metadata={
                    'source': 'nea',
                    'metric': metric,
                    'ingestion-timestamp': datetime.utcnow().isoformat()
                }
            )
            
            self.logger.info(f"Data written to S3", extra={
                "bucket": self.bucket,
                "key": s3_key,
                "metric": metric
            })
            
            # CloudWatch metric
            metrics.add_metric(
                name="NEADataIngested",
                unit="Count",
                value=1,
                dimensions={"Metric": metric}
            )
            
            return s3_key
            
        except Exception as e:
            self.logger.error(f"S3 write failed: {str(e)}", extra={
                "key": s3_key
            })
            metrics.add_metric(
                name="NEADataIngestionError",
                unit="Count",
                value=1
            )
            raise


def validate_response(response: Dict[str, Any], metric: str) -> bool:
    """Validate NEA API response"""
    if not isinstance(response, dict):
        logger.warn(f"Invalid response type for {metric}")
        return False
    
    if 'items' not in response or not isinstance(response['items'], list):
        logger.warn(f"Invalid items in {metric}")
        return False
    
    return True


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_cold_start_metric
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda handler: Ingest NEA data and write to S3
    
    Args:
        event: EventBridge scheduled event
        context: Lambda context
    
    Returns:
        Response dict with ingestion status
    """
    
    logger.info("NEA Ingestion started", extra={
        "request_id": context.request_id,
        "remaining_time_ms": context.get_remaining_time_in_millis()
    })
    
    fetcher = NEADataFetcher()
    writer = S3DataWriter(S3_RAW_BUCKET)
    results = {
        'status': 'success',
        'ingested': [],
        'failed': [],
        'errors': []
    }
    
    # Fetch and write each metric
    for metric_name, fetch_fn in [
        ('psi', fetcher.fetch_psi),
        ('pm25', fetcher.fetch_pm25),
        ('temperature', fetcher.fetch_temperature)
    ]:
        try:
            # Fetch
            data = fetch_fn()
            
            # Validate
            if not validate_response(data['data'], metric_name):
                raise ValueError(f"Invalid {metric_name} response")
            
            # Write
            s3_key = writer.write_data(metric_name, data)
            results['ingested'].append({
                'metric': metric_name,
                's3_key': s3_key
            })
            
        except Exception as e:
            error_msg = f"Failed to ingest {metric_name}: {str(e)}"
            logger.error(error_msg)
            results['failed'].append(metric_name)
            results['errors'].append(error_msg)
    
    # Set overall status
    if len(results['failed']) == 3:
        results['status'] = 'failed'
    elif len(results['failed']) > 0:
        results['status'] = 'partial_success'
    
    # Flush metrics
    metrics.flush()
    
    logger.info("NEA Ingestion completed", extra={
        "status": results['status'],
        "ingested_count": len(results['ingested']),
        "failed_count": len(results['failed'])
    })
    
    return results