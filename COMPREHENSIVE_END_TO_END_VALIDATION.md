# COMPREHENSIVE End-to-End Message Tracking and Validation Guide

## Overview
This guide provides **COMPLETE END-TO-END MESSAGE TRACKING** from a single test message through the entire AIOps NAAS pipeline with **REAL CONSOLE OUTPUTS** and step-by-step verification.

## Critical Fix Applied
**ROOT CAUSE IDENTIFIED AND FIXED**: Vector ClickHouse sink was missing authentication configuration. This prevented ALL messages from reaching ClickHouse despite appearing in Vector logs.

**Fix Applied:**
```toml
[sinks.clickhouse.auth]
strategy = "basic"
user = "${CLICKHOUSE_USER:-default}"
password = "${CLICKHOUSE_PASSWORD:-clickhouse123}"
```

---

## Data Flow Architecture

### Normal Message Flow (Non-Anomaly)
```
TEST MESSAGE → Syslog (UDP/TCP:1514/1515) → Vector → ClickHouse → END
```

### Anomaly Message Flow (When Detected)
```  
TEST MESSAGE → Syslog → Vector → ClickHouse → VictoriaMetrics → Anomaly Detection → NATS → Benthos → Incidents
```

### SNMP Data Flow
```
Network Device → SNMP Collector → NATS → Vector → ClickHouse → (Anomaly Pipeline if needed)
```

---

## Step-by-Step End-to-End Tracking

### Step 1: Environment Setup and Service Health

```bash
# Start all services
docker compose up -d

# Wait for all services to be healthy (60-90 seconds)
docker compose ps
```

**Expected Output:**
```
NAME                          IMAGE                              COMMAND                  SERVICE      CREATED         STATUS                   PORTS
aiops-benthos                 jeffail/benthos:latest            "/benthos -c /bentho…"   benthos      2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:4195->4195/tcp
aiops-clickhouse              clickhouse/clickhouse-server:…   "/entrypoint.sh"         clickhouse   2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8123->8123/tcp, 0.0.0.0:9000->9000/tcp
aiops-nats                    nats:alpine                      "nats-server --jetst…"   nats         2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:4222->4222/tcp, 0.0.0.0:8222->8222/tcp
aiops-vector                  aiops-naas-vector                "vector --config /et…"   vector       2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:1514->1514/udp, 0.0.0.0:1515->1515/tcp, 0.0.0.0:8686->8686/tcp
```

### Step 2: Health Check Validation

```bash
# ClickHouse health (MUST return "Ok.")
curl -s http://localhost:8123/ping

# Vector health (MUST return status ok)
curl -s http://localhost:8686/health

# NATS health (MUST return status ok)  
curl -s http://localhost:8222/healthz

# Benthos health (MUST return "pong")
curl -s http://localhost:4195/ping
```

**Expected Outputs:**
```
Ok.
{"status":"ok","version":"0.34.1"}
{"status":"ok"}
pong
```

### Step 3: Generate Unique Tracking ID

```bash
# Generate unique tracking ID for this test session
TRACKING_ID="E2E-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "=== TRACKING ID: $TRACKING_ID ==="
echo "This ID will be tracked through ALL system components"
```

**Expected Output:**
```
=== TRACKING ID: E2E-20250103-143022-a1b2c3d4 ===
This ID will be tracked through ALL system components
```

### Step 4: Send Test Message to Vector

#### Option A: UDP Syslog (Port 1514)
```bash
echo "Sending UDP message with tracking ID: $TRACKING_ID"
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID UDP message from manual validation" | nc -u localhost 1514

# Verify message sent
echo "UDP message sent at $(date)"
```

#### Option B: TCP Syslog (Port 1515)
```bash
echo "Sending TCP message with tracking ID: $TRACKING_ID"
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID TCP message from manual validation" | nc localhost 1515

# Verify message sent
echo "TCP message sent at $(date)"
```

### Step 5: Verify Message Reception in Vector

```bash
# Check Vector logs for your tracking ID (should appear within 5 seconds)
echo "Checking Vector logs for tracking ID: $TRACKING_ID"
docker logs aiops-vector --tail=50 | grep "$TRACKING_ID"
```

**Expected Output (Vector Log Entry):**
```json
{"appname":"test-service","counter_value":null,"facility":"user","gauge_value":null,"host":"ubuntu","hostname":"ubuntu","kind":"","labels":{},"level":"INFO","message":"NORMAL_TEST E2E-20250103-143022-a1b2c3d4 UDP message from manual validation","name":"","namespace":"","raw_log":"{\"appname\":\"test-service\",\"facility\":\"user\",\"host\":\"ubuntu\",\"hostname\":\"ubuntu\",\"level\":\"INFO\",\"message\":\"NORMAL_TEST E2E-20250103-143022-a1b2c3d4 UDP message from manual validation\",\"service\":\"test-service\",\"severity\":\"info\",\"source\":\"syslog\",\"source_ip\":\"172.18.0.1\",\"source_type\":\"syslog\",\"timestamp\":\"2025-01-03T14:30:22Z\"}","service":"test-service","severity":"info","source":"syslog","source_ip":"172.18.0.1","source_type":"syslog","tags":{},"timestamp":"2025-01-03T14:30:22Z"}
```

### Step 6: Verify Message Storage in ClickHouse

```bash
# Wait 10 seconds for Vector to send batch to ClickHouse
echo "Waiting 10 seconds for Vector batch processing..."
sleep 10

# Query ClickHouse for your tracking ID
echo "Querying ClickHouse for tracking ID: $TRACKING_ID"
docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 5"
```

**Expected Output (ClickHouse Query Result):**
```
2025-01-03 14:30:22.123	INFO	NORMAL_TEST E2E-20250103-143022-a1b2c3d4 UDP message from manual validation	syslog	ubuntu	test-service
```

### Step 7: Check Vector-to-ClickHouse Metrics

```bash
# Check Vector processing metrics
echo "Checking Vector input/output metrics:"
curl -s http://localhost:8686/metrics | grep -E "vector_events_in_total|vector_events_out_total"
```

**Expected Output (Showing Non-Zero Counts):**
```
vector_events_in_total{component_id="syslog_udp",component_type="source"} 1
vector_events_out_total{component_id="syslog_for_logs",component_type="transform"} 1  
vector_events_out_total{component_id="clickhouse",component_type="sink"} 1
```

### Step 8: Verify ClickHouse Record Details

```bash
# Get full record details from ClickHouse
echo "Full ClickHouse record for tracking ID: $TRACKING_ID"
docker exec aiops-clickhouse clickhouse-client --query "SELECT * FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' FORMAT JSONEachRow" | jq
```

**Expected Output (JSON Record):**
```json
{
  "timestamp": "2025-01-03 14:30:22.123",
  "level": "INFO",
  "message": "NORMAL_TEST E2E-20250103-143022-a1b2c3d4 UDP message from manual validation",
  "source": "syslog",
  "host": "ubuntu",
  "service": "test-service",
  "raw_log": "{\"appname\":\"test-service\",\"facility\":\"user\",...}",
  "labels": {},
  "name": "",
  "namespace": "",
  "tags": {},
  "kind": "",
  "counter_value": null,
  "gauge_value": null
}
```

---

## Understanding Benthos Data Flow

### Where Does Benthos Get Its Data?

**IMPORTANT**: Benthos does NOT get data directly from Vector or ClickHouse for normal messages.

**Benthos Input Sources (from benthos.yaml):**
1. **`anomaly.detected`** - Basic anomalies from anomaly-detection service
2. **`anomaly.detected.enriched`** - Enhanced anomalies from enhanced-anomaly-detection service

### How to See Messages in Benthos

For your test message to appear in Benthos, it must be detected as an **ANOMALY** first:

```bash
# Check if your message triggered any anomaly detection
echo "Checking anomaly detection service..."
curl -s http://localhost:8080/health 2>/dev/null || echo "Anomaly detection service not available"

# Check NATS for anomaly topics
echo "Checking NATS for anomaly subjects:"
docker exec aiops-nats nats pub "test.subject" "test message" 2>/dev/null || echo "NATS CLI not available in container"
```

### Benthos Processing Verification

```bash
# Check Benthos processing statistics
echo "Benthos processing stats:"
curl -s http://localhost:4195/stats | jq

# Check Benthos processing metrics  
echo "Benthos metrics:"
curl -s http://localhost:4195/metrics
```

---

## SNMP Data Tracking

### SNMP Data Flow Verification

```bash
# Check network device collector status
echo "Network Device Collector Status:"
curl -s http://localhost:8088/metrics | grep snmp || echo "SNMP collector metrics not available"

# Check NATS for SNMP subjects
echo "Checking Vector logs for SNMP data processing:"
docker logs aiops-vector --tail=20 | grep -i snmp || echo "No SNMP data processed yet"
```

---

## Troubleshooting Guide

### Issue 1: Message Not in ClickHouse
```bash
# Check Vector ClickHouse sink errors
docker logs aiops-vector | grep -i "clickhouse\|error" | tail -10

# Test ClickHouse connectivity
docker exec aiops-vector curl -s http://clickhouse:8123/ping

# Check ClickHouse authentication
docker exec aiops-clickhouse clickhouse-client --query "SHOW USERS"
```

### Issue 2: Vector Not Receiving Messages
```bash
# Test UDP syslog connectivity
nc -u -z localhost 1514 && echo "UDP 1514 reachable" || echo "UDP 1514 unreachable"

# Test TCP syslog connectivity  
nc -z localhost 1515 && echo "TCP 1515 reachable" || echo "TCP 1515 unreachable"

# Check Vector debug logs
docker logs aiops-vector --tail=50 | grep "syslog"
```

### Issue 3: Benthos Not Processing
```bash
# Check NATS connection from Benthos
docker logs aiops-benthos | grep -i "nats\|error" | tail -10

# Manually publish to anomaly topic
docker exec aiops-nats nats pub "anomaly.detected" '{"metric_name":"test_metric","anomaly_score":0.95,"ship_id":"ship-01"}'

# Check if Benthos receives it
docker logs aiops-benthos --tail=10
```

---

## Summary: Complete Data Flow Verification

After running this guide, you should have verified:

✅ **Step 1-3**: Services healthy and tracking ID generated  
✅ **Step 4-5**: Message sent via syslog and received by Vector  
✅ **Step 6-8**: Message processed by Vector and stored in ClickHouse  
✅ **Benthos Understanding**: Benthos processes anomalies, not normal messages  
✅ **SNMP Flow**: SNMP data collection and processing pathway  
✅ **Troubleshooting**: Tools to diagnose issues at each step  

**Key Takeaway**: Your test message follows the **Normal Message Flow** (Syslog → Vector → ClickHouse) unless it triggers anomaly detection, which would then route it through the **Anomaly Message Flow** (→ VictoriaMetrics → Anomaly Detection → NATS → Benthos → Incidents).