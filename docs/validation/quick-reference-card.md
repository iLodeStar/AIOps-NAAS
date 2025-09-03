# AIOps NAAS Manual Testing - Quick Reference Card

## 🚀 Quick Start Commands

```bash
# 1. Start the platform
cd /path/to/AIOps-NAAS
docker compose up -d

# 2. Run guided validation
./scripts/manual_validation_test.sh

# 3. Check all services
docker compose ps
```

## 📋 5-Step Validation Checklist

### ✅ Step 1: Syslog Capture
- **Service**: System rsyslog → Vector (port 514)
- **Test Command**: `logger "TEST: validation message"`
- **Validation**: `docker compose logs vector --tail 20`
- **Screenshot**: Vector logs processing syslogs

### ✅ Step 2: Log Reading Service  
- **Service**: Vector log processor
- **Health Check**: `curl http://localhost:8686/health` (port may vary)
- **Validation**: Vector processing logs and metrics
- **Screenshot**: Vector UI/logs interface

### ✅ Step 3: Log Storage
- **Service**: ClickHouse database
- **Health Check**: `curl http://localhost:8123/ping`
- **UI Access**: http://localhost:8123/play
- **Screenshot**: ClickHouse Play UI with log queries

### ✅ Step 4: Data Correlation
- **Services**: NATS (message bus) + Benthos (correlation)
- **Health Check**: `curl http://localhost:8222/varz`
- **UI Access**: http://localhost:8222 (NATS monitoring)
- **Screenshot**: NATS monitoring + correlation logs

### ✅ Step 5: Anomaly Detection
- **Service**: ML-based anomaly detection
- **Health Check**: `curl http://localhost:8080/health`
- **Test**: `./scripts/validate_pipeline.sh`
- **Screenshot**: Anomaly detection service response

## 🔧 Essential Endpoints

| Service | Port | Health Check | Web UI |
|---------|------|--------------|---------|
| ClickHouse | 8123 | `/ping` | `/play` |
| VictoriaMetrics | 8428 | `/health` | `/vmui` |
| Grafana | 3000 | `/api/health` | `/login` |
| NATS | 8222 | `/healthz` | `/` |
| Anomaly Detection | 8080 | `/health` | API only |
| Incident API | 8081 | `/health` | API only |

## 🐛 Quick Troubleshooting

### Services Not Starting
```bash
# Check resource usage
docker stats --no-stream

# Restart specific service
docker compose restart [service-name]

# View service logs
docker compose logs [service-name] --tail 50

# Clean restart
docker compose down && docker compose up -d
```

### No Data Flow
```bash
# Check all services health
curl http://localhost:8123/ping  # ClickHouse
curl http://localhost:8428/health # VictoriaMetrics  
curl http://localhost:8080/health # Anomaly Detection

# Test data generation
logger "TEST: troubleshooting message"
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