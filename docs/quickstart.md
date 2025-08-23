# AIOps NAAS v0.1 MVP Quickstart Guide

This guide walks you through setting up the complete local development environment for the Cruise AIOps Platform using Docker Compose.

## Prerequisites

- Docker Engine 20.10+ with Docker Compose
- At least 8GB RAM available for containers
- 20GB free disk space
- Git

## Quick Start

1. **Clone and prepare the environment:**

```bash
git clone https://github.com/iLodeStar/AIOps-NAAS.git
cd AIOps-NAAS
cp .env.example .env
```

2. **Start all services:**

```bash
docker compose up -d
```

3. **Verify services are healthy:**

```bash
docker compose ps
```

All services should show "healthy" or "running" status. If any service is unhealthy, check logs:

```bash
docker compose logs [service-name]
```

## Service Overview

The stack includes the following services:

| Service | Port | Purpose | UI Access |
|---------|------|---------|-----------|
| **ClickHouse** | 8123/9000 | Log storage | http://localhost:8123/play |
| **VictoriaMetrics** | 8428 | Metrics storage | http://localhost:8428 |
| **Grafana** | 3000 | Visualization | http://localhost:3000 |
| **Qdrant** | 6333 | Vector database | http://localhost:6333/dashboard |
| **Ollama** | 11434 | LLM inference | CLI only |
| **NATS** | 4222/8222 | Message bus | http://localhost:8222 |
| **MailHog** | 8025/1025 | Email testing | http://localhost:8025 |
| **Node Exporter** | 9100 | System metrics | http://localhost:9100/metrics |
| **Vector** | - | Log processing | Logs to docker compose logs vector |

## Step-by-Step Verification

### 1. Access Grafana Dashboard

1. Open http://localhost:3000
2. Login with `admin/admin` (or values from your `.env`)
3. Navigate to **Dashboards → AIOps NAAS → Ship Overview**
4. You should see:
   - CPU and Memory usage from node-exporter
   - Log level distribution from ClickHouse
   - Log counts over time

**Screenshot placeholder**: *Grafana Ship Overview dashboard showing metrics and log data*

### 2. Verify ClickHouse Log Ingestion

1. Open http://localhost:8123/play
2. Run this query to see ingested logs:

```sql
SELECT timestamp, level, message, source, service 
FROM logs.raw 
ORDER BY timestamp DESC 
LIMIT 10;
```

3. You should see sample logs from the `sample-logs/` directory

### 3. Check VictoriaMetrics

1. Open http://localhost:8428
2. Try this query in the web UI:
   ```
   node_cpu_seconds_total
   ```
3. You should see CPU metrics being scraped from node-exporter

### 4. Install and Test Ollama Model

**Note**: Do not auto-pull large models. Follow these steps:

1. Install a lightweight model:
```bash
docker compose exec ollama ollama pull mistral
```

2. Test the model:
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Explain what AIOps means for cruise ships:",
  "stream": false
}'
```

3. You should get a JSON response with the model's explanation

### 5. Test Email Alerts with MailHog

1. Open http://localhost:8025 to see the MailHog interface
2. The SMTP server is available at `localhost:1025` for sending test emails
3. Try sending a test alert (see Alerting section below)

**Screenshot placeholder**: *MailHog interface showing received test emails*

### 6. Verify NATS JetStream

1. Check NATS monitoring: http://localhost:8222
2. View server info and connections
3. JetStream is enabled and ready for message streaming

## Working with Sample Logs

### Generate Live Logs

To generate continuous log entries for testing:

```bash
# Start the log generator
./sample-logs/generate-logs.sh
```

The generator creates JSON logs that Vector will automatically pick up and send to ClickHouse.

### View Log Processing

1. Watch Vector processing logs:
```bash
docker compose logs -f vector
```

2. Check ClickHouse for new entries:
```sql
SELECT count(*) as total_logs, 
       max(timestamp) as latest_log 
FROM logs.raw;
```

## Alerting Demo (VictoriaMetrics → MailHog)

### Create a High CPU Alert

1. Create `alerts/cpu-alert.yml`:

```yaml
groups:
  - name: system_alerts
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 2m
        labels:
          severity: warning
          service: monitoring
        annotations:
          summary: "High CPU usage detected on {{ $labels.instance }}"
          description: "CPU usage is above 80% for more than 2 minutes. Current usage: {{ $value }}%"
```

2. Configure vmalert (add to docker-compose.yml):

```yaml
  vmalert:
    image: victoriametrics/vmalert:latest
    command:
      - --rule=/etc/alerts/cpu-alert.yml
      - --datasource.url=http://victoria-metrics:8428
      - --notifier.url=http://mailhog:1025
      - --remoteWrite.url=http://victoria-metrics:8428
    volumes:
      - ./alerts:/etc/alerts:ro
    depends_on:
      - victoria-metrics
      - mailhog
```

3. Restart the stack:
```bash
docker compose up -d
```

4. Generate high CPU load to trigger the alert:
```bash
docker run --rm -it --name cpu-stress alpine/stress:latest --cpu 4 --timeout 300
```

5. Check MailHog at http://localhost:8025 for alert notifications

## Troubleshooting

### Common Issues

**ClickHouse connection refused:**
- Wait 30-60 seconds for ClickHouse to fully initialize
- Check: `docker compose logs clickhouse`

**Grafana shows no data:**
- Verify VictoriaMetrics is running: `curl http://localhost:8428/metrics`
- Check Grafana datasource configuration in UI
- Ensure node-exporter is being scraped: `curl http://localhost:9100/metrics`

**Vector not processing logs:**
- Check Vector configuration: `docker compose logs vector`
- Verify sample logs exist: `ls -la sample-logs/`
- Test ClickHouse connectivity from Vector container

**Ollama model download fails:**
- Ensure sufficient disk space (models can be 4GB+)
- Check: `docker compose logs ollama`
- Try smaller models first: `ollama pull phi`

### Resource Monitoring

Monitor resource usage:
```bash
docker stats
```

Expected resource usage with all services:
- **Memory**: 6-8GB total
- **CPU**: 10-20% on modern systems
- **Disk**: ~2GB for container images, ~1GB for data

### Log Locations

Container logs are available via:
```bash
docker compose logs [service]
```

Persistent data volumes:
- ClickHouse data: `clickhouse_data` volume
- Grafana dashboards: `grafana_data` volume
- VictoriaMetrics data: `vm_data` volume
- Qdrant data: `qdrant_data` volume
- Ollama models: `ollama_data` volume

## Next Steps

Once your local environment is running:

1. **Explore the data**: Query logs and metrics through Grafana
2. **Add custom dashboards**: Create visualizations specific to your needs
3. **Experiment with Ollama**: Try different models and prompts
4. **Set up real data sources**: Configure Vector to ingest actual log files
5. **Learn the architecture**: Read `docs/architecture.md` for system design
6. **Plan your deployment**: Review `docs/roadmap.md` for production considerations

## Stopping and Cleanup

**Stop services:**
```bash
docker compose down
```

**Remove all data (destructive):**
```bash
docker compose down -v
```

**Clean up images:**
```bash
docker compose down --rmi all
```

## Getting Help

- **Issues**: Open a GitHub issue with logs and error details
- **Documentation**: See `docs/` directory for architecture and roadmap
- **Community**: Discuss in repository discussions

---

**Note**: This is a development environment. For production deployment, review security settings, resource limits, and backup strategies outlined in the full documentation.