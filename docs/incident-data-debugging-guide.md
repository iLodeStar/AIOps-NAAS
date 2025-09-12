# Incident Data Completeness Debugging Guide

This document provides a comprehensive methodology for debugging and fixing incomplete incident data in the AIOps NAAS platform, specifically addressing issues where incidents show fallback values like `unknown-ship`, `unknown_service`, `unknown_metric`, etc.

## Issue Overview

When incidents are created in ClickHouse, they may contain incomplete data with fallback values:

```bash
SELECT * FROM logs.incidents ORDER BY processing_timestamp DESC LIMIT 1;
```

**Problem Example:**
```
5ee629ee-3c36-44e2-a056-f75e06274121	incident	single_anomaly	medium	unknown-ship	unknown_service	open	02025-09-12 18:39:01.341	2025-09-12 18:39:01.341	3e2550e1-7a72-48e1-a9f5-59f0192053f4	2025-09-12 18:39:01.441	unknown_metric	0	0.5		[]	[{"description": "Incident created by anomaly correlation - single_anomaly on unknown-ship"...}]
```

**Fields with issues:**
- `ship_id`: "unknown-ship" (should be actual ship identifier)
- `service`: "unknown_service" (should be the originating service)
- `metric_name`: "unknown_metric" (should be the specific metric)
- `metric_value`: 0 (should be actual metric value)
- `host`: "unknown" in metadata (should be hostname)

## Root Cause Analysis

### Data Flow Architecture

The incident creation follows this path:

1. **Data Sources** → Vector (logs/metrics collection)
2. **Vector** → ClickHouse (raw data storage) + NATS (anomaly routing)
3. **NATS** → Anomaly Detection Service → Enhanced anomalies
4. **Enhanced Anomalies** → Benthos (correlation) → Incident API
5. **Incident API** → Device Registry (ship_id resolution) → ClickHouse (incidents)

### Common Root Causes

1. **Vector Configuration Issues:**
   - Not extracting hostname from syslog messages
   - Missing service field extraction
   - Improper data transformation

2. **Missing Source Data:**
   - Applications not logging with proper structure
   - Syslog messages missing hostname/appname
   - Metrics without proper labels

3. **Service Integration Issues:**
   - Device Registry not running or not accessible
   - No hostname-to-ship_id mappings configured
   - Anomaly Detection Service not publishing events

4. **Data Processing Issues:**
   - Benthos receiving null/empty values
   - Field extraction logic not working
   - Data type conversion problems

## Debugging Methodology

### Step 1: Run Diagnostic Scripts

First, use the provided diagnostic tools to identify the specific issues:

```bash
# Run comprehensive diagnostic
./scripts/diagnose_incident_data_completeness.sh

# Trace data field population in detail  
python3 scripts/trace_incident_data_fields.py --deep-analysis

# Analyze current incident data quality
python3 scripts/enhance_incident_data.py --analyze
```

### Step 2: Check Service Health

Verify all pipeline services are running and accessible:

```bash
# Check individual services
curl http://localhost:8686/health  # Vector
curl http://localhost:8123/ping    # ClickHouse  
curl http://localhost:4195/ping    # Benthos
curl http://localhost:8081/health  # Anomaly Detection
curl http://localhost:8082/health  # Device Registry
curl http://localhost:8083/health  # Incident API

# Check Docker containers
docker ps | grep aiops
```

### Step 3: Trace Raw Data Sources

Check if Vector is properly collecting and storing raw data:

```bash
# Check raw data volume and sources
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
SELECT 
    source,
    count() as records,
    uniq(host) as hosts,  
    uniq(service) as services,
    min(timestamp) as oldest,
    max(timestamp) as newest
FROM logs.raw 
WHERE timestamp > now() - INTERVAL 1 HOUR 
GROUP BY source 
ORDER BY records DESC"
```

### Step 4: Test Data Flow with Tracking

Generate test data to trace through the pipeline:

```bash
# Generate test data with tracking
python3 scripts/trace_incident_data_fields.py --generate-test-data

# Send manual test syslog message
TRACKING_ID="TEST-$(date +%Y%m%d-%H%M%S)"
echo "<14>$(date '+%b %d %H:%M:%S') test-ship-01 cpu-monitor: ERROR tracking_id=$TRACKING_ID metric_name=cpu_usage metric_value=95.5 anomaly_score=0.9" | nc -u localhost 1514

# Wait and check if data flows through
sleep 15
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT * FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'"
```

### Step 5: Check Device Registry Mappings

Verify ship_id resolution is working:

```bash
# Test hostname mappings
curl "http://localhost:8082/lookup/dhruv-system-01"
curl "http://localhost:8082/lookup/ship-01"  
curl "http://localhost:8082/lookup/test-ship-01"

# Register missing mappings if needed
python3 scripts/register_device.py --hostname test-ship-01 --ship-id test-ship-01 --location "Test Location"
```

### Step 6: Monitor Anomaly Detection

Check if anomaly detection is creating proper events:

```bash
# Check anomaly service metrics
curl http://localhost:8081/metrics | grep -i anomaly

# Monitor NATS subjects (if nats CLI is available)
docker exec aiops-nats nats sub "anomaly.detected" --count=5
```

### Step 7: Analyze Benthos Processing

Check Benthos correlation and processing:

```bash
# Check Benthos metrics and processing
curl http://localhost:4195/metrics | grep -E "(input|output|processed)"

# Check Benthos logs for errors
docker logs aiops-benthos --since=10m | grep -E "(ERROR|WARN)"
```

## Specific Field Troubleshooting

### ship_id shows "unknown-ship"

**Likely causes:**
1. Device Registry service not accessible
2. No hostname mappings configured
3. Hostname not extracted from logs

**Debug steps:**
```bash
# Check device registry health
curl http://localhost:8082/health

# Test hostname resolution  
curl "http://localhost:8082/lookup/$(hostname)"

# Check raw logs for hostname field
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT DISTINCT host FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR"

# Register hostname if missing
python3 scripts/register_device.py --hostname $(hostname) --ship-id my-ship-01
```

### service shows "unknown_service"  

**Likely causes:**
1. Syslog messages missing appname field
2. Vector not extracting service field
3. Applications not structured logging

**Debug steps:**
```bash
# Check raw logs for service field population
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT source, service, count() FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR GROUP BY source, service"

# Test structured syslog message
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) my-service: Test message" | nc -u localhost 1514
```

### metric_name shows "unknown_metric"

**Likely causes:**
1. Anomaly Detection not publishing events
2. NATS events missing metric_name
3. Benthos not extracting metric names

**Debug steps:**
```bash
# Check if anomaly detection is running
curl http://localhost:8081/health

# Check VictoriaMetrics for available metrics
curl "http://localhost:8428/api/v1/label/__name__/values"

# Test anomaly event structure
python3 scripts/publish_test_anomalies.py --metric-name cpu_usage --value 95.5
```

### metric_value shows 0

**Likely causes:**  
1. Anomaly events missing actual values
2. Data type conversion issues
3. Numeric parsing failures

**Debug steps:**
```bash
# Check for numeric values in recent raw logs
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT message FROM logs.raw WHERE message REGEXP '[0-9]+\\.?[0-9]*' AND timestamp > now() - INTERVAL 1 HOUR LIMIT 5"

# Test message with explicit metric value
echo "<14>$(date '+%b %d %H:%M:%S') test-host my-service: ERROR metric_name=cpu_usage metric_value=87.5" | nc -u localhost 1514
```

## Resolution Strategies

### Quick Fixes

1. **Restart Services:**
   ```bash
   docker-compose restart vector benthos device-registry anomaly-detection
   ```

2. **Register Device Mappings:**
   ```bash
   python3 scripts/register_device.py --hostname $(hostname) --ship-id ship-01
   ```

3. **Test Data Flow:**
   ```bash
   python3 scripts/trace_incident_data_fields.py --generate-test-data
   ```

### Configuration Fixes

1. **Update Vector to extract proper fields:**
   ```toml
   [transforms.syslog_for_logs]
   type = "remap"
   inputs = ["syslog_udp", "syslog_tcp"]
   source = '''
   .host = if exists(.hostname) { .hostname } else { "unknown" }
   .service = if exists(.appname) && .appname != "" { .appname } else { "unknown_service" }
   '''
   ```

2. **Add device registry mappings:**
   ```bash
   # Add mappings for common hostnames
   python3 scripts/register_device.py --batch-register hostnames.csv
   ```

3. **Configure structured logging:**
   ```python
   # In applications, use structured logging
   logger.info("CPU usage high", extra={
       "metric_name": "cpu_usage",
       "metric_value": 87.5,
       "service": "cpu-monitor"
   })
   ```

### Data Enhancement

Use the enhancement script to improve existing data:

```bash
# Analyze missing data patterns
python3 scripts/enhance_incident_data.py --analyze

# Apply automatic enhancements (dry run first)
python3 scripts/enhance_incident_data.py --fix-recent --dry-run
python3 scripts/enhance_incident_data.py --fix-recent
```

## Production Monitoring

### Set up continuous monitoring:

1. **Create alerts for missing data:**
   ```sql
   -- Alert if >50% of incidents have unknown fields
   SELECT 
       count() as total_incidents,
       countIf(ship_id = 'unknown-ship') as unknown_ships,
       countIf(service = 'unknown_service') as unknown_services
   FROM logs.incidents 
   WHERE created_at > now() - INTERVAL 1 HOUR
   ```

2. **Monitor service health:**
   ```bash
   # Add to monitoring system
   curl -f http://localhost:8082/health || echo "Device Registry Down"
   curl -f http://localhost:8081/health || echo "Anomaly Detection Down" 
   ```

3. **Track data quality metrics:**
   ```bash
   # Daily data quality report
   python3 scripts/enhance_incident_data.py --analyze >> /var/log/data-quality-$(date +%Y%m%d).log
   ```

## Validation and Testing

### Test complete data flow:

1. **Generate test incidents:**
   ```bash
   python3 scripts/trace_incident_data_fields.py --generate-test-data
   ```

2. **Validate field population:**
   ```bash
   docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
   SELECT 
       ship_id, service, metric_name, metric_value 
   FROM logs.incidents 
   WHERE created_at > now() - INTERVAL 10 MINUTE
   ORDER BY created_at DESC 
   LIMIT 5"
   ```

3. **Check enhancement effectiveness:**
   ```bash
   python3 scripts/enhance_incident_data.py --fix-recent --dry-run
   ```

## Summary

The key to resolving incomplete incident data is:

1. **Identify the source** - Use diagnostic scripts to find where data is missing
2. **Fix upstream sources** - Ensure raw data has proper fields
3. **Configure services** - Set up device registry, proper Vector transforms
4. **Test thoroughly** - Use tracking IDs to verify complete data flow
5. **Monitor continuously** - Set up alerts for data quality issues

The provided diagnostic and enhancement scripts automate much of this process and provide clear recommendations for resolving specific issues.