# One-Click Incident Debugging Tool

A comprehensive diagnostic solution for incident data pipeline issues in the AIOps platform.

## 🎯 Purpose

This tool addresses the critical issue where ClickHouse incidents contain fallback values instead of meaningful data:

- `ship_id: "unknown-ship"` (should be actual ship identifier)
- `service: "unknown_service"` (should be originating service)
- `metric_name: "unknown_metric"` (should be specific metric)
- `metric_value: 0` (should be actual value)

## 🚀 Quick Start

### Option 1: Interactive Menu (Recommended)
```bash
./scripts/one_click_debug.sh
```

### Option 2: Direct Python Execution
```bash
# Quick diagnostic
python3 scripts/one_click_incident_debugging.py

# Deep analysis with extended monitoring
python3 scripts/one_click_incident_debugging.py --deep-analysis

# Full report generation (GitHub-ready issue)
python3 scripts/one_click_incident_debugging.py --deep-analysis --generate-issue-report
```

## 🔧 What It Does

### 1. **Service Health Checks**
- Vector (log processing)
- ClickHouse (data storage)
- NATS (message bus) 
- Benthos (stream processing)
- Victoria Metrics (metrics storage)
- Incident API
- Device Registry

### 2. **Test Data Generation**
- Creates 3 trackable test scenarios
- Each with unique tracking IDs
- Covers different service types and metrics
- Includes expected vs actual data mapping

### 3. **End-to-End Data Tracking**
- **Vector**: Monitors log ingestion and parsing
- **NATS**: Tracks message flow through streams (with CLI)
- **Benthos**: Monitors stream processing statistics
- **ClickHouse**: Validates data storage and field population

### 4. **Mismatch Analysis**
- Compares expected vs actual field values
- Identifies root cause for each missing field
- Maps responsible services for each issue
- Provides specific fix recommendations

### 5. **GitHub Issue Generation**
- Creates copy-paste ready issue reports
- Includes reproduction steps with exact data points
- Contains service health status
- Provides debugging commands and fix recommendations

## 📊 Diagnostic Modes

| Mode | Duration | Features | Use Case |
|------|----------|----------|----------|
| **Quick** | 2-3 min | Basic health checks, test data injection, simple tracking | First-time diagnosis |
| **Deep** | 5-7 min | Extended monitoring, detailed NATS analysis, component debugging | Thorough investigation |
| **Full Report** | 5-7 min | Deep analysis + GitHub issue generation | Creating actionable issues |

## 🧪 Test Data Examples

The tool generates realistic test scenarios:

```yaml
Test Case 1:
  tracking_id: "ONECLICK-20240312-143052-DATA-001"
  ship_id: "test-ship-alpha"
  hostname: "alpha-bridge-01"
  service: "navigation_system"
  metric: "gps_accuracy_meters = 2.5"
  message: "[TRACKING_ID] GPS accuracy degraded to 2.5 meters in heavy fog"

Test Case 2:
  tracking_id: "ONECLICK-20240312-143052-DATA-002"
  ship_id: "test-ship-beta"
  hostname: "beta-engine-02"
  service: "engine_monitoring"
  metric: "fuel_pressure_psi = 45.2"
  message: "[TRACKING_ID] Fuel pressure dropped to 45.2 PSI on starboard engine"
```

## 🔍 What Gets Tracked

### Service Pipeline Flow
```
Log Message → Vector → NATS → Benthos → ClickHouse
     ↓           ↓       ↓        ↓         ↓
  Syslog     Parsing  Stream   Process   Storage
 Injection   Rules   Publish  Rules     Query
```

### Data Field Tracking
- **ship_id**: Device Registry hostname mapping
- **service**: Syslog appname field extraction
- **metric_name**: Anomaly detection event publishing
- **metric_value**: Metric data correlation
- **hostname**: Log source identification

## 📝 Sample Output

### Console Output
```
🚀 ONE-CLICK INCIDENT DEBUGGING SESSION: ONECLICK-20240312-143052-a1b2c3d4
================================================================================

📋 STEP 1: SERVICE HEALTH CHECKS
----------------------------------------
🔍 Checking Vector...
  ✅ Vector: HTTP 200
🔍 Checking ClickHouse...
  ✅ ClickHouse: Connected with admin/admin
🔍 Checking NATS...
  ✅ NATS: HTTP 200

🧪 STEP 2: GENERATE TRACKABLE TEST DATA
----------------------------------------
🧪 Generating trackable test data points...
  📝 Generated: ONECLICK-20240312-143052-DATA-001 -> test-ship-alpha/navigation_system
  📝 Generated: ONECLICK-20240312-143052-DATA-002 -> test-ship-beta/engine_monitoring
  📝 Generated: ONECLICK-20240312-143052-DATA-003 -> test-ship-gamma/communication_system

📤 STEP 3: INJECT TEST DATA INTO PIPELINE
----------------------------------------
📤 Injecting test data into pipeline...
  🚀 Injecting: ONECLICK-20240312-143052-DATA-001
    ✅ Device registered: alpha-bridge-01 -> test-ship-alpha
    ✅ Syslog sent via HTTP: ONECLICK-20240312-143052-DATA-001
    ✅ Metric published: gps_accuracy_meters=2.5
    ✅ Anomaly detection triggered: ONECLICK-20240312-143052-DATA-001
```

### GitHub Issue Report
```markdown
# Incident Data Pipeline Diagnostic Report

**Generated:** 2024-03-12T14:30:52  
**Tracking Session:** ONECLICK-20240312-143052-a1b2c3d4  

## 🚨 Issue Summary
Incident data pipeline is producing incomplete/fallback values instead of meaningful data.

## 📊 Service Health Status
| Service | Status | Details |
|---------|--------|---------|
| Vector | ✅ healthy | HTTP 200 |
| ClickHouse | ✅ healthy | Connected with admin/admin |
| NATS | ✅ healthy | HTTP 200 |

## ❌ Data Mismatches Identified
### Ship Id Mismatch
- **Expected:** `test-ship-alpha`
- **Actual:** `unknown-ship`
- **Service Responsible:** Device Registry
- **Root Cause:** Hostname to ship_id mapping missing
```

## 🛠 Advanced Features

### NATS CLI Integration
The tool now includes NATS CLI in the container for debugging:

```bash
# Check streams
docker exec aiops-nats nats stream ls

# View messages in a stream
docker exec aiops-nats nats stream view STREAM_NAME

# Monitor real-time activity
docker exec aiops-nats nats stream info STREAM_NAME
```

### Custom Debugging Commands
```bash
# Quick service status
docker-compose ps

# Check recent incidents
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \
  --query="SELECT * FROM logs.incidents ORDER BY processing_timestamp DESC LIMIT 5"

# Monitor Vector metrics
curl http://localhost:8686/metrics | grep vector_component

# Check Benthos processing
curl http://localhost:4195/stats | jq '.'
```

## 🔧 Troubleshooting

### Common Issues

**Services not running:**
```bash
docker-compose up -d
docker-compose ps  # Verify all services are running
```

**Python dependencies missing:**
```bash
pip3 install requests
```

**NATS CLI not available:**
Use the interactive menu → Advanced Options → Install NATS CLI

**ClickHouse connection issues:**
The tool automatically tries different credential combinations:
- admin/admin
- default/clickhouse123
- default/(empty)

### Manual Reproduction

If the automated tool fails, you can manually reproduce the issue:

1. **Register a test device:**
   ```bash
   curl -X POST http://localhost:8091/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"test-host","ship_id":"test-ship"}'
   ```

2. **Send a syslog message:**
   ```bash
   echo '<134>1 2024-03-12T14:30:52Z test-host test_service - - Test message' | nc localhost 514
   ```

3. **Check results:**
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

## 📄 Files Generated

- `INCIDENT_DATA_ISSUE_REPORT_YYYYMMDD_HHMMSS.md`: GitHub-ready issue report
- Console logs: Real-time diagnostic progress
- Reproduction steps: Exact commands for manual testing

## 🎯 Expected Outcomes

After using this tool, you should have:

1. **Clear identification** of which services are causing data issues
2. **Specific reproduction steps** with trackable data points
3. **Root cause analysis** for each missing field type
4. **Actionable fix recommendations** for each identified issue
5. **GitHub-ready issue** with complete diagnostic information

## 📚 Related Documentation

- `docs/incident-data-debugging-guide.md`: Complete troubleshooting methodology
- `INCIDENT_DATA_DEBUGGING_README.md`: Quick start guide
- `scripts/diagnose_incident_data_completeness.sh`: Original diagnostic script
- `scripts/trace_incident_data_fields.py`: Advanced Python analyzer

## 🤝 Contributing

To extend the diagnostic tool:

1. Add new test scenarios in `_generate_test_data()`
2. Extend service checks in `_perform_health_checks()`
3. Add new tracking methods for additional services
4. Enhance the GitHub issue template in `_generate_github_issue()`

---

**Note:** This tool is designed to be run in a development/testing environment. For production debugging, consider using the read-only analysis features without test data injection.