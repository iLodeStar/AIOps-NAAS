# AIOps NAAS Manual Testing - Quick Reference Card

## ⚠️ CRITICAL FIXES APPLIED

**Vector UDP Configuration Fixed**: Vector now properly accepts UDP syslog messages on port 1514.

**Before (BROKEN)**: Vector configured for TCP, test commands used UDP → Messages not received
**After (FIXED)**: Vector configured for UDP, matches test commands → Messages received and processed

## 🚀 Quick Start Commands

```bash
# 1. Start the platform
cd /path/to/AIOps-NAAS
docker compose up -d

# 2. Quick validation test (NEW)
./scripts/quick_validation_test.sh

# 3. Full guided validation
./scripts/manual_validation_test.sh

# 4. Check all services
docker compose ps
```

## 📋 5-Step Validation Checklist (UPDATED)

### ✅ Step 1: Syslog Message Sending (CORRECTED)
- **Service**: Vector UDP syslog receiver (port 1514)
- **CORRECTED Command**: `echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test: MESSAGE" | nc -u localhost 1514`
- **Validation**: `curl -s http://localhost:8686/metrics | grep vector_events_in_total`
- **Expected**: Should show incremented event counter
- **Screenshot**: Vector metrics showing message reception

### ✅ Step 2: Vector Log Processing (WORKING)
- **Service**: Vector log processor and transformer
- **Health Check**: `curl http://localhost:8686/health` ← Should return JSON status
- **Debug Check**: `curl -s http://localhost:8686/metrics | grep vector_events` ← Should show metrics
- **Validation**: Vector processing logs and transforming to ClickHouse format
- **Screenshot**: Vector logs/metrics showing processing activity

### ✅ Step 3: ClickHouse Log Storage (WORKING)
- **Service**: ClickHouse database (logs.raw table)
- **Health Check**: `curl http://localhost:8123/ping` ← Should return "Ok."
- **UI Access**: http://localhost:8123/play (ClickHouse Web UI)
- **Query Test**: `SELECT * FROM logs.raw ORDER BY timestamp DESC LIMIT 5`
- **Screenshot**: ClickHouse Play UI showing stored log messages

### ✅ Step 4: NATS Message Bus & Benthos Correlation
- **Services**: NATS (port 4222) + Benthos (port 4195)
- **NATS Health**: `curl http://localhost:8222/healthz` ← Should return {"status":"ok"}
- **Benthos Health**: `curl http://localhost:4195/ping` ← Should return "pong"
- **UI Access**: http://localhost:8222 (NATS monitoring interface)
- **Screenshot**: NATS monitoring showing message flow + Benthos stats

### ✅ Step 5: Anomaly Detection & Incident Creation  
- **Service**: ML-based anomaly detection service
- **Health Check**: `curl http://localhost:8080/health`
- **Integration Test**: Send anomaly message via UDP syslog
- **Validation**: Check NATS topics for anomaly events
- **Screenshot**: Anomaly detection response + incident creation

## 🔧 Essential Endpoints (VALIDATED)

| Service | Port | Health Check | Web UI | Status |
|---------|------|--------------|---------|--------|
| Vector | 8686 | `/health` | `/` | ✅ UDP Fixed |
| ClickHouse | 8123 | `/ping` | `/play` | ✅ Working |
| VictoriaMetrics | 8428 | `/health` | `/vmui` | ✅ Working |
| Grafana | 3000 | `/api/health` | `/login` | ✅ Working |
| NATS | 8222 | `/healthz` | `/` | ✅ Working |
| Benthos | 4195 | `/ping` | Stats API | ✅ Working |
| Anomaly Detection | 8080 | `/health` | API only | ✅ Working |
| Incident API | 8081 | `/health` | API only | ✅ Working |

## 💡 Working Command Examples (TESTED)

### Message Tracking Commands
```bash
# Generate tracking ID
TRACKING_ID="E2E-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

# Send test message (CORRECTED - uses UDP)
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test: $TRACKING_ID" | nc -u localhost 1514

# Check Vector received it
curl -s http://localhost:8686/metrics | grep vector_events_in_total

# Find in ClickHouse
docker exec aiops-clickhouse clickhouse-client --query "SELECT * FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'"
```

### Health Check Commands (ALL WORKING)
```bash
# Vector health (should return JSON)
curl -s http://localhost:8686/health

# ClickHouse health (should return "Ok.")
curl -s http://localhost:8123/ping

# NATS health (should return JSON with status ok)
curl -s http://localhost:8222/healthz

# Benthos health (should return "pong")
curl -s http://localhost:4195/ping
```

## 🐛 Quick Troubleshooting (UPDATED)

### ❌ Issue: Vector Not Receiving Messages
**FIXED**: Vector now configured for UDP. Verify with:
```bash
# Check Vector UDP configuration
docker exec aiops-vector cat /etc/vector/vector.toml | grep -A 3 syslog
# Should show: mode = "udp"

# If still TCP, restart after configuration change
docker compose restart vector
```

### ❌ Issue: Empty Vector Metrics
**FIXED**: Debug sinks enabled. Verify with:
```bash
# Should show multiple metric lines
curl -s http://localhost:8686/metrics | wc -l
# Expected: >100 lines

# Should show event counters  
curl -s http://localhost:8686/metrics | grep vector_events
# Expected: Multiple vector_events_* lines
```

### Services Not Starting
```bash
# Check resource usage
docker stats --no-stream

# Restart specific service
docker compose restart [service-name]

# View service logs
docker compose logs [service-name] --tail 50

# Clean restart all services
docker compose down && docker compose up -d
```

### No Data Flow After Fixes
```bash
# Run the quick validation test
./scripts/quick_validation_test.sh

# Manual verification steps
curl http://localhost:8123/ping         # ClickHouse: "Ok."
curl http://localhost:8686/health       # Vector: JSON response  
curl http://localhost:8222/healthz      # NATS: {"status":"ok"}
curl http://localhost:4195/ping         # Benthos: "pong"

# Test message sending (UDP)
echo "test" | nc -u localhost 1514
sleep 5
curl -s http://localhost:8686/metrics | grep vector_events
```

## 🎯 Success Indicators

**✅ Working System Shows:**
- Vector metrics increment with each test message
- ClickHouse queries return your tracking IDs  
- NATS shows message activity in monitoring UI
- Benthos logs show correlation processing
- All health checks return expected responses

**❌ Broken System Shows:**
- Vector metrics stay at 0 or don't exist
- ClickHouse queries return empty results
- Health checks return errors or empty responses
- Service containers keep restarting
./scripts/simulate_node_metrics.sh
```

### No Anomalies Detected
```bash
# Check metrics availability
curl "http://localhost:8428/api/v1/query?query=up"

# Generate test anomalies
python3 scripts/publish_test_anomalies.py

# Check incident creation
curl http://localhost:8081/incidents
```

## 📸 Screenshot Requirements

1. **Vector Logs**: Show syslog processing activity
2. **Vector UI**: Service interface (if available)
3. **ClickHouse Play**: Database UI with sample queries
4. **NATS Monitoring**: Message bus activity dashboard
5. **Anomaly Detection**: Service health and processing logs
6. **Grafana Dashboard**: Main visualization interface

## 🔄 Data Flow Validation

```
Ubuntu Syslogs → Vector → ClickHouse (logs)
                    ↓
System Metrics → VictoriaMetrics → Anomaly Detection
                                        ↓
NATS Message Bus ← Benthos Correlation ← Anomaly Events
      ↓
Incident API → Grafana Dashboards
```

## 📞 Emergency Commands

```bash
# Stop everything
docker compose down

# Emergency cleanup
docker system prune -f
docker volume prune -f

# Full restart with logs
docker compose up -d && docker compose logs -f

# Check system resources
free -h && df -h && docker system df
```

## 📁 Important Files

- **Main Guide**: `docs/validation/manual-testing-guide.md`
- **Automated Script**: `scripts/manual_validation_test.sh`
- **Docker Config**: `docker-compose.yml`
- **Environment**: `.env` (copy from `.env.example`)

## 🎯 Expected Results

- **All services**: Healthy status in `docker compose ps`
- **Syslog flow**: Messages visible in Vector logs
- **Log storage**: Data queryable in ClickHouse
- **Correlation**: Related events combined in incidents
- **Anomaly detection**: Incidents generated from high metrics
- **Visualization**: Grafana dashboards show system data

---
*For detailed instructions, see `docs/validation/manual-testing-guide.md`*