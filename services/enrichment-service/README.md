# Enrichment Service - Fast Path L1 Enrichment

Fast Path L1 enrichment service for the AIOps NAAS v0.3+ platform.

## Overview

This service enriches anomalies detected by the anomaly detection service with historical context from ClickHouse, enabling better severity assessment and incident correlation.

**Target Performance**: <500ms p99 latency

## Architecture

```
anomaly.detected (NATS) 
    ↓
Enrichment Service
    ↓ (queries)
ClickHouse
    ↓
anomaly.enriched (NATS)
```

## Features

- **Device Metadata Enrichment**: Queries device information (type, vendor, model, criticality)
- **Historical Failure Rates**: Analyzes anomaly patterns over the last 24 hours
- **Similar Anomaly Detection**: Finds similar anomalies from the last 7 days
- **Recent Incident Context**: Retrieves related incidents for correlation
- **Context-Aware Severity**: Computes severity based on score + historical context
- **Performance Monitoring**: Tracks p95/p99 latency metrics

## File Structure

```
services/enrichment-service/
├── enrichment_service.py   # Main service implementation
├── clickhouse_queries.py   # ClickHouse query functions
├── Dockerfile              # Container image
├── requirements.txt        # Python dependencies
└── test_enrichment.py      # Validation tests
```

## Configuration

Environment variables:

```bash
NATS_URL=nats://nats:4222           # NATS server URL
CLICKHOUSE_HOST=clickhouse           # ClickHouse server hostname
CLICKHOUSE_USER=admin                # ClickHouse username
CLICKHOUSE_PASSWORD=admin            # ClickHouse password
ENRICHMENT_PORT=8085                 # HTTP service port
```

## API Endpoints

### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "enrichment-v3",
  "version": "3.0",
  "stats": { ... },
  "nats": {
    "connected": true,
    "input": "anomaly.detected",
    "output": "anomaly.enriched"
  },
  "clickhouse": {
    "connected": true
  }
}
```

### GET /metrics

Prometheus-compatible metrics endpoint.

**Metrics exposed**:
- `enrichment_processed_total`: Total anomalies processed
- `enrichment_enriched_total`: Total anomalies enriched successfully
- `enrichment_errors_total`: Total enrichment errors
- `enrichment_latency_ms_avg`: Average enrichment latency
- `enrichment_latency_ms_p95`: P95 enrichment latency
- `enrichment_latency_ms_p99`: P99 enrichment latency
- `enrichment_device_metadata_hits`: Total device metadata found
- `enrichment_similar_anomalies_found`: Total similar anomalies found

### GET /stats

Detailed statistics in JSON format.

**Response**:
```json
{
  "service": "enrichment-v3",
  "stats": {
    "processed": 1000,
    "enriched": 995,
    "errors": 5,
    "avg_latency_ms": 125.5,
    "p95_latency_ms": 245.0,
    "p99_latency_ms": 385.0,
    "device_metadata_hits": 850,
    "similar_anomalies_found": 320
  },
  "targets": {
    "p99_latency_target_ms": 500,
    "p99_latency_met": true
  }
}
```

## Data Flow

### Input: AnomalyDetected

Subscribe to `anomaly.detected` topic.

```json
{
  "tracking_id": "req-20250103-120000-abc123",
  "ts": "2025-01-03T12:00:00Z",
  "ship_id": "vessel-001",
  "domain": "comms",
  "anomaly_type": "high_latency",
  "score": 0.85,
  "detector": "threshold",
  "service": "satellite-modem",
  "device_id": "sat-001",
  "metric_name": "latency_ms",
  "metric_value": 1500.0,
  "threshold": 500.0
}
```

### Output: AnomalyEnriched

Publish to `anomaly.enriched` topic.

```json
{
  "tracking_id": "req-20250103-120000-abc123",
  "ts": "2025-01-03T12:00:00Z",
  "ship_id": "vessel-001",
  "domain": "comms",
  "anomaly_type": "high_latency",
  "score": 0.85,
  "severity": "high",
  "detector": "threshold",
  "service": "satellite-modem",
  "device_id": "sat-001",
  "context": {
    "similar_count_1h": 2,
    "similar_count_24h": 8,
    "last_incident_ts": "2025-01-03T10:30:00Z"
  },
  "meta": {
    "device_metadata": {
      "device_type": "satellite_modem",
      "vendor": "Inmarsat",
      "model": "Fleet One",
      "criticality": "high"
    },
    "historical_failure_rates": {
      "total_anomalies_24h": 12,
      "critical_count_24h": 2,
      "high_count_24h": 5,
      "avg_score_24h": 0.72,
      "failure_rate_per_hour": 0.5
    },
    "similar_anomalies": [ ... ],
    "recent_incidents": [ ... ]
  }
}
```

## ClickHouse Queries

### Device Metadata
```sql
SELECT device_type, vendor, model, location, criticality
FROM devices 
WHERE ship_id = ? AND device_id = ?
LIMIT 1
```

### Historical Failure Rates (24h)
```sql
SELECT 
    count() as total_anomalies,
    countIf(severity = 'critical') as critical_count,
    countIf(severity = 'high') as high_count,
    avg(score) as avg_score
FROM anomalies
WHERE ship_id = ? AND domain = ?
  AND ts >= now() - INTERVAL 24 HOUR
```

### Similar Anomalies (7d)
```sql
SELECT ts, severity, score, detector, service, metric_name, metric_value
FROM anomalies
WHERE ship_id = ? AND domain = ? AND anomaly_type = ?
  AND ts >= now() - INTERVAL 7 DAY
ORDER BY ts DESC
LIMIT 10
```

## Severity Computation

The service computes severity based on anomaly score and historical context:

- **CRITICAL**: 
  - Score ≥ 0.9, OR
  - Score ≥ 0.7 AND (≥5 similar in 1h OR ≥20 similar in 24h)

- **HIGH**:
  - Score ≥ 0.7, OR
  - Score ≥ 0.5 AND (≥3 similar in 1h OR ≥10 similar in 24h)

- **MEDIUM**: Score ≥ 0.4

- **LOW**: Score < 0.4

## Error Handling

The service implements graceful error fallback:

1. **ClickHouse Query Failures**: Return empty/default values, continue enrichment
2. **Enrichment Errors**: Return minimal enrichment with error tag
3. **NATS Publish Errors**: Logged, increment error counter

All errors are logged with tracking_id for end-to-end tracing.

## Running the Service

### Docker

```bash
docker build -t enrichment-service .
docker run -p 8085:8085 \
  -e NATS_URL=nats://nats:4222 \
  -e CLICKHOUSE_HOST=clickhouse \
  -e CLICKHOUSE_USER=admin \
  -e CLICKHOUSE_PASSWORD=admin \
  enrichment-service
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python enrichment_service.py
```

## Testing

```bash
# Run validation tests
python test_enrichment.py
```

## Performance Optimization

To maintain <500ms p99 latency:

1. **Query Optimization**: All queries use indexed columns (ship_id, domain, ts)
2. **Parallel Queries**: Device metadata and historical queries run in sequence but could be parallelized
3. **Result Limiting**: Queries limit results (LIMIT 10 for similar anomalies, LIMIT 5 for incidents)
4. **Graceful Degradation**: Failed queries don't block the pipeline

## Monitoring

Monitor these key metrics:

- `enrichment_latency_ms_p99` - Must be <500ms
- `enrichment_errors_total` - Should be low
- `enrichment_device_metadata_hits` - Device registry coverage
- `enrichment_similar_anomalies_found` - Context enrichment effectiveness

## Dependencies

See `requirements.txt`:
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- pydantic==2.5.0
- nats-py==2.6.0
- clickhouse-driver==0.2.6
- python-dateutil==2.8.2

## Integration

This service integrates with:

- **Upstream**: anomaly-detection service (publishes to `anomaly.detected`)
- **Downstream**: correlation-service (subscribes to `anomaly.enriched`)
- **Storage**: ClickHouse (queries `devices`, `anomalies`, `incidents` tables)
- **Message Bus**: NATS JetStream

## Acceptance Criteria

- [x] Subscribes to `anomaly.detected`
- [x] ClickHouse queries work (device metadata, failure rates, similar anomalies)
- [x] Publishes `AnomalyEnriched` to `anomaly.enriched`
- [x] Latency <500ms (p99) with tracking
- [x] `/health` and `/metrics` endpoints
- [x] Error fallback handling
