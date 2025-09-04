# Comprehensive Step-by-Step Testing Guide
## AIOps NAAS End-to-End Data Flow Validation

### Overview
This guide provides comprehensive step-by-step testing procedures for validating the complete AIOps NAAS data pipeline from ingestion to incident creation. Each test case includes detailed input/output validation, execution steps, and verification procedures.

---

## 🎯 Test Case Categories

### **TC-001: Normal Syslog Flow (UDP/TCP)**
**Objective**: Validate basic syslog message processing through Vector to ClickHouse storage  
**Data Path**: Syslog → Vector → ClickHouse  
**Expected Outcome**: Message stored in ClickHouse without triggering anomaly detection

### **TC-002: Anomaly Detection Flow**
**Objective**: Validate anomaly detection and correlation pipeline activation  
**Data Path**: Syslog → Vector → ClickHouse → VictoriaMetrics → Anomaly Detection → NATS → Benthos → Incidents  
**Expected Outcome**: Anomaly detected, correlated, and incident created

### **TC-003: Host Metrics Flow**
**Objective**: Validate system metrics collection and storage  
**Data Path**: Host Metrics → Vector → ClickHouse → VictoriaMetrics  
**Expected Outcome**: Metrics stored and available for monitoring

### **TC-004: SNMP Network Data Flow**
**Objective**: Validate network device monitoring via SNMP  
**Data Path**: Network Device → SNMP Collector → NATS → Vector → ClickHouse  
**Expected Outcome**: Network metrics stored for analysis

### **TC-005: File-based Log Flow**
**Objective**: Validate file log ingestion and processing  
**Data Path**: Log Files → Vector → ClickHouse  
**Expected Outcome**: File logs processed and stored

### **TC-006: End-to-End Incident Correlation**
**Objective**: Validate complete incident lifecycle with correlation rules  
**Data Path**: Multiple Sources → Correlation → Incident Creation → API Response  
**Expected Outcome**: Correlated incidents with proper suppression and enrichment

---

## 📋 Test Execution Format

### Standard Test Step Format:
```
**Step X**: [One-line description]
**Input**: [What data/command is provided]
**Output**: [Expected result/response]
**Validation**: [How to verify the result]
```

---

## 🔧 Pre-Test Setup Requirements

### **SETUP-001: Environment Preparation**
**Step 1**: Verify all services are running  
**Input**: Service health check commands  
**Output**: All services report healthy status  
**Validation**: HTTP 200 responses from all health endpoints

```bash
# ClickHouse health check
curl -s http://localhost:8123/ping
# Expected Output: Ok.

# Vector health check  
curl -s http://localhost:8686/health
# Expected Output: {"status":"ok","version":"..."}

# VictoriaMetrics health check
curl -s http://localhost:8428/health
# Expected Output: {"status":"ok"}

# NATS health check
curl -s http://localhost:8222/healthz
# Expected Output: {"status":"ok"}

# Benthos health check
curl -s http://localhost:4195/ping
# Expected Output: pong

# Anomaly Detection service health
curl -s http://localhost:8080/health
# Expected Output: {"status":"healthy"}
```

### **SETUP-002: Generate Unique Test Session ID**
**Step 1**: Create session tracking identifier  
**Input**: Date and UUID generation command  
**Output**: Unique session ID for message tracking  
**Validation**: Session ID format matches expected pattern

```bash
# Generate unique session ID
TEST_SESSION_ID="TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "=== TEST SESSION: $TEST_SESSION_ID ==="
# Expected Output: === TEST SESSION: TEST-20250903-143022-a1b2c3d4 ===
```

---

## 🧪 Test Case TC-001: Normal Syslog Flow

### **Test Description**
Validates that normal operational syslog messages are properly ingested by Vector, processed, and stored in ClickHouse without triggering anomaly detection.

### **Step-by-Step Execution**

**Step 1**: Send normal UDP syslog message  
**Input**: RFC3164 formatted syslog message via UDP  
**Output**: Message transmitted to Vector  
**Validation**: No connection errors, message sent successfully

```bash
# Send normal UDP syslog message
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_OPERATION $TEST_SESSION_ID system startup completed" | nc -u localhost 1514
# Expected Output: (No output = success)
```

**Step 2**: Verify Vector receives the message  
**Input**: Vector log query for session ID  
**Output**: JSON formatted log entry with parsed syslog data  
**Validation**: Message appears in Vector logs with correct parsing

```bash
# Check Vector logs for the message
docker compose logs vector | grep "$TEST_SESSION_ID" | head -1
# Expected Output: 
# {"appname":"test-service","facility":"user","host":"ubuntu","hostname":"ubuntu","message":"NORMAL_OPERATION TEST-20250903-143022-a1b2c3d4 system startup completed","severity":"info","source_ip":"172.18.0.1","source_type":"syslog","timestamp":"2025-09-03T14:30:22Z"}
```

**Step 3**: Verify Vector processes and transforms the message  
**Input**: Vector log query for transformed message  
**Output**: Transformed message with ClickHouse-compatible fields  
**Validation**: Message contains required fields: timestamp, level, message, source, host, service

```bash
# Check for transformed message
docker compose logs vector | grep "$TEST_SESSION_ID" | grep '"level":"INFO"'
# Expected Output:
# {"appname":"test-service","counter_value":null,"facility":"user","gauge_value":null,"host":"ubuntu","hostname":"ubuntu","kind":"","labels":{},"level":"INFO","message":"NORMAL_OPERATION TEST-20250903-143022-a1b2c3d4 system startup completed","name":"","namespace":"","raw_log":"{...}","service":"test-service","severity":"info","source":"syslog","source_ip":"172.18.0.1","source_type":"syslog","tags":{},"timestamp":"2025-09-03 14:30:22.000"}
```

**Step 4**: Verify Vector sends message to ClickHouse  
**Input**: Vector metrics query for sink statistics  
**Output**: Incremented event count for ClickHouse sink  
**Validation**: events_out_total shows message processed by ClickHouse sink

```bash
# Check Vector sink metrics
curl -s http://localhost:8686/metrics | grep 'vector_events_out_total.*clickhouse'
# Expected Output:
# vector_events_out_total{component_id="clickhouse",component_type="sink"} 1
```

**Step 5**: Verify message stored in ClickHouse  
**Input**: ClickHouse SQL query for test session message  
**Output**: Retrieved message with all fields populated  
**Validation**: Message found with correct timestamp, content, and metadata

```bash
# Query ClickHouse for the message
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 1"
# Expected Output:
# 2025-09-03 14:30:22.000	INFO	NORMAL_OPERATION TEST-20250903-143022-a1b2c3d4 system startup completed	syslog	ubuntu	test-service
```

**Step 6**: Verify no anomaly detection triggered  
**Input**: VictoriaMetrics query for anomaly metrics  
**Output**: No anomaly metrics for this session  
**Validation**: Query returns empty result or no anomaly flags

```bash
# Check for anomaly detection on this message
curl -s "http://localhost:8428/api/v1/query?query=anomaly_detected{session_id=\"$TEST_SESSION_ID\"}"
# Expected Output: 
# {"status":"success","data":{"resultType":"vector","result":[]}}
```

### **TC-001 Success Criteria**
- ✅ Message successfully sent via UDP
- ✅ Vector receives and parses syslog message
- ✅ Vector transforms message with correct ClickHouse fields
- ✅ Vector sink metrics show successful processing
- ✅ Message stored in ClickHouse with all fields
- ✅ No anomaly detection triggered

---

## 🚨 Test Case TC-002: Anomaly Detection Flow

### **Test Description**
Validates that anomalous log patterns trigger the complete detection and correlation pipeline, resulting in incident creation.

### **Step-by-Step Execution**

**Step 1**: Send anomalous error message  
**Input**: High-severity error message via TCP syslog  
**Output**: Message transmitted to Vector  
**Validation**: Connection successful, message sent

```bash
# Send anomalous error message via TCP
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) critical-service: ERROR $TEST_SESSION_ID CRITICAL_FAILURE database connection lost timeout exceeded" | nc localhost 1515
# Expected Output: (No output = success)
```

**Step 2**: Verify Vector processes anomalous message  
**Input**: Vector log query for error message  
**Output**: Processed message with error severity  
**Validation**: Message contains error indicators and proper formatting

```bash
# Check Vector logs for anomalous message
docker compose logs vector | grep "$TEST_SESSION_ID" | grep "CRITICAL_FAILURE"
# Expected Output:
# {"appname":"critical-service","facility":"daemon","host":"ubuntu","hostname":"ubuntu","message":"ERROR TEST-20250903-143022-a1b2c3d4 CRITICAL_FAILURE database connection lost timeout exceeded","severity":"err","source_ip":"172.18.0.1","source_type":"syslog","timestamp":"2025-09-03T14:35:22Z"}
```

**Step 3**: Verify message stored in ClickHouse  
**Input**: ClickHouse query for anomalous message  
**Output**: Stored message with error details  
**Validation**: Message retrieved with correct severity and content

```bash
# Query ClickHouse for anomalous message
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%CRITICAL_FAILURE%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 1"
# Expected Output:
# 2025-09-03 14:35:22.000	INFO	ERROR TEST-20250903-143022-a1b2c3d4 CRITICAL_FAILURE database connection lost timeout exceeded	syslog	ubuntu	critical-service
```

**Step 4**: Verify anomaly detection triggers  
**Input**: Anomaly service logs query  
**Output**: Anomaly detection processing log  
**Validation**: Service processes the error and flags it as anomalous

```bash
# Check anomaly detection service logs
docker compose logs anomaly-detection | grep "$TEST_SESSION_ID"
# Expected Output:
# [2025-09-03 14:35:25] INFO: Processing message for anomaly detection: TEST-20250903-143022-a1b2c3d4
# [2025-09-03 14:35:25] WARNING: Anomaly detected - CRITICAL_FAILURE pattern matched
```

**Step 5**: Verify NATS message published  
**Input**: NATS monitoring for anomaly.detected subject  
**Output**: Anomaly event published to NATS  
**Validation**: Message appears on anomaly.detected subject

```bash
# Monitor NATS for anomaly events (run in background for 10 seconds)
timeout 10s docker exec aiops-nats nats sub "anomaly.detected" --count=1 | grep "$TEST_SESSION_ID"
# Expected Output:
# {"timestamp":"2025-09-03T14:35:25Z","session_id":"TEST-20250903-143022-a1b2c3d4","anomaly_type":"CRITICAL_FAILURE","severity":"high","message":"database connection lost timeout exceeded","host":"ubuntu","service":"critical-service"}
```

**Step 6**: Verify Benthos processes anomaly event  
**Input**: Benthos processing metrics and logs  
**Output**: Event correlation processing statistics  
**Validation**: Benthos receives and processes the anomaly event

```bash
# Check Benthos processing statistics
curl -s http://localhost:4195/stats | jq '.input.broker.received'
# Expected Output: 1 (or incremented count)

# Check Benthos logs for correlation processing
docker compose logs benthos | grep "$TEST_SESSION_ID"
# Expected Output:
# [2025-09-03 14:35:26] INFO: Processing anomaly event for correlation: TEST-20250903-143022-a1b2c3d4
# [2025-09-03 14:35:26] INFO: Correlation rules applied, creating incident
```

**Step 7**: Verify incident creation  
**Input**: Incident API query for created incident  
**Output**: Created incident with correlation details  
**Validation**: Incident exists with proper metadata and status

```bash
# Query incident API for created incident
curl -s "http://localhost:8081/api/v1/incidents?session_id=$TEST_SESSION_ID" | jq '.'
# Expected Output:
# {
#   "incidents": [
#     {
#       "id": "INC-2025090314352601",
#       "session_id": "TEST-20250903-143022-a1b2c3d4",
#       "severity": "high",
#       "status": "open",
#       "title": "CRITICAL_FAILURE detected on ubuntu",
#       "description": "database connection lost timeout exceeded",
#       "created_at": "2025-09-03T14:35:26Z",
#       "correlation_id": "corr-a1b2c3d4",
#       "affected_services": ["critical-service"],
#       "host": "ubuntu"
#     }
#   ]
# }
```

**Step 8**: Verify incident published to NATS  
**Input**: NATS monitoring for incidents.created subject  
**Output**: Incident creation event  
**Validation**: Incident notification published for downstream systems

```bash
# Monitor NATS for incident creation events
timeout 5s docker exec aiops-nats nats sub "incidents.created" --count=1 | grep "$TEST_SESSION_ID"
# Expected Output:
# {"incident_id":"INC-2025090314352601","session_id":"TEST-20250903-143022-a1b2c3d4","severity":"high","status":"open","created_at":"2025-09-03T14:35:26Z","correlation_id":"corr-a1b2c3d4"}
```

### **TC-002 Success Criteria**
- ✅ Anomalous message successfully sent via TCP
- ✅ Vector processes message with error indicators
- ✅ Message stored in ClickHouse
- ✅ Anomaly detection service identifies the anomaly
- ✅ Anomaly event published to NATS
- ✅ Benthos processes and correlates the event
- ✅ Incident created via incident API
- ✅ Incident notification published to NATS

---

## 📊 Test Case TC-003: Host Metrics Flow

### **Test Description**
Validates system metrics collection from the host, processing through Vector, and storage in both ClickHouse and VictoriaMetrics.

### **Step-by-Step Execution**

**Step 1**: Verify host metrics collection  
**Input**: Vector host metrics source  
**Output**: System metrics collected (CPU, memory, disk, network)  
**Validation**: Metrics appear in Vector logs

```bash
# Check Vector host metrics collection
docker compose logs vector | grep '"name":"host_cpu_seconds_total"' | head -1
# Expected Output:
# {"counter":{"value":45.2},"name":"host_cpu_seconds_total","namespace":"host","tags":{"cpu":"0","mode":"user"},"timestamp":"2025-09-03T14:40:00Z","kind":"absolute"}
```

**Step 2**: Verify metrics transformation for ClickHouse  
**Input**: Vector metric-to-log transformation  
**Output**: Metrics converted to log format with ClickHouse fields  
**Validation**: Transformed metrics contain required fields

```bash
# Check transformed metrics for ClickHouse
docker compose logs vector | grep '"source":"host_metrics"' | head -1
# Expected Output:
# {"counter_value":null,"gauge_value":null,"host":"ubuntu","kind":"","labels":{},"level":"INFO","message":"Metric: host_cpu_seconds_total = 45.2","name":"","namespace":"","raw_log":"{...}","service":"metrics-collector","source":"host_metrics","tags":{},"timestamp":"2025-09-03 14:40:00.000"}
```

**Step 3**: Verify metrics stored in ClickHouse  
**Input**: ClickHouse query for recent host metrics  
**Output**: Metrics data in logs.raw table  
**Validation**: Host metrics present with proper formatting

```bash
# Query ClickHouse for host metrics
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, message, source, host FROM logs.raw WHERE source = 'host_metrics' ORDER BY timestamp DESC LIMIT 3"
# Expected Output:
# 2025-09-03 14:40:00.000	Metric: host_cpu_seconds_total = 45.2	host_metrics	ubuntu
# 2025-09-03 14:40:00.000	Metric: host_memory_total_bytes = 8589934592	host_metrics	ubuntu
# 2025-09-03 14:40:00.000	Metric: host_disk_usage_bytes = 12884901888	host_metrics	ubuntu
```

**Step 4**: Verify metrics forwarded to VictoriaMetrics  
**Input**: VictoriaMetrics query for host metrics  
**Output**: Time series data for system metrics  
**Validation**: Metrics available for monitoring and alerting

```bash
# Query VictoriaMetrics for host CPU metrics
curl -s "http://localhost:8428/api/v1/query?query=host_cpu_seconds_total" | jq '.data.result[0]'
# Expected Output:
# {
#   "metric": {
#     "__name__": "host_cpu_seconds_total",
#     "cpu": "0",
#     "instance": "ubuntu",
#     "job": "host_metrics",
#     "mode": "user"
#   },
#   "value": [1725376800, "45.2"]
# }
```

**Step 5**: Verify metrics scraping by vmagent  
**Input**: vmagent configuration and scraping status  
**Output**: Successful metric scraping from Vector  
**Validation**: vmagent successfully collects and forwards metrics

```bash
# Check vmagent scraping statistics
curl -s http://localhost:8429/metrics | grep 'vm_promscrape_targets{job="vector"}'
# Expected Output:
# vm_promscrape_targets{job="vector",status="up"} 1
```

### **TC-003 Success Criteria**
- ✅ Host metrics collected by Vector (CPU, memory, disk, network)
- ✅ Metrics transformed to ClickHouse log format
- ✅ Metrics stored in ClickHouse logs.raw table
- ✅ Metrics available in VictoriaMetrics for querying
- ✅ vmagent successfully scrapes Vector metrics endpoint

---

## 🌐 Test Case TC-004: SNMP Network Data Flow

### **Test Description**
Validates network device monitoring through SNMP collection, NATS messaging, Vector processing, and ClickHouse storage.

### **Step-by-Step Execution**

**Step 1**: Verify SNMP collector service  
**Input**: Network device collector health check  
**Output**: Service running and collecting SNMP data  
**Validation**: Collector service responds to health check

```bash
# Check SNMP collector health
curl -s http://localhost:8082/health
# Expected Output:
# {"status":"healthy","devices_monitored":2,"last_collection":"2025-09-03T14:45:00Z"}
```

**Step 2**: Verify SNMP data published to NATS  
**Input**: NATS monitoring for telemetry.network.* subjects  
**Output**: SNMP data events on NATS bus  
**Validation**: Network telemetry data flowing through NATS

```bash
# Monitor NATS for network telemetry (run for 10 seconds)
timeout 10s docker exec aiops-nats nats sub "telemetry.network.>" --count=3
# Expected Output:
# [telemetry.network.switch01] {"device_id":"switch01","interface":"GigabitEthernet0/1","rx_bytes":1048576,"tx_bytes":2097152,"timestamp":"2025-09-03T14:45:15Z","collection_session":"SNMP-14451501"}
# [telemetry.network.router01] {"device_id":"router01","interface":"FastEthernet0/0","rx_packets":15420,"tx_packets":18650,"timestamp":"2025-09-03T14:45:15Z","collection_session":"SNMP-14451502"}
# [telemetry.network.switch01] {"device_id":"switch01","cpu_utilization":15.2,"memory_utilization":45.8,"timestamp":"2025-09-03T14:45:15Z","collection_session":"SNMP-14451503"}
```

**Step 3**: Verify Vector receives SNMP data from NATS  
**Input**: Vector NATS source logs  
**Output**: SNMP data processed by Vector  
**Validation**: Vector logs show NATS message consumption

```bash
# Check Vector logs for SNMP data from NATS
docker compose logs vector | grep '"source_type":"nats"' | grep "telemetry.network" | head -1
# Expected Output:
# {"device_id":"switch01","interface":"GigabitEthernet0/1","rx_bytes":1048576,"tx_bytes":2097152,"source_type":"nats","subject":"telemetry.network.switch01","timestamp":"2025-09-03T14:45:15Z"}
```

**Step 4**: Verify SNMP data transformation  
**Input**: Vector SNMP data transform logs  
**Output**: SNMP data formatted for ClickHouse storage  
**Validation**: Data contains required ClickHouse fields

```bash
# Check transformed SNMP data
docker compose logs vector | grep '"source":"snmp"' | head -1
# Expected Output:
# {"counter_value":null,"device_id":"switch01","gauge_value":null,"host":"switch01","interface":"GigabitEthernet0/1","kind":"","labels":{"device_type":"switch","interface":"GigabitEthernet0/1"},"level":"INFO","message":"Network interface metrics: rx_bytes=1048576, tx_bytes=2097152","name":"","namespace":"","raw_log":"{...}","rx_bytes":1048576,"service":"network-monitoring","source":"snmp","tags":{},"timestamp":"2025-09-03 14:45:15.000","tx_bytes":2097152}
```

**Step 5**: Verify SNMP data stored in ClickHouse  
**Input**: ClickHouse query for SNMP network data  
**Output**: Network telemetry data in storage  
**Validation**: SNMP metrics retrievable from ClickHouse

```bash
# Query ClickHouse for SNMP network data
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, message, source, host, service FROM logs.raw WHERE source = 'snmp' ORDER BY timestamp DESC LIMIT 3"
# Expected Output:
# 2025-09-03 14:45:15.000	Network interface metrics: rx_bytes=1048576, tx_bytes=2097152	snmp	switch01	network-monitoring
# 2025-09-03 14:45:15.000	Network interface metrics: rx_packets=15420, tx_packets=18650	snmp	router01	network-monitoring
# 2025-09-03 14:45:15.000	Device health metrics: cpu_utilization=15.2, memory_utilization=45.8	snmp	switch01	network-monitoring
```

**Step 6**: Verify network anomaly detection capability  
**Input**: Trigger high bandwidth usage scenario  
**Output**: Network anomaly detection and alerting  
**Validation**: High utilization detected and flagged

```bash
# Simulate high bandwidth usage alert
curl -X POST http://localhost:8082/simulate/high_bandwidth \
  -H "Content-Type: application/json" \
  -d '{"device_id":"switch01","interface":"GigabitEthernet0/1","utilization_percent":95}'

# Check for network anomaly detection
sleep 5
docker compose logs enhanced-anomaly-detection | grep "network_utilization_high"
# Expected Output:
# [2025-09-03 14:46:00] WARNING: Network anomaly detected - switch01 interface utilization 95% exceeds threshold
```

### **TC-004 Success Criteria**
- ✅ SNMP collector service operational and monitoring devices
- ✅ SNMP data successfully published to NATS telemetry subjects
- ✅ Vector receives and processes SNMP data from NATS
- ✅ SNMP data transformed with ClickHouse-compatible fields
- ✅ Network telemetry data stored in ClickHouse
- ✅ Network anomaly detection operational for high utilization

---

## 📁 Test Case TC-005: File-based Log Flow

### **Test Description**
Validates file-based log ingestion from mounted volumes, processing through Vector, and storage in ClickHouse.

### **Step-by-Step Execution**

**Step 1**: Create test log file  
**Input**: Write test log entries to monitored directory  
**Output**: Log file created with test entries  
**Validation**: File exists and contains expected content

```bash
# Create test log file in monitored directory
echo "$(date '+%Y-%m-%d %H:%M:%S') INFO [application] $TEST_SESSION_ID Application started successfully" > /tmp/test-app.log
echo "$(date '+%Y-%m-%d %H:%M:%S') WARN [database] $TEST_SESSION_ID Connection pool nearing capacity" >> /tmp/test-app.log
echo "$(date '+%Y-%m-%d %H:%M:%S') ERROR [auth] $TEST_SESSION_ID Failed login attempt from user admin" >> /tmp/test-app.log

# Copy to Vector's monitored directory (simulating application logs)
docker exec aiops-vector sh -c "mkdir -p /var/log/sample && cp /tmp/test-app.log /var/log/sample/"

# Verify file creation
docker exec aiops-vector ls -la /var/log/sample/
# Expected Output:
# -rw-r--r-- 1 root root 285 Sep  3 14:50 test-app.log
```

**Step 2**: Verify Vector detects and reads log file  
**Input**: Vector file source monitoring  
**Output**: Log file detected and content read  
**Validation**: Vector logs show file processing activity

```bash
# Check Vector logs for file detection
docker compose logs vector | grep "file" | grep "$TEST_SESSION_ID"
# Expected Output:
# {"file":"/var/log/sample/test-app.log","host":"ubuntu","message":"INFO [application] TEST-20250903-143022-a1b2c3d4 Application started successfully","source_type":"file","timestamp":"2025-09-03T14:50:22Z"}
```

**Step 3**: Verify file log transformation  
**Input**: Vector file log processing  
**Output**: File logs transformed for ClickHouse storage  
**Validation**: Transformed logs contain required fields

```bash
# Check transformed file logs
docker compose logs vector | grep '"source":"file"' | grep "$TEST_SESSION_ID"
# Expected Output:
# {"counter_value":null,"file":"/var/log/sample/test-app.log","gauge_value":null,"host":"ubuntu","kind":"","labels":{},"level":"INFO","message":"INFO [application] TEST-20250903-143022-a1b2c3d4 Application started successfully","name":"","namespace":"","raw_log":"{...}","service":"file-logs","source":"file","tags":{},"timestamp":"2025-09-03 14:50:22.000"}
```

**Step 4**: Verify file logs stored in ClickHouse  
**Input**: ClickHouse query for file-based logs  
**Output**: File log entries in storage  
**Validation**: All log levels (INFO, WARN, ERROR) stored correctly

```bash
# Query ClickHouse for file logs with session ID
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, level, message, source FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' AND source = 'file' ORDER BY timestamp ASC"
# Expected Output:
# 2025-09-03 14:50:22.000	INFO	INFO [application] TEST-20250903-143022-a1b2c3d4 Application started successfully	file
# 2025-09-03 14:50:22.000	WARN	WARN [database] TEST-20250903-143022-a1b2c3d4 Connection pool nearing capacity	file
# 2025-09-03 14:50:22.000	ERROR	ERROR [auth] TEST-20250903-143022-a1b2c3d4 Failed login attempt from user admin	file
```

**Step 5**: Verify file rotation handling  
**Input**: Simulate log file rotation  
**Output**: Vector continues reading after rotation  
**Validation**: No log entries lost during rotation

```bash
# Simulate log rotation
docker exec aiops-vector sh -c "mv /var/log/sample/test-app.log /var/log/sample/test-app.log.old"
docker exec aiops-vector sh -c "echo '$(date '+%Y-%m-%d %H:%M:%S') INFO [system] $TEST_SESSION_ID Log rotation completed' > /var/log/sample/test-app.log"

# Wait for Vector to detect new file
sleep 10

# Verify Vector processes rotated file
docker compose logs vector | grep "Log rotation completed" | grep "$TEST_SESSION_ID"
# Expected Output:
# {"file":"/var/log/sample/test-app.log","host":"ubuntu","message":"INFO [system] TEST-20250903-143022-a1b2c3d4 Log rotation completed","source_type":"file","timestamp":"2025-09-03T14:52:30Z"}
```

### **TC-005 Success Criteria**
- ✅ Test log file created in monitored directory
- ✅ Vector detects and reads log file content
- ✅ File logs transformed with ClickHouse-compatible fields
- ✅ All log levels (INFO, WARN, ERROR) stored in ClickHouse
- ✅ Log file rotation handled without data loss

---

## 🔗 Test Case TC-006: End-to-End Incident Correlation

### **Test Description**
Validates the complete incident lifecycle including correlation rules, deduplication, suppression, and API integration.

### **Step-by-Step Execution**

**Step 1**: Configure correlation rules  
**Input**: Update Benthos correlation configuration  
**Output**: Rules configured for service correlation  
**Validation**: Configuration applied and service restarted

```bash
# Check current Benthos correlation configuration
curl -s http://localhost:4195/config | jq '.pipeline.processors[] | select(.mapping)'
# Expected Output: Current correlation mapping configuration

# Verify correlation cache settings
curl -s http://localhost:4195/stats | jq '.cache'
# Expected Output:
# {
#   "correlation_cache": {
#     "size": 1000,
#     "ttl": 300
#   }
# }
```

**Step 2**: Generate correlated error sequence  
**Input**: Send multiple related error messages  
**Output**: Sequence of correlated events  
**Validation**: Multiple messages sent successfully

```bash
# Send sequence of related errors
CORRELATION_ID="CORR-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

# Database connection error
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) db-service: ERROR $TEST_SESSION_ID $CORRELATION_ID database connection failed" | nc localhost 1515

# Application service error (related)
sleep 2
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) app-service: ERROR $TEST_SESSION_ID $CORRELATION_ID service unavailable due to database" | nc localhost 1515

# Web service error (related)  
sleep 2
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) web-service: ERROR $TEST_SESSION_ID $CORRELATION_ID HTTP 503 service temporarily unavailable" | nc localhost 1515
```

**Step 3**: Verify anomaly detection processes sequence  
**Input**: Monitor anomaly detection for error sequence  
**Output**: Multiple anomalies detected for correlation  
**Validation**: All three errors flagged as anomalous

```bash
# Check anomaly detection logs for correlation sequence
docker compose logs anomaly-detection | grep "$CORRELATION_ID"
# Expected Output:
# [2025-09-03 14:55:10] WARNING: Anomaly detected - database connection failed
# [2025-09-03 14:55:12] WARNING: Anomaly detected - service unavailable due to database  
# [2025-09-03 14:55:14] WARNING: Anomaly detected - HTTP 503 service temporarily unavailable
```

**Step 4**: Verify NATS publishes correlated events  
**Input**: Monitor NATS for anomaly.detected events  
**Output**: Multiple anomaly events with correlation metadata  
**Validation**: Events contain correlation identifiers

```bash
# Monitor NATS for correlated anomaly events
timeout 15s docker exec aiops-nats nats sub "anomaly.detected" --count=3 | grep "$CORRELATION_ID"
# Expected Output:
# {"timestamp":"2025-09-03T14:55:10Z","correlation_id":"CORR-20250903-145510-b1c2d3e4","anomaly_type":"database_connection_failure","severity":"high","message":"database connection failed","service":"db-service"}
# {"timestamp":"2025-09-03T14:55:12Z","correlation_id":"CORR-20250903-145510-b1c2d3e4","anomaly_type":"service_dependency_failure","severity":"high","message":"service unavailable due to database","service":"app-service"}
# {"timestamp":"2025-09-03T14:55:14Z","correlation_id":"CORR-20250903-145510-b1c2d3e4","anomaly_type":"http_service_error","severity":"medium","message":"HTTP 503 service temporarily unavailable","service":"web-service"}
```

**Step 5**: Verify Benthos correlation processing  
**Input**: Benthos correlation engine processing  
**Output**: Events correlated into single incident  
**Validation**: Correlation logic identifies related events

```bash
# Check Benthos correlation processing logs
docker compose logs benthos | grep "$CORRELATION_ID"
# Expected Output:
# [2025-09-03 14:55:15] INFO: Processing correlation for CORR-20250903-145510-b1c2d3e4
# [2025-09-03 14:55:15] INFO: Correlation rule matched: cascading_service_failure
# [2025-09-03 14:55:15] INFO: Creating correlated incident for 3 related events
# [2025-09-03 14:55:15] INFO: Incident correlation completed: INC-2025090314551501
```

**Step 6**: Verify incident creation with correlation  
**Input**: Query incident API for correlated incident  
**Output**: Single incident representing multiple related events  
**Validation**: Incident contains all correlated events and proper metadata

```bash
# Query incident API for correlated incident
curl -s "http://localhost:8081/api/v1/incidents?correlation_id=$CORRELATION_ID" | jq '.'
# Expected Output:
# {
#   "incidents": [
#     {
#       "id": "INC-2025090314551501",
#       "correlation_id": "CORR-20250903-145510-b1c2d3e4",
#       "title": "Cascading Service Failure - Database Connectivity",
#       "description": "Multiple service failures detected following database connection loss",
#       "severity": "critical",
#       "status": "open",
#       "created_at": "2025-09-03T14:55:15Z",
#       "affected_services": ["db-service", "app-service", "web-service"],
#       "correlation_rule": "cascading_service_failure",
#       "event_count": 3,
#       "root_cause": "database_connection_failure",
#       "related_events": [
#         {"service": "db-service", "message": "database connection failed"},
#         {"service": "app-service", "message": "service unavailable due to database"},
#         {"service": "web-service", "message": "HTTP 503 service temporarily unavailable"}
#       ]
#     }
#   ]
# }
```

**Step 7**: Verify suppression for duplicate events  
**Input**: Send duplicate error message  
**Output**: Suppressed duplicate, no new incident  
**Validation**: Existing incident updated, no new incident created

```bash
# Send duplicate database error
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) db-service: ERROR $TEST_SESSION_ID $CORRELATION_ID database connection failed" | nc localhost 1515

# Wait for processing
sleep 10

# Verify no new incident created (count should remain 1)
INCIDENT_COUNT=$(curl -s "http://localhost:8081/api/v1/incidents?correlation_id=$CORRELATION_ID" | jq '.incidents | length')
echo "Incident count: $INCIDENT_COUNT"
# Expected Output: Incident count: 1

# Verify existing incident updated with suppression info
curl -s "http://localhost:8081/api/v1/incidents?correlation_id=$CORRELATION_ID" | jq '.incidents[0].suppressed_duplicates'
# Expected Output: 1
```

### **TC-006 Success Criteria**
- ✅ Correlation rules configured and operational
- ✅ Sequence of related errors generated and processed
- ✅ All errors detected as anomalies by detection service
- ✅ Correlated anomaly events published to NATS
- ✅ Benthos correlation engine processes related events
- ✅ Single correlated incident created for multiple events
- ✅ Duplicate event suppression working correctly

---

## 📊 Result Validation and Storage Format

### **Test Result Template**

```json
{
  "test_session": {
    "session_id": "TEST-20250903-143022-a1b2c3d4",
    "timestamp": "2025-09-03T14:30:22Z",
    "tester": "manual",
    "environment": "local-docker"
  },
  "test_cases": {
    "TC-001": {
      "name": "Normal Syslog Flow",
      "status": "PASSED",
      "execution_time": "45s",
      "steps": [
        {
          "step": 1,
          "description": "Send normal UDP syslog message",
          "status": "PASSED",
          "input": "UDP syslog message",
          "output": "Message transmitted successfully",
          "validation": "No connection errors"
        }
      ],
      "evidence": {
        "vector_logs": "Message processed",
        "clickhouse_query": "1 record found",
        "metrics": "events_out_total incremented"
      }
    }
  },
  "summary": {
    "total_tests": 6,
    "passed": 5,
    "failed": 1,
    "success_rate": "83.3%",
    "critical_failures": []
  }
}
```

### **Issue Tracking Template**

```markdown
## Issue Report Template

**Issue ID**: ISSUE-{YYYY}{MM}{DD}-{HHMM}{SS}-{UUID}
**Test Case**: TC-{NUMBER}
**Priority**: {Critical|High|Medium|Low}
**Status**: {Open|In Progress|Resolved|Closed}

### Issue Description
Brief description of the issue encountered during testing.

### Test Step Details
- **Step Number**: {X}
- **Step Description**: {Description}
- **Expected Result**: {What should happen}
- **Actual Result**: {What actually happened}
- **Input Used**: {Command/data used}

### Environment Information
- **Test Session ID**: {TEST_SESSION_ID}
- **Timestamp**: {ISO 8601 timestamp}
- **Component**: {Service/component involved}
- **Docker Compose Version**: {Version}

### Evidence/Logs
```bash
# Commands used for investigation
{Investigation commands}

# Relevant log output
{Log excerpts}
```

### Reproduction Steps
1. {Step 1}
2. {Step 2}
3. {Step 3}

### Impact Assessment
- **Service Affected**: {Service name}
- **Data Flow Impact**: {Which flow is broken}
- **Severity Justification**: {Why this priority level}

### Resolution Notes
{Steps taken to resolve, if resolved}

### Related Issues
- Related to: {Other issue IDs}
- Depends on: {Dependencies}
```

---

## 🔧 Correlation Rules and Incident Configuration

### **Modifying Correlation Rules**

**Step 1**: Update Benthos correlation configuration  
**Input**: Modified benthos.yaml with new correlation rules  
**Output**: Updated correlation logic  
**Validation**: Configuration reload successful

```bash
# Backup current configuration
docker exec aiops-benthos cat /benthos/benthos.yaml > benthos-backup.yaml

# Edit correlation rules (example: add new pattern)
# Add to correlation mapping in benthos.yaml:
# root.correlation_rules.new_pattern = if this.message.contains("PATTERN") { "new_incident_type" } else { null }

# Reload configuration
docker exec aiops-benthos pkill -HUP benthos
# Expected Output: Configuration reloaded successfully
```

**Step 2**: Test new correlation rule  
**Input**: Send message matching new pattern  
**Output**: New correlation rule applied  
**Validation**: Incident created with new classification

```bash
# Test new correlation pattern
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) test-service: ERROR $TEST_SESSION_ID NEW_PATTERN custom error type" | nc localhost 1515

# Verify new correlation applied
sleep 10
curl -s "http://localhost:8081/api/v1/incidents?session_id=$TEST_SESSION_ID" | jq '.incidents[0].incident_type'
# Expected Output: "new_incident_type"
```

### **Adjusting Suppression Thresholds**

**Step 1**: Modify suppression configuration  
**Input**: Updated suppression timeouts and thresholds  
**Output**: New suppression behavior  
**Validation**: Suppression rules apply correctly

```bash
# Update suppression threshold (example: reduce duplicate window to 60 seconds)
# In benthos.yaml, modify:
# root.suppression_window = "60s"
# root.duplicate_threshold = 5

# Test suppression with rapid duplicates
for i in {1..7}; do
  echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) test-service: ERROR $TEST_SESSION_ID DUPLICATE_TEST message $i" | nc localhost 1515
  sleep 5
done

# Verify suppression applied after threshold
curl -s "http://localhost:8081/api/v1/incidents?session_id=$TEST_SESSION_ID" | jq '.incidents[0].suppressed_duplicates'
# Expected Output: 2 (7 messages - 5 threshold = 2 suppressed)
```

---

## 🎯 Final Comprehensive Execution Plan

### **Complete End-to-End Validation Sequence**

**Phase 1: Environment Setup and Validation (15 minutes)**
1. Execute SETUP-001: Verify all services healthy
2. Execute SETUP-002: Generate test session ID
3. Validate prerequisite configurations
4. Establish baseline metrics

**Phase 2: Individual Data Flow Testing (45 minutes)**
1. Execute TC-001: Normal Syslog Flow (10 minutes)
2. Execute TC-003: Host Metrics Flow (10 minutes)  
3. Execute TC-004: SNMP Network Data Flow (15 minutes)
4. Execute TC-005: File-based Log Flow (10 minutes)

**Phase 3: Advanced Correlation Testing (30 minutes)**
1. Execute TC-002: Anomaly Detection Flow (15 minutes)
2. Execute TC-006: End-to-End Incident Correlation (15 minutes)

**Phase 4: Performance and Edge Case Testing (20 minutes)**
1. High volume message testing
2. Service failure simulation and recovery
3. Network partition testing
4. Resource exhaustion scenarios

**Phase 5: Results Compilation and Analysis (10 minutes)**
1. Compile test results using standard template
2. Generate pass/fail summary
3. Document any issues found
4. Create improvement recommendations

### **Success Criteria for Complete Validation**
- ✅ All services operational (100% health checks pass)
- ✅ All data flows functional (6/6 test cases pass)
- ✅ End-to-end message tracking working
- ✅ Anomaly detection and correlation operational
- ✅ Incident creation and API integration functional
- ✅ No critical data loss or processing failures
- ✅ Performance within acceptable thresholds

### **Failure Response Protocol**
1. **Critical Failure**: Stop testing, implement immediate fix
2. **High Priority**: Complete current test case, address before continuing
3. **Medium Priority**: Note issue, continue testing, address in batch
4. **Low Priority**: Document for future improvement

This comprehensive guide provides the framework for validating the complete AIOps NAAS pipeline with precise step-by-step instructions, input/output validation, and structured result documentation.