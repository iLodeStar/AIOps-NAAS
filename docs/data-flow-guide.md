# Vector to ClickHouse Data Flow Guide

## Overview
This guide documents the step-by-step data flow from Vector to ClickHouse and provides verification points for each stage.

## Data Flow Architecture

```
[Host Metrics Source] 
    ↓ (raw metrics)
[metrics_for_logs Transform] 
    ↓ (transformed data)  
[ClickHouse Sink] → [ClickHouse Database]
    ↓
[console_debug Sink] → [Docker logs for debugging]
```

## Step-by-Step Verification Points

### 1. Host Metrics Collection
**What happens**: Vector collects system metrics (CPU, memory, network, disk) every 10 seconds.

**Verification**:
```bash
# Check if host metrics source is active
docker compose logs vector | grep -i "host_metrics" | tail -5

# Should show: Events received/sent from host_metrics source
```

**Expected output**: `Events received. count=280 byte_size=193831` (numbers will vary)

### 2. Metrics Transformation 
**What happens**: Raw host metrics are transformed into log format compatible with ClickHouse schema.

**Verification**:
```bash
# Check transformation activity
docker compose logs vector | grep -i "transform.*metrics_for_logs" | tail -5

# Should show: Events processed by metrics_for_logs transform
```

**Transformation rules**:
- `.timestamp = .timestamp` (preserve timestamp)
- `.level = "INFO"` (set log level)
- `.message = .name` (metric name becomes log message)
- `.source = "host_metrics"`
- `.host = .tags.host` (extract host from tags)
- `.service = "metrics"`
- Additional fields for ClickHouse compatibility

### 3. Data Batching
**What happens**: Transformed events are batched (max 1 event, 1 second timeout for immediate testing).

**Configuration**:
```toml
batch.max_events = 1
batch.timeout_secs = 1
```

### 4. ClickHouse Connection
**What happens**: Vector connects to ClickHouse using HTTP API with basic auth.

**Verification**:
```bash
# Check ClickHouse connectivity
docker compose logs vector | grep -i clickhouse | tail -5

# Should show successful HTTP requests to ClickHouse
```

### 5. Data Insertion
**What happens**: Transformed metrics are inserted into `logs.raw` table.

**Verification**:
```bash
# Check total record count
curl -u "default:changeme_clickhouse" \
  "http://localhost:8123/?query=SELECT count(*) FROM logs.raw"

# Check recent records by source
curl -u "default:changeme_clickhouse" \
  "http://localhost:8123/?query=SELECT source, count(*) FROM logs.raw WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY source"
```

## Debugging Common Issues

### Issue 1: No Data in ClickHouse
**Symptoms**: ClickHouse shows only initial sample data (4 records)

**Debug steps**:
1. Check Vector transform logs for activity
2. Verify ClickHouse authentication credentials
3. Check Vector sink logs for errors
4. Verify ClickHouse table schema compatibility

### Issue 2: Transform Not Working
**Symptoms**: Console debug shows raw metrics instead of transformed data

**Debug steps**:
1. Verify VRL transformation syntax
2. Check for VRL compilation errors in Vector logs
3. Test transformation with simpler mapping

### Issue 3: Authentication Errors  
**Symptoms**: HTTP 516 authentication errors

**Solution**: Update Vector config with correct ClickHouse credentials:
```toml
[sinks.clickhouse.auth]
strategy = "basic"
user = "default" 
password = "changeme_clickhouse"
```

## Current Status

✅ **Working Components**:
- Vector container healthy and running
- ClickHouse accessible and healthy  
- Vector API endpoints working
- Host metrics collection active
- ClickHouse connectivity established

⚠️  **Issues to Resolve**:
- Transformation output not reaching ClickHouse
- Need to verify data format compatibility
- Console debug shows raw instead of transformed data

## Next Steps

1. **Fix transformation pipeline**:
   - Verify VRL script syntax
   - Check data type compatibility
   - Test with simpler transformation

2. **Validate data flow**:
   - Use console sink to verify transformation
   - Check ClickHouse receives correct data format
   - Monitor real-time data insertion

3. **Performance tuning**:
   - Adjust batch sizes for production
   - Configure appropriate timeouts
   - Set up monitoring and alerts