# Ubuntu Manual Validation Testing Guide

**Simple 5-Step Validation for AIOps NAAS Data Flow**

This guide provides clear, step-by-step instructions for test engineers to validate the complete data flow from Ubuntu syslogs to anomaly detection in layman terms.

## Prerequisites

- Ubuntu 18.04+ VM with Docker installed
- AIOps NAAS services running in Docker containers
- Basic command line knowledge
- `nc` (netcat) and `curl` tools installed

## Quick Setup Check

```bash
# Verify you're in the right directory
cd /path/to/AIOps-NAAS

# Check if Docker services are running
docker compose ps

# Expected: All services should show "Up" or "healthy" status
```

---

## Step 1: Capture Ubuntu Syslogs and Validate Vector Service

**Objective:** Generate syslog messages on your Ubuntu machine and verify Vector service receives them.

### 1.1 Check Vector Service Status

```bash
# Check if Vector is running
docker compose ps vector

# Expected Output: 
# NAME           STATUS              PORTS
# aiops-vector   Up (healthy)        0.0.0.0:1514->1514/udp, 0.0.0.0:8686->8686/tcp
```

### 1.2 Verify Vector is Listening for Syslogs

```bash
# Check Vector health endpoint
curl http://localhost:8686/health

# Expected Output: {"status":"ok","version":"..."}

# Check if UDP port 1514 is listening
sudo netstat -ulnp | grep 1514

# Expected Output: udp 0.0.0.0:1514 ... docker-proxy
```

### 1.3 Send Test Syslog Message

```bash
# Generate unique test message
TEST_ID="TEST-$(date +%Y%m%d-%H%M%S)-$$"
echo "Generated test ID: $TEST_ID"

# Send syslog message to Vector
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-app: VALIDATION $TEST_ID Normal system operation" | nc -u localhost 1514

# Wait for processing
sleep 5
```

### 1.4 Verify Vector Received the Message

```bash
# Check Vector metrics for received events
curl -s http://localhost:8686/metrics | grep "vector_events_in_total"

# Expected Output: vector_events_in_total{component_kind="source",...} [number > 0]

# Check Vector logs
docker compose logs vector --tail 20

# Expected: Should show log processing activity
```

**✅ Step 1 Success Criteria:**
- Vector service is healthy
- UDP port 1514 is listening
- Vector metrics show events received
- No errors in Vector logs

---

## Step 2: Validate Log Storage in ClickHouse

**Objective:** Verify that Vector successfully transforms and stores logs in ClickHouse database.

### 2.1 Check ClickHouse Service Status

```bash
# Check ClickHouse container
docker compose ps clickhouse

# Expected Output: aiops-clickhouse Up (healthy)

# Test ClickHouse connection
curl http://localhost:8123/ping

# Expected Output: Ok.
```

### 2.2 Verify Your Test Message in ClickHouse

```bash
# Search for your test message in the logs table
docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message, source FROM logs.raw WHERE message LIKE '%$TEST_ID%' ORDER BY timestamp DESC LIMIT 5"

# Expected Output: Your test message should appear with timestamp and parsed fields
```

### 2.3 Check Overall Log Volume

```bash
# Check total number of logs in ClickHouse
docker exec aiops-clickhouse clickhouse-client --query "SELECT count() FROM logs.raw"

# Expected Output: A number > 0 showing logs are being stored

# Check recent logs (last 10)
docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message FROM logs.raw ORDER BY timestamp DESC LIMIT 10"
```

**✅ Step 2 Success Criteria:**
- ClickHouse is accessible via HTTP
- Your test message appears in logs.raw table
- Log count is increasing over time
- No connection errors

---

## Step 3: Validate Data Transformation and Metrics Processing

**Objective:** Verify that logs are processed into metrics and stored in VictoriaMetrics.

### 3.1 Check VictoriaMetrics Service

```bash
# Check VictoriaMetrics status
docker compose ps victoria-metrics

# Test VictoriaMetrics health
curl http://localhost:8428/health

# Expected Output: {"status":"ok"}
```

### 3.2 Verify Metrics are Being Generated

```bash
# Check if any metrics are present
curl "http://localhost:8428/api/v1/query?query=up" | grep -o '"status":"success"'

# Expected Output: "status":"success"

# Check for log-derived metrics
curl "http://localhost:8428/api/v1/query?query=log_events_total"

# Expected Output: Should show metrics if log-to-metric transformation is working
```

### 3.3 Check Anomaly Detection Service Connection

```bash
# Verify anomaly detection service is running
docker compose ps anomaly-detection

# Check its health endpoint
curl http://localhost:8080/health

# Expected Output: Should show service status and connections to VictoriaMetrics
```

**✅ Step 3 Success Criteria:**
- VictoriaMetrics is healthy and accessible
- Metrics queries return successful responses  
- Anomaly detection service is connected
- Log data is being transformed to metrics

---

## Step 4: Validate Data Enrichment and Correlation

**Objective:** Verify that the system enriches data, performs correlation, and prepares for anomaly detection.

### 4.1 Generate Anomaly Test Message

```bash
# Create an anomaly pattern (high error rate)
ANOMALY_ID="ANOMALY-$(date +%Y%m%d-%H%M%S)-$$"
echo "Generated anomaly ID: $ANOMALY_ID"

# Send multiple error messages to simulate anomaly
for i in {1..5}; do
    echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) critical-app: ERROR $ANOMALY_ID Database connection failed - attempt $i" | nc -u localhost 1514
    sleep 2
done
```

### 4.2 Check NATS Message Bus

```bash
# Check NATS service status
docker compose ps nats

# Check NATS stats
curl -s "http://localhost:8222/varz" | grep -E "(in_msgs|out_msgs|connections)"

# Expected Output: Should show message counts > 0
```

### 4.3 Verify Benthos Correlation Processing

```bash
# Check Benthos correlation service
docker compose ps benthos

# Check Benthos health
curl http://localhost:4195/ping

# Expected Output: pong

# Check Benthos stats for processing activity
curl -s http://localhost:4195/stats | grep -E "(input|output|processor)"
```

### 4.4 Monitor for Correlation Activity

```bash
# Wait for correlation processing
sleep 10

# Check Benthos logs for correlation activity
docker compose logs benthos --tail 20 | grep -i -E "(correlation|incident|anomaly)"

# Expected Output: Should show correlation processing logs
```

**✅ Step 4 Success Criteria:**
- NATS shows message activity (in_msgs/out_msgs > 0)
- Benthos is processing messages
- Correlation logic is active
- No errors in correlation processing

---

## Step 5: Validate Anomaly Detection Logic

**Objective:** Verify the anomaly detection service identifies anomalies and creates incidents.

### 5.1 Check Anomaly Detection Processing

```bash
# Wait for anomaly processing
sleep 15

# Check anomaly detection service logs
docker compose logs anomaly-detection --tail 30

# Expected Output: Should show anomaly analysis and detection logic
```

### 5.2 Verify Anomaly Detection Results

```bash
# Check if incidents were created
curl -s http://localhost:8081/incidents | grep -o '"total":[0-9]*'

# Expected Output: Should show incident count

# Get latest incidents
curl -s http://localhost:8081/incidents | head -20

# Expected Output: Should show recent incidents including your anomaly
```

### 5.3 Validate Anomaly Logic Correctness

```bash
# Search for your specific anomaly in incidents
curl -s http://localhost:8081/incidents | grep "$ANOMALY_ID"

# Expected Output: Should find your anomaly ID in incident records

# Check incident details
curl -s "http://localhost:8081/incidents" | grep -A 10 -B 5 "$ANOMALY_ID"
```

### 5.4 Verify Alert Generation

```bash
# Check if alerting is working
docker compose ps alertmanager

# Check alert status
curl -s "http://localhost:9093/api/v1/alerts" | grep -o '"status":"firing"'

# Expected Output: May show firing alerts if anomalies triggered alerts
```

**✅ Step 5 Success Criteria:**
- Anomaly detection service processed your test anomaly
- Incidents were created containing your anomaly ID
- Alert logic is functioning
- End-to-end flow completed successfully

---

## Complete Validation Summary

If all 5 steps passed, your data flow is working correctly:

```
Ubuntu Syslog → Vector (Port 1514) → ClickHouse (logs.raw) → 
VictoriaMetrics (metrics) → Anomaly Detection → NATS → 
Benthos (correlation) → Incident API (incidents)
```

## Troubleshooting Guide

### Docker Services Not Running

```bash
# Check all services
docker compose ps

# Restart specific service
docker compose restart [service-name]

# View service logs
docker compose logs [service-name] --tail 50

# Restart all services
docker compose down && docker compose up -d
```

### Port Connection Issues

```bash
# Check what's listening on required ports
sudo netstat -tlnp | grep -E "(1514|8123|8428|8080|8081|4195|8222)"

# Check Docker port mapping
docker compose ps --format "table {{.Names}}\t{{.Ports}}"
```

### No Data Flowing

```bash
# Verify Vector is receiving data
curl http://localhost:8686/metrics | grep vector_events_in_total

# Check ClickHouse log count
docker exec aiops-clickhouse clickhouse-client --query "SELECT count() FROM logs.raw"

# Verify VictoriaMetrics has data
curl "http://localhost:8428/api/v1/query?query=up"
```

### Service Health Issues

```bash
# Run comprehensive health check
./scripts/troubleshoot_validation.sh

# Check resource usage
docker stats --no-stream

# Check Docker logs for errors
docker compose logs --tail 100 | grep -i error
```

### Cannot Find Your Test Messages

```bash
# List all recent logs in ClickHouse
docker exec aiops-clickhouse clickhouse-client --query "SELECT message FROM logs.raw ORDER BY timestamp DESC LIMIT 20"

# Check if Vector transformed your message
docker compose logs vector | grep "$TEST_ID"

# Verify your message format
echo "$TEST_ID"
```

## Quick Reference Commands

```bash
# Health check all services
curl http://localhost:8686/health  # Vector
curl http://localhost:8123/ping    # ClickHouse  
curl http://localhost:8428/health  # VictoriaMetrics
curl http://localhost:8080/health  # Anomaly Detection
curl http://localhost:8081/health  # Incident API
curl http://localhost:4195/ping    # Benthos

# Send test message
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test: MESSAGE_ID" | nc -u localhost 1514

# Check logs in ClickHouse
docker exec aiops-clickhouse clickhouse-client --query "SELECT * FROM logs.raw ORDER BY timestamp DESC LIMIT 5"

# Check incidents
curl -s http://localhost:8081/incidents
```

This guide provides a practical, step-by-step approach to validating your AIOps NAAS data flow from a Ubuntu VM perspective with all services running in Docker containers.