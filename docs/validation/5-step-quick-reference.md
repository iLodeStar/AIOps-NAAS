# Quick Reference: 5-Step Manual Validation

**For Test Engineers - Ubuntu VM with Docker Services**

## Pre-Check: Validate Docker is Running
```bash
cd /path/to/AIOps-NAAS
docker compose ps
# All services should show "Up" or "healthy"
```

---

## Step 1: Capture Ubuntu Syslogs → Vector Service

**Commands:**
```bash
# Check Vector status
curl http://localhost:8686/health
# Expected: {"status":"ok","version":"..."}

# Send test message
TEST_ID="TEST-$(date +%Y%m%d-%H%M%S)-$$"
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-app: VALIDATION $TEST_ID Normal system operation" | nc -u localhost 1514

# Verify received
curl -s http://localhost:8686/metrics | grep "vector_events_in_total"
```

**✅ Success:** Vector shows events received, no errors in logs

---

## Step 2: Find Log Storage Service → ClickHouse

**Commands:**
```bash
# Check ClickHouse status
curl http://localhost:8123/ping
# Expected: Ok.

# Find your test message
docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message FROM logs.raw WHERE message LIKE '%$TEST_ID%' ORDER BY timestamp DESC LIMIT 5"
```

**✅ Success:** Your test message appears in ClickHouse logs.raw table

---

## Step 3: Find Transformed Data → VictoriaMetrics

**Commands:**
```bash
# Check VictoriaMetrics
curl http://localhost:8428/health
# Expected: {"status":"ok"}

# Verify metrics exist
curl "http://localhost:8428/api/v1/query?query=up" | grep '"status":"success"'

# Check anomaly detection connection
curl http://localhost:8080/health
```

**✅ Success:** VictoriaMetrics has data, anomaly service connected

---

## Step 4: Validate Data Enrichment & Correlation

**Commands:**
```bash
# Create anomaly pattern
ANOMALY_ID="ANOMALY-$(date +%Y%m%d-%H%M%S)-$$"
for i in {1..5}; do
    echo "<11>$(date '+%b %d %H:%M:%S') $(hostname) critical-app: ERROR $ANOMALY_ID Database connection failed - attempt $i" | nc -u localhost 1514
    sleep 2
done

# Check NATS message bus
curl -s "http://localhost:8222/varz" | grep -E "(in_msgs|out_msgs)"

# Check Benthos correlation
curl http://localhost:4195/ping
# Expected: pong

# Wait and check correlation logs
sleep 10
docker compose logs benthos --tail 20 | grep -i -E "(correlation|incident|anomaly)"
```

**✅ Success:** NATS shows message activity, Benthos processing correlation

---

## Step 5: Validate Anomaly Detection Logic

**Commands:**
```bash
# Wait for processing
sleep 15

# Check anomaly detection logs
docker compose logs anomaly-detection --tail 30

# Check incidents created
curl -s http://localhost:8081/incidents | grep -o '"total":[0-9]*'

# Find your specific anomaly
curl -s http://localhost:8081/incidents | grep "$ANOMALY_ID"
```

**✅ Success:** Anomaly detected, incidents created with your ANOMALY_ID

---

## Troubleshooting Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Service down | `docker compose restart [service-name]` |
| No response | `docker compose ps` → check status |
| Port not listening | `sudo netstat -tlnp \| grep [port]` |
| No data flowing | Check logs: `docker compose logs [service] --tail 50` |
| Test message not found | Verify with: `echo $TEST_ID` |

## Health Check All Services
```bash
curl http://localhost:8686/health  # Vector
curl http://localhost:8123/ping    # ClickHouse  
curl http://localhost:8428/health  # VictoriaMetrics
curl http://localhost:8080/health  # Anomaly Detection
curl http://localhost:8081/health  # Incident API
curl http://localhost:4195/ping    # Benthos
```

## Expected Data Flow
```
Ubuntu VM → Vector (1514/udp) → ClickHouse (logs.raw) → 
VictoriaMetrics (metrics) → Anomaly Detection → 
NATS → Benthos (correlation) → Incident API
```

**Total validation time: ~5-10 minutes**