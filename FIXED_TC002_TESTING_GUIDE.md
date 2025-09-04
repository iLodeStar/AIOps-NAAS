# FIXED TC-002: Anomaly Detection Flow - Step-by-Step Validation

## Critical Fix Applied
✅ **Root Cause Resolved**: Enhanced Vector configuration to send ERROR/WARNING syslog messages to NATS for real-time processing by anomaly detection service.

✅ **Enhanced Anomaly Service**: Added log-based anomaly detection capability to process individual syslog messages with tracking IDs.

## TC-002: Anomaly Detection Flow (CORRECTED)

### **Test Description**
Validates that ERROR/WARNING syslog messages trigger the complete anomaly detection and correlation pipeline, resulting in incident creation with end-to-end tracking.

### **Corrected Data Flow**
```
Syslog ERROR/WARNING → Vector → [ClickHouse + NATS] → Anomaly Detection → NATS → Benthos → Incidents
```

### **Step-by-Step Execution (CORRECTED)**

#### **Pre-Execution Setup**
```bash
# Generate unique session ID for tracking
TEST_SESSION_ID="TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "=== TEST SESSION: $TEST_SESSION_ID ==="
echo "Copy this ID for tracking through the pipeline"
```

#### **Step 1**: Send anomalous error message  
**Input**: High-severity error message via TCP syslog with tracking ID  
**Output**: Message transmitted to Vector  
**Validation**: Message appears in Vector logs

```bash
# Send ERROR message that will trigger anomaly detection
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) critical-service: ERROR $TEST_SESSION_ID Critical database connection failure - timeout exceeded" | nc localhost 1515

# Wait for processing
sleep 5

# VALIDATION: Check Vector processed the message
docker compose logs vector | tail -20 | grep "$TEST_SESSION_ID"
# EXPECTED: JSON log entry with the tracking ID
```

#### **Step 2**: Verify Vector sends message to ClickHouse AND NATS  
**Input**: Vector processing logs and NATS subject monitoring  
**Output**: Message stored in ClickHouse and sent to anomalous logs NATS subject  
**Validation**: Data visible in both ClickHouse and NATS

```bash
# Check ClickHouse storage
docker exec aiops-clickhouse clickhouse-client --query="SELECT timestamp, level, message, host, service FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 2"
# EXPECTED: Row with ERROR level and tracking ID

# Check NATS anomalous logs subject (enhanced Vector sends ERROR logs here)
timeout 10s docker exec aiops-nats nats sub "logs.anomalous" --count=1 | grep "$TEST_SESSION_ID" || echo "No immediate message - may have been processed already"
# EXPECTED: JSON with tracking_id field and anomaly metadata
```

#### **Step 3**: Verify anomaly detection service processes the log  
**Input**: Anomaly detection service logs  
**Output**: Log anomaly detection processing message  
**Validation**: Service logs show tracking ID processing

```bash
# Check anomaly detection service processed the log message
docker compose logs anomaly-detection | grep "$TEST_SESSION_ID"
# EXPECTED OUTPUT (FIXED):
# INFO - Processing anomalous log: tracking_id=TEST-20250903-143022-a1b2c3d4, message='ERROR TEST-20250903-143022-a1b2c3d4 Critical database...'
# INFO - Published log anomaly with tracking ID: TEST-20250903-143022-a1b2c3d4
```

#### **Step 4**: Verify anomaly event published to NATS  
**Input**: NATS anomaly.detected subject subscription  
**Output**: Anomaly event with tracking ID metadata  
**Validation**: Anomaly event contains log information and tracking ID

```bash
# Check for anomaly event on NATS
timeout 15s docker exec aiops-nats nats sub "anomaly.detected" --count=1 | grep -i "$TEST_SESSION_ID"
# EXPECTED OUTPUT:
# {"timestamp":"2025-09-04T...","metric_name":"log_anomaly","anomaly_score":0.9,"detector_name":"log_pattern_detector","metadata":{"tracking_id":"TEST-20250903-143022-a1b2c3d4",...}}
```

#### **Step 5**: Verify Benthos processes anomaly event  
**Input**: Benthos processing logs  
**Output**: Correlation processing confirmation  
**Validation**: Benthos logs show event correlation

```bash
# Check Benthos processed the anomaly event
docker compose logs benthos | grep -A 5 -B 5 "$TEST_SESSION_ID"
# EXPECTED: Correlation processing and incident creation logs
```

#### **Step 6**: Verify incident creation  
**Input**: Incident API query  
**Output**: Created incident with tracking ID  
**Validation**: Incident exists with proper metadata

```bash
# Check incident was created
timeout 10s docker exec aiops-nats nats sub "incidents.created" --count=1 | grep "$TEST_SESSION_ID"
# EXPECTED: Incident JSON with tracking ID in metadata

# Alternative: Check incident API
curl -s "http://localhost:8081/api/v1/incidents" | jq --arg tracking_id "$TEST_SESSION_ID" '.[] | select(.metadata.tracking_id==$tracking_id)'
# EXPECTED: Incident object with status="open", tracking ID in metadata
```

### **TC-002 Success Criteria (CORRECTED)**
- ✅ ERROR message successfully sent via TCP with tracking ID
- ✅ Vector processes message and sends to both ClickHouse and NATS  
- ✅ Message stored in ClickHouse with ERROR level
- ✅ Vector sends anomalous log to NATS logs.anomalous subject
- ✅ Anomaly detection service processes log and extracts tracking ID
- ✅ Log-based anomaly event published to NATS anomaly.detected subject
- ✅ Benthos processes and correlates the log anomaly event
- ✅ Incident created with tracking ID in metadata
- ✅ Incident notification published to NATS incidents.created subject

### **Complete Validation Command Sequence**
```bash
#!/bin/bash
# TC-002 Complete Validation Script

# Setup
TEST_SESSION_ID="TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "=== TC-002 ANOMALY DETECTION FLOW TEST ==="
echo "Tracking ID: $TEST_SESSION_ID"
echo ""

# Step 1: Send ERROR message
echo "Step 1: Sending ERROR message..."
echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) critical-service: ERROR $TEST_SESSION_ID Critical database connection failure - timeout exceeded" | nc localhost 1515
echo "✅ Message sent"

# Step 2: Wait and check Vector processing
echo ""
echo "Step 2: Checking Vector processing (wait 5s)..."
sleep 5
if docker compose logs vector | grep "$TEST_SESSION_ID" >/dev/null 2>&1; then
    echo "✅ Vector processed message"
else
    echo "❌ Vector did not process message"
fi

# Step 3: Check ClickHouse storage
echo ""
echo "Step 3: Checking ClickHouse storage..."
CLICKHOUSE_RESULT=$(docker exec aiops-clickhouse clickhouse-client --query="SELECT count() FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%'")
if [ "$CLICKHOUSE_RESULT" -gt 0 ]; then
    echo "✅ Message stored in ClickHouse"
else
    echo "❌ Message not found in ClickHouse"
fi

# Step 4: Check anomaly detection processing
echo ""
echo "Step 4: Checking anomaly detection processing (wait 10s)..."
sleep 10
if docker compose logs anomaly-detection | grep "$TEST_SESSION_ID" >/dev/null 2>&1; then
    echo "✅ Anomaly detection processed tracking ID"
    docker compose logs anomaly-detection | grep "$TEST_SESSION_ID" | tail -2
else
    echo "❌ Anomaly detection did not process tracking ID"
fi

# Step 5: Check for incident creation
echo ""
echo "Step 5: Checking incident creation (wait 10s)..."
sleep 10
if timeout 5s docker exec aiops-nats nats sub "incidents.created" --count=1 2>/dev/null | grep "$TEST_SESSION_ID" >/dev/null 2>&1; then
    echo "✅ Incident created with tracking ID"
else
    echo "❌ Incident not created or tracking ID not found"
fi

echo ""
echo "=== TC-002 VALIDATION COMPLETE ==="
echo "Review logs above for detailed results"
```

## Key Differences from Previous Version

1. **Vector Enhancement**: Now filters ERROR/WARNING logs and sends them to NATS for real-time processing
2. **Anomaly Service Enhancement**: Added log-based anomaly detection capability that processes individual messages
3. **Proper Flow**: ERROR logs now flow through both storage (ClickHouse) and real-time processing (NATS → Anomaly Detection)
4. **Tracking ID Preservation**: Tracking IDs are extracted and preserved throughout the pipeline
5. **Correct Expectations**: Test now expects to find tracking IDs in anomaly detection logs because the service actually processes them

This fix resolves the fundamental mismatch between what the test expected and what the system actually did.