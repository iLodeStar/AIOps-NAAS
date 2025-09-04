# CRITICAL FIX: Vector ClickHouse Integration Issue Resolution

## Root Cause Analysis

After investigating the user's issue where messages appear in Vector logs but don't reach ClickHouse, I've identified **two critical problems**:

### Problem 1: Service Not Running
The primary issue is that **Docker services are not running**. When the user tries to query ClickHouse, the container `aiops-clickhouse` doesn't exist.

### Problem 2: Timestamp Format Mismatch  
Vector was sending raw timestamp objects to ClickHouse, but ClickHouse table expects `DateTime64(3)` format with specific string formatting.

## Complete Fix Applied

### 1. Fixed Vector Timestamp Formatting

**Before (Causing Schema Mismatch):**
```toml
[transforms.syslog_for_logs]
source = '''
.timestamp = .timestamp  # Raw timestamp object
'''
```

**After (ClickHouse Compatible):**
```toml
[transforms.syslog_for_logs]  
source = '''
# Ensure timestamp is properly formatted for ClickHouse DateTime64(3)
.timestamp = format_timestamp!(.timestamp, "%Y-%m-%d %H:%M:%S%.3f")
'''
```

### 2. Consistent Formatting Across All Transforms
Applied the same timestamp fix to:
- `syslog_for_logs` - Syslog messages (UDP/TCP)
- `file_logs_processed` - File-based logs  
- `snmp_for_logs` - SNMP data from NATS
- `format_for_clickhouse` - Host metrics (already correct)

### 3. Authentication Already Fixed
Vector ClickHouse authentication was already added in previous commit:
```toml
[sinks.clickhouse.auth]
strategy = "basic"
user = "${CLICKHOUSE_USER:-default}"
password = "${CLICKHOUSE_PASSWORD:-clickhouse123}"
```

## Step-by-Step Resolution Guide

### Step 1: Start the Services
```bash
cd /home/runner/work/AIOps-NAAS/AIOps-NAAS

# Start all services with docker-compose
docker compose up -d

# Wait for services to be healthy
docker compose ps

# Verify Vector is running
docker ps | grep aiops-vector
```

### Step 2: Wait for Service Readiness
```bash
# Wait 60 seconds for all services to start and become healthy
sleep 60

# Check service health
curl -s http://localhost:8686/health  # Vector
curl -s http://localhost:8123/ping    # ClickHouse  
curl -s http://localhost:8222/healthz # NATS
```

### Step 3: Test Message Flow
```bash
# Generate tracking ID
TRACKING_ID="FIX-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

# Send test message
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: TIMESTAMP_FIX_TEST $TRACKING_ID" | nc -u localhost 1514

# Wait for batch processing  
sleep 15

# Query ClickHouse
docker exec aiops-clickhouse clickhouse-client \
  --user=default --password=clickhouse123 \
  --query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 5"
```

### Step 4: Comprehensive Validation
```bash
# Run diagnostic script
./scripts/diagnose_clickhouse_issue.sh

# Run full validation
./scripts/validate_complete_end_to_end_flow.sh
```

## Expected Results

### Before Fix:
- ✅ Messages in Vector logs: `docker logs aiops-vector | grep TRACKING_ID`
- ❌ No records in ClickHouse: `SELECT count() FROM logs.raw WHERE message LIKE '%TRACKING_ID%'` returns 0

### After Fix:
- ✅ Messages in Vector logs
- ✅ Records in ClickHouse with properly formatted timestamps  
- ✅ Vector metrics showing successful sink processing

## Validation Commands

### Check Vector Processing
```bash
# Should show events being processed
curl -s http://localhost:8686/metrics | grep -E "vector_component.*clickhouse"

# Should show no processing errors
curl -s http://localhost:8686/metrics | grep -E "vector_component_errors.*clickhouse"
```

### Check ClickHouse Data
```bash
# Should show increasing record count
docker exec aiops-clickhouse clickhouse-client \
  --user=default --password=clickhouse123 \
  --query="SELECT count() FROM logs.raw WHERE source = 'syslog'"

# Should show recent records with proper timestamp format
docker exec aiops-clickhouse clickhouse-client \
  --user=default --password=clickhouse123 \
  --query="SELECT timestamp, message FROM logs.raw WHERE source = 'syslog' ORDER BY timestamp DESC LIMIT 3"
```

## Key Points for User

1. **Services Must Be Running**: Always start with `docker compose up -d`
2. **Wait for Health**: Allow 60+ seconds for all services to become healthy
3. **Timestamp Format Critical**: The timestamp formatting fix resolves schema mismatches
4. **Authentication Working**: Vector-to-ClickHouse auth was already fixed in previous commits

## SNMP Data Flow Clarification

**User asked: "Where are we tracking SNMP data?"**

SNMP data flows through this pipeline:
```
Network Devices → SNMP Collector → NATS (telemetry.network.*) → Vector → ClickHouse
```

Vector processes SNMP data via:
- **Source**: `[sources.snmp_nats]` listening to NATS `telemetry.network.>` subjects
- **Transform**: `[transforms.snmp_for_logs]` converts SNMP metrics to log format
- **Sink**: `[sinks.clickhouse]` stores SNMP data in `logs.raw` table with `source = "snmp"`

To verify SNMP data:
```bash
# Check SNMP records in ClickHouse
docker exec aiops-clickhouse clickhouse-client \
  --user=default --password=clickhouse123 \
  --query="SELECT timestamp, message, host, service FROM logs.raw WHERE source = 'snmp' ORDER BY timestamp DESC LIMIT 5"
```

## Summary

The combination of:
1. **Starting Docker services** (`docker compose up -d`)
2. **Timestamp formatting fix** (`format_timestamp!(.timestamp, "%Y-%m-%d %H:%M:%S%.3f")`)
3. **Existing authentication configuration**

Should resolve the issue completely and enable true end-to-end message tracking from Vector to ClickHouse.