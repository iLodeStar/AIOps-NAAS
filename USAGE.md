# AIOps NAAS v0.1 MVP - Usage Guide

## Quick Start

Start the complete observability stack:

```bash
docker compose up -d
```

Wait 30-60 seconds for all services to initialize, then access:

## Service Access

| Service | URL | Purpose | Credentials |
|---------|-----|---------|-------------|
| **Grafana Dashboard** | http://localhost:3000 | Ship health visualization | admin/admin |
| **MailHog** | http://localhost:8025 | Email testing interface | None |
| **ClickHouse** | http://localhost:8123/play | Log database queries | default/clickhouse123 |
| **VictoriaMetrics** | http://localhost:8428 | Metrics database | None |
| **Qdrant** | http://localhost:6333/dashboard | Vector database UI | None |
| **NATS** | http://localhost:8222 | Message bus monitoring | None |
| **VMAlert** | http://localhost:8880 | Alert rules status | None |

## Key Features Demonstrated

### 1. Ship Health Dashboard
- Navigate to Grafana → Dashboards → AIOps NAAS → Ship Overview
- View real-time CPU, Memory, Load, and Disk metrics
- Auto-refreshing every 30 seconds

### 2. Email Alerting System
- Alerts automatically fire when CPU > 80% for 2+ minutes
- Emails delivered to MailHog inbox with full alert details
- Test by generating CPU load: `docker run --rm -d --name stress busybox:latest sh -c 'while true; do :; done'`

### 3. Log Processing
- Vector processes logs from `sample-logs/app.log`
- Add new log entries to see them processed in real-time
- Check Vector output: `docker compose logs vector`

### 4. Metrics Collection
- Node-exporter provides system metrics
- VictoriaMetrics stores time-series data
- Query metrics directly at http://localhost:8428

## Testing the System

### Generate Alert
```bash
# Create CPU stress to trigger alert
docker run --rm -d --name stress busybox:latest sh -c 'while true; do :; done'

# Wait 2-3 minutes, then check MailHog for alert email
# Clean up when done
docker stop stress
```

### Add Sample Logs
```bash
# Append new log entry
echo '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.000Z)'","level":"INFO","message":"Test log entry","service":"test","host":"ship-01"}' >> sample-logs/app.log

# Check Vector processing
docker compose logs vector --tail=5
```

### Query ClickHouse
```sql
-- In ClickHouse web interface (http://localhost:8123/play)
SELECT timestamp, level, message, service 
FROM logs.raw 
ORDER BY timestamp DESC 
LIMIT 10;
```

## Troubleshooting

### Services Not Starting
```bash
# Check service status
docker compose ps

# View logs for specific service
docker compose logs [service-name]

# Restart specific service
docker compose restart [service-name]
```

### No Data in Grafana
- Wait 1-2 minutes for metrics collection to begin
- Verify VictoriaMetrics is receiving data: http://localhost:8428
- Check that node-exporter is running: http://localhost:9100/metrics

### Alerts Not Firing
- Check VMAlert rules: http://localhost:8880/api/v1/rules
- View alert status: http://localhost:8880/api/v1/alerts
- Verify Alertmanager config: http://localhost:9093

## Architecture

This v0.1 MVP implements:

- **Log Pipeline**: Vector → ClickHouse (logs stored, console output working)
- **Metrics Pipeline**: Node-exporter → VMAgent → VictoriaMetrics → Grafana
- **Alerting Pipeline**: VMAlert → Alertmanager → MailHog
- **Vector Database**: Qdrant (ready for RAG/LLM integration)
- **LLM Service**: Ollama (ready for model deployment)
- **Message Bus**: NATS JetStream (ready for event streaming)

## Next Steps

The system is ready for:
1. Production LLM model deployment
2. Advanced log correlation rules  
3. Custom dashboard creation
4. Integration with real ship systems
5. k3s/Argo CD deployment (future milestone)

## Stopping the Stack

```bash
# Stop all services
docker compose down

# Remove all data (destructive)
docker compose down -v
```