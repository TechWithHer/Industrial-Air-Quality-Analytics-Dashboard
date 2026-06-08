# Architecture Documentation

## System Design & Technical Specifications

### Version: 2.0.0
### Last Updated: June 2026
### Status: Production Ready

---

## Overview

IAQAP is an event-driven serverless data pipeline designed for real-time air quality monitoring. The system follows a layered architecture:

```
┌─────────────────────────────┐
│ Ingestion Layer │ EventBridge + Lambda
└────────┬────────────────────┘
         ↓
┌─────────────────────────────┐
│ Storage Layer   │ S3 (Raw + Processed)
└────────┬────────────────────┘
         ↓
┌─────────────────────────────┐
│ Analytics Layer │ Athena + Glue
└────────┬────────────────────┘
         ↓
┌─────────────────────────────┐
│ Delivery Layer  │ CloudFront + Dashboard
└────────┬────────────────────┘
         ↓
┌─────────────────────────────┐
│ Alerting Layer  │ Lambda + SNS
└────────┬────────────────────┘
         ↓
┌─────────────────────────────┐
│Observability    │ CloudWatch + X-Ray
└─────────────────────────────┘
```

---

## 1. Ingestion Layer

### EventBridge Rules

```yaml
Rule: air-quality-ingestion-nea
  Schedule: "cron(0/15 * * * ? *)"  # Every 15 minutes
  Targets:
    - Lambda: air-quality-nea-ingestion
    - DeadLetterConfig: SQS DLQ
```

### Lambda Functions

**air-quality-nea-ingestion**
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 60 seconds
- Metrics: Invocations, errors, latency

**air-quality-openaq-ingestion**
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 60 seconds
- Handles: Jakarta, KL, Manila, SG

**air-quality-waqi-ingestion** (Optional)
- Runtime: Python 3.11
- Memory: 256 MB
- Timeout: 60 seconds
- 130+ countries supported

---

## 2. Storage Layer

### S3 Raw Bucket

```
s3://air-quality-raw/
└── year=2026/month=06/day=08/hour=14/
    ├── nea_psi.json
    ├── nea_pm25.json
    ├── openaq_measurements.json
    └── metadata.json
```

**Lifecycle Policy**
- Transition to STANDARD_IA: 30 days
- Transition to GLACIER: 90 days
- Delete: 365 days

### S3 Processed Bucket

```
s3://air-quality-processed/
└── air_quality/year=2026/month=06/day=08/
    └── *.parquet (Snappy compressed)
```

**Schema**
- timestamp, source, country, region
- psi, pm25, pm10, no2, so2, co, o3
- temperature, humidity, wind_speed
- station_id, ingestion_time

### Encryption

```yaml
Type: SSE-S3 (default) or SSE-KMS (high-security)
Versioning: Enabled
Block Public Access: All enabled
```

---

## 3. Transformation Layer

### Lambda: air-quality-transformer

```python
# Input: S3 JSON files
# Processing:
#   1. Schema validation (JSON Schema)
#   2. Data normalization
#   3. Type conversion
#   4. Compression (Parquet + Snappy)
# Output: S3 Parquet files
# Error Route: Quarantine bucket
```

**Configuration**
- Memory: 512 MB
- Timeout: 300 seconds
- Trigger: S3:ObjectCreated events

---

## 4. Analytics Layer

### Athena Configuration

```yaml
Workgroup: air_quality_analytics
Engine: v3
Partition Projection: Enabled
Query Cost: ~₹0.60 per 1GB scanned
Latency (p95): < 2 seconds
```

### Sample Queries

**1. 7-Day PSI Trend**
```sql
SELECT 
  date_trunc('hour', timestamp) AS hour,
  AVG(CAST(psi AS DECIMAL)) AS avg_psi
FROM air_quality_processed
WHERE source = 'nea' AND country = 'sg'
  AND timestamp > CURRENT_TIMESTAMP - INTERVAL '7' day
GROUP BY date_trunc('hour', timestamp)
ORDER BY hour DESC;
```

**2. Haze Detection**
```sql
WITH psi_readings AS (
  SELECT timestamp, psi,
    ROW_NUMBER() OVER (ORDER BY timestamp) AS rn
  FROM air_quality_processed
  WHERE psi > 100 AND source = 'nea'
)
SELECT 
  MIN(timestamp) AS event_start,
  MAX(timestamp) AS event_end,
  COUNT(*) AS consecutive_readings
FROM psi_readings
GROUP BY (rn - ROW_NUMBER() OVER (ORDER BY timestamp))
HAVING COUNT(*) >= 6
ORDER BY event_start DESC;
```

---

## 5. Delivery Layer

### CloudFront Distribution

```yaml
Domain: d123456abc.cloudfront.net
Origin: S3
Protocol: HTTPS (TLS 1.3)
Caching:
  Default TTL: 1 hour
  Max TTL: 24 hours
Compression: Gzip + Brotli
Logging: Enabled
```

### Dashboard

- Frontend: HTML/CSS/JavaScript
- Charts: Chart.js library
- Data: Athena queries via Lambda API
- Real-time: Optional WebSocket integration

---

## 6. Alerting Layer

### Lambda: air-quality-haze-detector

```python
# Trigger: EventBridge hourly
# Logic:
#   1. Query: PSI > 100 for last 6 hours
#   2. If true: Trigger SNS
# Targets: Email, SMS, Slack, DynamoDB
# Response Time: < 5 minutes
```

### SNS Topics

- **air-quality-alerts**: Critical alerts (haze events)
- **air-quality-notifications**: General updates
- **air-quality-errors**: System errors (for ops team)

---

## 7. Observability Layer

### CloudWatch Metrics

```
IngestEvents, TransformSuccess, TransformErrors
QueryCount, QueryLatency
AlertTriggered
S3 Put/Get operations
```

### CloudWatch Alarms

```
✓ Lambda errors > 1%
✓ DLQ depth > 10 messages
✓ Query latency > 5 seconds
✓ S3 upload failures
```

### X-Ray Tracing

```
Sampling Rate: 10% (cost-optimized)
Traced Services: All Lambdas
Visualization: Service map, traces, latency
```

---

## Scaling & Performance

### Horizontal Scaling

| Component | Concurrency | Limit |
|-----------|-------------|-------|
| Lambda | 100 | AWS account |
| S3 | Unlimited | 11,500 PUT/sec per prefix |
| Athena | Auto-scaled | Depends on DPU |
| CloudFront | Global | 10,000 req/sec |

### Performance Targets

- Ingestion: < 30 sec
- Transformation: < 60 sec
- Query: < 2 sec (p95)
- Alert: < 5 min
- Dashboard: < 1 sec (cached)

---

## Security Architecture

### Defense Layers

1. **Perimeter**: AWS Shield + CloudFront WAF
2. **Access**: IAM roles + resource-based policies
3. **Data**: TLS 1.3 + SSE-S3/KMS
4. **Monitoring**: CloudTrail + GuardDuty
5. **Incidents**: SNS alerts + runbooks

### Compliance

- ✅ No hardcoded credentials
- ✅ Least-privilege IAM
- ✅ Encryption in transit & at rest
- ✅ Audit logging (CloudTrail)
- ✅ No PII in data

---

## Cost Optimization

```
S3 Lifecycle: Raw → Glacier → Delete
Data Format: JSON → Parquet (60% smaller)
Partitioning: year/month/day/hour (query pruning)
X-Ray Sampling: 10% (90% cost reduction)
Lambda Memory: 256–512 MB (right-sized)
Athena: Partition projection (no crawler)

Estimated Monthly Cost: SGD 1–3
```

---

## Disaster Recovery

### Backup Strategy

- **Type**: S3 Cross-Region Replication (CRR)
- **Primary**: ap-southeast-1 (SG)
- **Backup**: ap-southeast-2 (Sydney)
- **RPO**: < 15 minutes
- **RTO**: < 2 hours

### Failover Procedure

1. Detect primary region failure
2. Notify on-call engineer
3. Run: `terraform apply -var aws_region=ap-southeast-2`
4. Update CloudFront origin
5. Verify: Test dashboard

---

## Appendix: Key Files

- `terraform/main.tf` - Infrastructure definition
- `lambdas/ingestion/nea_ingestion/handler.py` - Data fetcher
- `lambdas/transformation/handler.py` - ETL logic
- `lambdas/anomaly_detection/handler.py` - Alert logic
- `docs/API_REFERENCE.md` - API specifications

---

**End of Architecture Document**