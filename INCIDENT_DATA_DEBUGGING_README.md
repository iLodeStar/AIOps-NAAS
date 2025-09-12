# Incident Data Debugging Tools - Quick Start

This directory contains comprehensive tools to debug and fix incomplete incident data where ClickHouse entries show fallback values like `unknown-ship`, `unknown_service`, `unknown_metric`.

## Problem Description

When querying incidents from ClickHouse:
```sql
SELECT * FROM logs.incidents ORDER BY processing_timestamp DESC LIMIT 1;
```

You may see incomplete data with fallback values:
```
incident_id                           | ship_id      | service         | metric_name    | metric_value | ...
5ee629ee-3c36-44e2-a056-f75e06274121 | unknown-ship | unknown_service | unknown_metric | 0            | ...
```

## Quick Diagnostic Commands

### 1. Run Full Diagnostic (Recommended First Step)
```bash
./scripts/diagnose_incident_data_completeness.sh
```
**What it does:** Comprehensive health check, data quality analysis, test data generation, and actionable recommendations.

### 2. Deep Analysis with Python Tool
```bash
python3 scripts/trace_incident_data_fields.py --deep-analysis
```
**What it does:** Detailed component analysis, service health checks, and data quality metrics.

### 3. Generate Test Data to Trace Pipeline
```bash
python3 scripts/trace_incident_data_fields.py --generate-test-data
```
**What it does:** Sends test data through the pipeline and traces it to identify where it gets lost.

### 4. Analyze Missing Data Patterns
```bash
python3 scripts/enhance_incident_data.py --analyze
```
**What it does:** Analyzes recent incidents to identify patterns in missing data.

### 5. Get Specific Recommendations Only
```bash
python3 scripts/trace_incident_data_fields.py --recommendations-only
```
**What it does:** Shows specific fixes for each type of missing field without running diagnostics.

## Common Issues & Quick Fixes

### Issue: `ship_id = "unknown-ship"`

**Quick Check:**
```bash
curl http://localhost:8082/health  # Device registry health
curl "http://localhost:8082/lookup/$(hostname)"  # Test hostname lookup
```

**Quick Fix:**
```bash
# Register your hostname
python3 scripts/register_device.py --hostname $(hostname) --ship-id my-ship-01
```

### Issue: `service = "unknown_service"`

**Quick Check:**
```bash
# Check if services are being extracted from logs
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT DISTINCT service FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR"
```

**Quick Fix:**
```bash
# Send test syslog with proper service name
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) my-service: Test message" | nc -u localhost 1514
```

### Issue: `metric_name = "unknown_metric"`

**Quick Check:**
```bash
curl http://localhost:8081/health  # Anomaly detection service
```

**Quick Fix:**
```bash
# Check if anomaly detection is publishing events
python3 scripts/publish_test_anomalies.py --metric-name cpu_usage --value 95.5
```

### Issue: `metric_value = 0`

**Quick Check:**
```bash
# Look for numeric values in recent logs
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT message FROM logs.raw WHERE message REGEXP '[0-9]+\\.?[0-9]*' LIMIT 5"
```

**Quick Fix:**
```bash
# Send message with explicit metric value
echo "<14>$(date '+%b %d %H:%M:%S') test-host my-service: ERROR metric_name=cpu_usage metric_value=87.5" | nc -u localhost 1514
```

## Data Enhancement

### Fix Recent Incidents (Dry Run)
```bash
python3 scripts/enhance_incident_data.py --fix-recent --dry-run
```

### Apply Automatic Enhancements
```bash
python3 scripts/enhance_incident_data.py --fix-recent
```

### Show Data Source Mapping
```bash
python3 scripts/enhance_incident_data.py --data-mapping
```

## Files Description

| File | Purpose | Usage |
|------|---------|-------|
| `diagnose_incident_data_completeness.sh` | Comprehensive bash diagnostic script | `./scripts/diagnose_incident_data_completeness.sh` |
| `trace_incident_data_fields.py` | Detailed Python analysis tool | `python3 scripts/trace_incident_data_fields.py --help` |
| `enhance_incident_data.py` | Data enhancement and pattern analysis | `python3 scripts/enhance_incident_data.py --help` |
| `incident-data-debugging-guide.md` | Complete debugging methodology | Read for detailed troubleshooting steps |

## Typical Debugging Workflow

1. **Start with full diagnostic:**
   ```bash
   ./scripts/diagnose_incident_data_completeness.sh
   ```

2. **Identify specific issues from output**

3. **Run deep analysis if needed:**
   ```bash
   python3 scripts/trace_incident_data_fields.py --deep-analysis
   ```

4. **Test data flow:**
   ```bash
   python3 scripts/trace_incident_data_fields.py --generate-test-data
   ```

5. **Apply fixes based on recommendations**

6. **Enhance existing data:**
   ```bash
   python3 scripts/enhance_incident_data.py --fix-recent --dry-run
   python3 scripts/enhance_incident_data.py --fix-recent  # If dry run looks good
   ```

7. **Verify improvements by re-running diagnostics**

## Service Dependencies

The tools check these services automatically:
- **Vector** (port 8686) - Log/metric collection
- **ClickHouse** (port 8123/9000) - Data storage  
- **Benthos** (port 4195) - Event correlation
- **Device Registry** (port 8082) - Ship ID resolution
- **Anomaly Detection** (port 8081) - Anomaly events
- **Incident API** (port 8083) - Incident management

## Getting Help

For detailed troubleshooting methodology, see:
- `docs/incident-data-debugging-guide.md` - Complete step-by-step guide
- `docs/incident-flow-architecture.md` - Data flow architecture

Run any script with `--help` for detailed usage information.