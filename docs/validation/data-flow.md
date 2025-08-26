# AIOps NAAS Pipeline Validation Guide

This document provides comprehensive guidance for validating the end-to-end anomaly detection pipeline, troubleshooting common issues, and understanding the data flow.

## Overview

The AIOps NAAS anomaly detection pipeline consists of several components that work together to detect anomalies, correlate events, and generate incidents:

```
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│ Node        │    │ VictoriaMetrics │    │ Anomaly      │    │ NATS        │
│ Exporter    ├───►│ (Metrics Store) ├───►│ Detection    ├───►│ JetStream   │
│             │    │                 │    │ Service      │    │             │
└─────────────┘    └─────────────────┘    └──────────────┘    └─────────────┘
                                                                      │
┌─────────────┐    ┌─────────────────┐    ┌──────────────┐           │
│ ClickHouse  │◄───│ Incident API    │◄───│ Benthos      │◄──────────┘
│ (Storage)   │    │ (REST)          │    │ (Correlation)│
└─────────────┘    └─────────────────┘    └──────────────┘
```

## Validation Strategies

### Strategy 1: Full Pipeline Validation (Recommended)

Tests the complete metrics → anomaly → correlation → incident flow.

**Requirements:**
- All services running (docker compose up -d)
- Node-exporter working OR metrics simulation

**Command:**
```bash
export CH_USER=admin CH_PASS=admin
./scripts/validate_pipeline.sh
```

**What it does:**
1. Sends baseline node metrics to VictoriaMetrics
2. Sends anomaly spikes (high CPU/memory usage)
3. Waits for anomaly detection service to process
4. Verifies incidents are created via Incident API
5. Optionally checks ClickHouse storage

### Strategy 2: NATS Bypass Validation

Tests correlation → incident flow when metrics/anomaly detection is problematic.

**Requirements:**
- NATS, Benthos, Incident API running
- Python environment with nats-py

**Command:**
```bash
python3 scripts/publish_test_anomalies.py
```

**What it does:**
1. Publishes high-confidence anomalies directly to NATS
2. Bypasses VictoriaMetrics and anomaly detection
3. Tests Benthos correlation and Incident API persistence

### Strategy 3: Node Metrics Simulation

Provides node_exporter-compatible metrics when node-exporter fails.

**Requirements:**
- VictoriaMetrics running

**Command:**
```bash
./scripts/simulate_node_metrics.sh --duration 300
```

**What it does:**
1. Generates realistic node_cpu_seconds_total metrics
2. Generates node_memory_* metrics  
3. Provides data for anomaly detector PromQL queries

### Strategy 4: Basic Smoke Test

Quick connectivity and API response check.

**Command:**
```bash
./scripts/smoke_endpoints.sh
```

## Data Flow Details

### Metrics Path (Normal Operation)

1. **Node Exporter** (`node-exporter:9100`)
   - Collects system metrics from host
   - Exposes Prometheus-format metrics

2. **VictoriaMetrics Agent** (`vmagent`)
   - Scrapes metrics from node-exporter
   - Sends to VictoriaMetrics storage

3. **VictoriaMetrics** (`victoria-metrics:8428`)
   - Stores time-series metrics
   - Provides PromQL query API

4. **Anomaly Detection Service** (`anomaly-detection:8082`)
   - Queries VictoriaMetrics every 60s with:
     - CPU: `100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
     - Memory: `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`
   - Applies anomaly detection algorithms (Z-score, EWMA, MAD)
   - Publishes anomalies to NATS topic `anomaly.detected`

5. **NATS JetStream** (`nats:4222`)
   - Receives anomaly events
   - Provides durable message streaming

6. **Benthos** (`benthos:4195`)
   - Consumes from NATS `anomaly.detected`
   - Performs event correlation and enrichment
   - Converts anomalies to incidents
   - Sends incidents to Incident API

7. **Incident API** (`incident-api:8081`)
   - Receives incident events via HTTP
   - Stores incidents in ClickHouse
   - Provides REST API for incident retrieval

8. **ClickHouse** (`clickhouse:8123`)
   - Persistent storage for incidents
   - Supports complex analytical queries

### Bypass Path (When Node Metrics Unavailable)

Direct anomaly publishing skips steps 1-4 and injects events directly into step 5.

## Troubleshooting Guide

### No Incidents Generated

**Symptoms:**
- `validate_pipeline.sh` reports no incidents
- Incident API returns empty array `[]`

**Diagnosis:**
```bash
# Check each component in the pipeline
docker compose logs anomaly-detection --tail 50
docker compose logs nats --tail 20  
docker compose logs benthos --tail 50
docker compose logs incident-api --tail 50
```

**Common Causes:**

1. **Node-exporter not running/no metrics**
   ```bash
   curl http://localhost:9100/metrics | grep node_cpu_seconds_total
   ```
   *Solution:* Use `./scripts/simulate_node_metrics.sh`

2. **Anomaly detection service not querying metrics**
   ```bash
   # Check if VictoriaMetrics has node metrics
   curl "http://localhost:8428/api/v1/query?query=node_cpu_seconds_total" | jq
   ```
   *Solution:* Check vmagent scraping config, restart vmagent

3. **Anomalies not published to NATS**
   ```bash
   # Check NATS subscriptions
   curl http://localhost:8222/subsz | jq
   ```
   *Solution:* Verify anomaly detection NATS connection

4. **Benthos not processing events**
   ```bash
   # Check Benthos metrics
   curl http://localhost:4195/stats | jq
   ```
   *Solution:* Check benthos.yaml configuration

5. **Incident API not storing incidents**
   ```bash
   curl http://localhost:8081/health
   ```
   *Solution:* Check ClickHouse connectivity

### Node-Exporter Mount Issues

**Symptoms:**
```
Error: path / is mounted on / but it is not a shared or slave mount
```

**Cause:**
Host filesystem uses private mount propagation, incompatible with `rslave`.

**Solution:**
The `docker-compose.override.yml` in this repo fixes this by using `rprivate`:

```yaml
services:
  node-exporter:
    volumes:
      - '/:/host:ro,rprivate'
    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
```

**Alternative:**
Use metric simulation instead:
```bash
./scripts/simulate_node_metrics.sh --duration 600
```

### ClickHouse Access Issues

**Symptoms:**
- Cannot verify incidents in ClickHouse
- HTTP auth errors

**Diagnosis:**
```bash
# Test ClickHouse HTTP access
curl -u admin:admin http://localhost:8123/ping
```

**Solutions:**

1. **Set credentials in environment:**
   ```bash
   export CH_USER=admin CH_PASS=admin
   ```

2. **Check if ClickHouse uses HTTP or native TCP:**
   ```bash
   docker compose logs clickhouse | grep -i "http\|tcp"
   ```

3. **Query via docker exec (bypass HTTP):**
   ```bash
   docker compose exec clickhouse clickhouse-client -q "SELECT count() FROM incidents"
   ```

### Service Dependencies

**Start services in order for troubleshooting:**

1. **Storage layer:**
   ```bash
   docker compose up -d clickhouse victoria-metrics nats
   ```

2. **Ingestion layer:**
   ```bash
   docker compose up -d vmagent node-exporter
   # OR use: ./scripts/simulate_node_metrics.sh
   ```

3. **Processing layer:**
   ```bash
   docker compose up -d anomaly-detection benthos
   ```

4. **API layer:**
   ```bash
   docker compose up -d incident-api
   ```

## Validation Scripts Reference

### validate_pipeline.sh

**Purpose:** Complete end-to-end validation
**Duration:** ~60 seconds
**Requirements:** All services running

**Environment Variables:**
- `VM_URL` - VictoriaMetrics URL (default: http://localhost:8428)
- `INCIDENT_API_URL` - Incident API URL (default: http://localhost:8081)
- `CH_USER` / `CH_PASS` - ClickHouse credentials
- `WAIT_TIME` - Processing wait time (default: 30s)

### validate_pipeline.py

**Purpose:** Python version of full validation
**Duration:** ~60 seconds  
**Requirements:** All services running, Python requests library

**Usage:**
```bash
pip install requests
python3 scripts/validate_pipeline.py
```

### publish_test_anomalies.py

**Purpose:** Direct NATS anomaly publishing
**Duration:** ~15 seconds
**Requirements:** NATS running, Python nats-py library

**Usage:**
```bash
pip install nats-py
python3 scripts/publish_test_anomalies.py
```

**Environment Variables:**
- `NATS_URL` - NATS server URL (default: nats://localhost:4222)
- `COUNT` - Number of anomalies (default: 3)
- `INTERVAL` - Seconds between anomalies (default: 2)

### simulate_node_metrics.sh

**Purpose:** Generate node_exporter-compatible metrics
**Duration:** Configurable (default: 300s)
**Requirements:** VictoriaMetrics running

**Options:**
```bash
./scripts/simulate_node_metrics.sh --duration 600 --interval 30 --cpu-usage 75 --memory-usage 85
```

### smoke_endpoints.sh

**Purpose:** Basic service connectivity check
**Duration:** ~10 seconds
**Requirements:** Core services running

**What it tests:**
- Service health endpoints
- API response formats
- Basic metric ingestion
- NATS connectivity

## Best Practices

### Development Workflow

1. **Start with smoke test:** `./scripts/smoke_endpoints.sh`
2. **If node-exporter fails:** `./scripts/simulate_node_metrics.sh`
3. **Run full validation:** `./scripts/validate_pipeline.sh`
4. **If validation fails:** `python3 scripts/publish_test_anomalies.py`

### CI/CD Integration

```bash
#!/bin/bash
# CI validation script
set -e

echo "Starting services..."
docker compose up -d

echo "Waiting for services..."
sleep 30

echo "Running smoke test..."
./scripts/smoke_endpoints.sh

echo "Running full validation..."
export CH_USER=admin CH_PASS=admin
./scripts/validate_pipeline.sh

echo "Validation successful!"
```

### Monitoring in Production

- Monitor anomaly detection service metrics
- Set up alerts for NATS message queue depth
- Track incident API response times
- Monitor ClickHouse disk usage and query performance

## Common Metric Names

The anomaly detector specifically looks for these metrics:

### CPU Metrics
```
node_cpu_seconds_total{mode="idle"}     # Used to calculate CPU usage
node_cpu_seconds_total{mode="system"}   # System CPU time
node_cpu_seconds_total{mode="user"}     # User CPU time
```

### Memory Metrics
```
node_memory_MemTotal_bytes              # Total system memory
node_memory_MemAvailable_bytes          # Available memory (includes cache/buffers)
node_memory_MemFree_bytes               # Free memory
node_memory_Buffers_bytes               # Buffer cache
node_memory_Cached_bytes                # Page cache
```

### Filesystem Metrics
```
node_filesystem_size_bytes{mountpoint="/"}   # Total filesystem size  
node_filesystem_avail_bytes{mountpoint="/"}  # Available space
```

## Queries Used by Anomaly Detector

### CPU Usage Calculation
```promql
100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```
Returns CPU usage percentage (0-100).

### Memory Usage Calculation  
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```
Returns memory usage percentage (0-100).

### Disk Usage Calculation
```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)
```
Returns disk usage percentage (0-100).

---

## Quick Reference

| Issue | Command | Expected Result |
|-------|---------|-----------------|
| Full validation | `./scripts/validate_pipeline.sh` | "VALIDATION SUCCESSFUL" |
| No node-exporter | `./scripts/simulate_node_metrics.sh` | Metrics in VictoriaMetrics |
| Test correlation | `python3 scripts/publish_test_anomalies.py` | Incidents created |
| Basic connectivity | `./scripts/smoke_endpoints.sh` | All endpoints ✅ |
| Check incidents | `curl http://localhost:8081/incidents` | JSON array |
| Check metrics | `curl "http://localhost:8428/api/v1/query?query=up"` | Metrics data |