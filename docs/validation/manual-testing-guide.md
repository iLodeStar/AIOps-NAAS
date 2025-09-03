# Manual Validation Testing Guide

## Overview

This guide provides step-by-step instructions for test engineers to manually validate the complete AIOps NAAS data flow from syslog collection on Ubuntu to anomaly detection services. Each step includes practical commands, UI navigation, screenshots, and troubleshooting guidance.

## Prerequisites

- Ubuntu 18.04+ system with Docker Engine 20.10+
- At least 8GB RAM and 20GB free disk space
- Basic command line knowledge
- Access to browser for UI validation

## Pre-Validation: Docker Environment Setup

Before starting the 5-step validation process, ensure your Docker environment is properly configured.

### 1. Validate Docker Installation

```bash
# Check Docker version and status
docker --version
docker compose version
sudo systemctl status docker

# Expected output: Docker version 20.10+ and active status
```

### 2. Start AIOps NAAS Platform

```bash
# Navigate to project directory
cd /path/to/AIOps-NAAS

# Copy environment configuration
cp .env.example .env

# Start all services
docker compose up -d

# Wait 2-3 minutes for all services to start
sleep 180
```

### 3. Validate All Services Are Running

```bash
# Check service status
docker compose ps

# Expected output: All services should show "healthy" or "running"
```

**Expected Services List:**
```
NAME                      STATUS
aiops-clickhouse         Up (healthy)
aiops-victoria-metrics   Up (healthy)
aiops-grafana           Up (healthy)
aiops-nats              Up (healthy)
aiops-vector            Up (healthy)
aiops-node-exporter     Up
aiops-vmagent           Up
aiops-anomaly-detection Up (healthy)
aiops-incident-api      Up (healthy)
aiops-benthos           Up (healthy)
aiops-vmalert           Up
aiops-alertmanager      Up
aiops-mailhog           Up (healthy)
```

### 4. Troubleshooting Failed Services

If any service shows unhealthy status:

```bash
# Check logs for specific service
docker compose logs [service-name] --tail 50

# Common fixes:
# 1. Restart individual service
docker compose restart [service-name]

# 2. Check resource usage
docker stats --no-stream

# 3. Clean up if needed
docker system prune -f

# 4. Restart all services
docker compose down && docker compose up -d
```

---

## Step 1: Capture Syslogs on Local Ubuntu Machine

### 1.1 Validate System Syslog Generation

```bash
# Check if rsyslog is running
sudo systemctl status rsyslog

# Check current syslog files
sudo ls -la /var/log/syslog*

# Generate test syslog entries
logger "TEST: Manual validation syslog entry $(date)"
logger -p user.info "TEST: Info level message"
logger -p user.warning "TEST: Warning level message"
logger -p user.err "TEST: Error level message"
```

### 1.2 Configure Syslog Forwarding to Vector

Vector service collects syslogs on port 514. Configure your system to forward logs:

```bash
# Check if Vector is listening on port 514
docker compose ps vector
docker compose logs vector --tail 10

# Test syslog forwarding (Vector should be listening)
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-app: Manual validation test message" | nc -u localhost 514
```

### 1.3 Validate Syslog Collection

```bash
# Check Vector is processing syslogs
docker compose logs vector --tail 20

# Expected output: Should show syslog processing messages
# Look for: "Received syslog message" or similar log entries
```

**Screenshot Required:** Take a screenshot of the Vector logs showing syslog processing

---

## Step 2: Find and Validate Log Reading Service

### 2.1 Identify the Log Reading Service

The **Vector** service is responsible for reading and processing syslogs.

```bash
# Check Vector service configuration
docker compose exec vector vector --version

# Inspect Vector configuration
docker compose exec vector cat /etc/vector/vector.toml 2>/dev/null || echo "Config location may vary"
```

### 2.2 Validate Vector Service Health

```bash
# Check Vector health endpoint
curl -s "http://localhost:8686/health" 2>/dev/null || echo "Vector API may be on different port"

# Alternative health check methods
docker compose logs vector --tail 10
docker compose exec vector vector validate --config-toml /etc/vector/vector.toml 2>/dev/null || echo "Config validation unavailable"
```

### 2.3 Vector UI and Metrics Validation

```bash
# Check if Vector exposes metrics
curl -s "http://localhost:8686/metrics" 2>/dev/null | head -20 || echo "Vector metrics not available on this port"

# Check Vector internal logs for processing stats
docker compose exec vector vector top 2>/dev/null || docker compose logs vector --tail 30
```

**Screenshot Required:** 
1. Take a screenshot of Vector logs showing active syslog processing
2. If Vector UI is available, screenshot the main dashboard
3. Screenshot showing Vector metrics output

### 2.4 Validate Data Flow from Vector

```bash
# Send test messages and trace processing
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) validation-test: Step 2 validation message" | nc -u localhost 514

# Wait a moment and check Vector logs
sleep 5
docker compose logs vector --tail 10

# Expected: Vector should show processing of the test message
```

---

## Step 3: Find Service for Log Transformation and Storage

### 3.1 Identify Log Storage Service

**ClickHouse** is the primary log storage service where transformed logs are stored.

```bash
# Check ClickHouse service status
docker compose ps clickhouse

# Validate ClickHouse health
curl -s "http://localhost:8123/ping"
# Expected output: "Ok."

# Check ClickHouse version
curl -s "http://localhost:8123/" | head -5
```

### 3.2 Validate Log Storage in ClickHouse

```bash
# Access ClickHouse client
docker compose exec clickhouse clickhouse-client --query "SHOW DATABASES"

# Check for logs database/tables
docker compose exec clickhouse clickhouse-client --query "SHOW TABLES FROM system"

# Look for log-related tables (table names may vary based on Vector configuration)
docker compose exec clickhouse clickhouse-client --query "SHOW TABLES" 2>/dev/null || echo "No custom database found"
```

### 3.3 Validate Log Data in Storage

```bash
# Send a test log and verify it reaches ClickHouse
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) clickhouse-test: Step 3 storage validation" | nc -u localhost 514

# Wait for processing
sleep 10

# Try to find the log in ClickHouse (table structure may vary)
docker compose exec clickhouse clickhouse-client --query "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 5" 2>/dev/null || \
docker compose exec clickhouse clickhouse-client --query "SELECT * FROM system.query_log WHERE query LIKE '%logs%' LIMIT 5" 2>/dev/null || \
echo "Log table structure needs investigation"
```

### 3.4 ClickHouse Web UI Validation

```bash
# Access ClickHouse Play UI
echo "Open browser to: http://localhost:8123/play"
echo "Default credentials may be: default/clickhouse123 (check .env file)"

# Test query in UI
echo "Try query: SELECT name FROM system.tables WHERE database != 'system' LIMIT 10"
```

**Screenshot Required:**
1. Screenshot of ClickHouse Play UI main interface
2. Screenshot showing available tables/databases
3. Screenshot of a sample query showing log data (if available)

---

## Step 4: Validate Data Enrichment and Correlation Service

### 4.1 Identify Correlation Services

The **Benthos** service handles event correlation and data enrichment.

```bash
# Check Benthos service status
docker compose ps benthos

# Check Benthos logs for correlation activity
docker compose logs benthos --tail 20

# Validate Benthos configuration
docker compose exec benthos benthos --version 2>/dev/null || echo "Benthos version check failed"
```

### 4.2 NATS Message Bus Validation

**NATS** is the message bus that connects services for correlation.

```bash
# Check NATS service status
curl -s "http://localhost:8222/varz" | jq '{connections, in_msgs, out_msgs, subscriptions}' 2>/dev/null || \
curl -s "http://localhost:8222/varz"

# Check NATS monitoring interface
echo "NATS Monitoring UI: http://localhost:8222"
```

### 4.3 Validate Correlation Logic

```bash
# Generate correlated anomaly events for testing
python3 scripts/publish_test_anomalies.py 2>/dev/null || echo "Test script not found - using manual method"

# Manual correlation test - send multiple related anomalies
echo "Sending CPU anomaly..."
curl -X POST "http://localhost:8080/test/anomaly" -H "Content-Type: application/json" \
  -d '{"metric":"cpu_usage","value":85.5,"threshold":70}' 2>/dev/null || echo "Direct anomaly API not available"

echo "Sending Memory anomaly..."
curl -X POST "http://localhost:8080/test/anomaly" -H "Content-Type: application/json" \
  -d '{"metric":"memory_usage","value":92.3,"threshold":80}' 2>/dev/null || echo "Direct anomaly API not available"
```

### 4.4 Validate Correlation Output

```bash
# Check if correlated incidents were created
sleep 10
curl -s "http://localhost:8081/incidents" | jq '.' 2>/dev/null || \
curl -s "http://localhost:8081/incidents"

# Check Benthos logs for correlation activity
docker compose logs benthos --tail 10

# Check NATS message flow
docker compose logs nats --tail 10
```

**Screenshot Required:**
1. Screenshot of NATS monitoring UI showing active connections
2. Screenshot of Benthos logs showing correlation processing
3. Screenshot of incidents API response showing correlated events

---

## Step 5: Validate Anomaly Detection Service

### 5.1 Identify Anomaly Detection Service

The **Anomaly Detection** service performs ML-based anomaly detection.

```bash
# Check anomaly detection service status
curl -s "http://localhost:8080/health" | jq '.' 2>/dev/null || \
curl -s "http://localhost:8080/health"

# Expected output: JSON with service health status
```

### 5.2 Validate Anomaly Detection Configuration

```bash
# Check available detectors
curl -s "http://localhost:8080/detectors" | jq '.' 2>/dev/null || \
curl -s "http://localhost:8080/detectors"

# Check current configuration
curl -s "http://localhost:8080/config" | jq '.' 2>/dev/null || \
curl -s "http://localhost:8080/config"

# Check metrics endpoint
curl -s "http://localhost:8080/metrics" | jq '.' 2>/dev/null || \
curl -s "http://localhost:8080/metrics"
```

### 5.3 Test Anomaly Detection Logic

```bash
# Run comprehensive pipeline validation
./scripts/validate_pipeline.sh 2>/dev/null || echo "Pipeline validation script not executable - checking manually"

# Manual anomaly detection test
echo "Testing anomaly detection with high CPU usage..."

# Check if VictoriaMetrics has data for anomaly detection
curl -s "http://localhost:8428/api/v1/query?query=node_cpu_seconds_total" | jq '.data.result | length' 2>/dev/null || \
echo "Checking VictoriaMetrics data availability"

# Send simulated metrics if node-exporter is not running
./scripts/simulate_node_metrics.sh 2>/dev/null || echo "Node metrics simulation not available"
```

### 5.4 Validate Anomaly Detection Output

```bash
# Check anomaly detection service logs
docker compose logs anomaly-detection --tail 20

# Validate that anomalies are being published to NATS
docker compose logs nats --tail 10

# Check if incidents are created after anomaly detection
sleep 30
curl -s "http://localhost:8081/incidents" | jq 'length' 2>/dev/null || \
curl -s "http://localhost:8081/incidents"
```

### 5.5 Anomaly Detection Algorithm Validation

```bash
# Check supported anomaly detection algorithms
curl -s "http://localhost:8080/algorithms" 2>/dev/null || echo "Algorithms endpoint not available"

# Check current anomaly scores
curl -s "http://localhost:8080/scores" 2>/dev/null || echo "Scores endpoint not available"

# View recent anomaly detection activity
docker compose logs anomaly-detection --tail 50 | grep -i "anomaly\|score\|threshold"
```

**Screenshot Required:**
1. Screenshot of anomaly detection service health endpoint response
2. Screenshot of service logs showing anomaly detection processing
3. Screenshot of incidents created after anomaly detection
4. Screenshot of any available anomaly detection UI or metrics

---

## Complete End-to-End Validation

### Comprehensive Flow Test

```bash
# Run complete validation script
echo "Running comprehensive validation..."
./scripts/validate_pipeline.sh

# Expected output: "VALIDATION SUCCESSFUL - End-to-end pipeline working!"
```

### Grafana Dashboard Validation

```bash
# Access Grafana for visualization
echo "Grafana UI: http://localhost:3000"
echo "Default login: admin/admin (check .env for custom credentials)"

# Health check
curl -s "http://localhost:3000/api/health" | jq '.' 2>/dev/null || \
curl -s "http://localhost:3000/api/health"
```

**Screenshot Required:**
1. Screenshot of Grafana login page
2. Screenshot of main dashboard showing system metrics
3. Screenshot of anomaly detection dashboard (if available)
4. Screenshot of incident timeline dashboard

---

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue 1: Services Not Starting

**Symptoms:**
- `docker compose ps` shows unhealthy services
- Service logs show connection errors

**Diagnosis:**
```bash
# Check system resources
free -h
df -h
docker system df

# Check individual service logs
docker compose logs [service-name] --tail 50
```

**Solutions:**
1. Increase system resources (RAM/disk space)
2. Restart services: `docker compose restart [service-name]`
3. Clean Docker system: `docker system prune -f`
4. Restart entire stack: `docker compose down && docker compose up -d`

#### Issue 2: No Data Flow

**Symptoms:**
- Endpoints return empty responses
- No logs in service containers
- Metrics not appearing in VictoriaMetrics

**Diagnosis:**
```bash
# Check connectivity between services
./scripts/smoke_endpoints.sh 2>/dev/null || echo "Smoke test not available"

# Manual endpoint testing
curl http://localhost:8123/ping  # ClickHouse
curl http://localhost:8428/health # VictoriaMetrics
curl http://localhost:8080/health # Anomaly Detection
```

**Solutions:**
1. Verify all services are running: `docker compose ps`
2. Check Docker network: `docker network ls`
3. Restart data collection: `docker compose restart vmagent node-exporter vector`

#### Issue 3: No Anomalies Detected

**Symptoms:**
- Incident API returns empty array
- Anomaly detection service shows no activity

**Diagnosis:**
```bash
# Check if metrics are flowing to VictoriaMetrics
curl "http://localhost:8428/api/v1/query?query=up" | jq '.data.result | length'

# Check anomaly detection service configuration
curl http://localhost:8080/config
```

**Solutions:**
1. Generate test data: `./scripts/simulate_node_metrics.sh`
2. Lower anomaly thresholds in service configuration
3. Publish test anomalies: `python3 scripts/publish_test_anomalies.py`

### Service Dependency Order

Start services in this order for troubleshooting:

```bash
# 1. Storage layer
docker compose up -d clickhouse victoria-metrics nats

# 2. Data collection  
docker compose up -d vmagent node-exporter vector

# 3. Processing layer
docker compose up -d anomaly-detection benthos

# 4. API and UI layer
docker compose up -d incident-api grafana
```

### Log Locations for Investigation

```bash
# Service logs
docker compose logs clickhouse --tail 50
docker compose logs victoria-metrics --tail 50
docker compose logs vector --tail 50
docker compose logs anomaly-detection --tail 50
docker compose logs benthos --tail 50
docker compose logs incident-api --tail 50

# System logs (if needed)
sudo journalctl -u docker --tail 50
tail -f /var/log/syslog
```

---

## Validation Checklist

Use this checklist to ensure all steps are completed:

### Pre-Validation Setup
- [ ] Docker and Docker Compose installed and running
- [ ] AIOps NAAS repository cloned and environment configured
- [ ] All services started with `docker compose up -d`
- [ ] All services showing healthy/running status

### Step 1: Syslog Capture
- [ ] System rsyslog service is running
- [ ] Test syslog messages generated
- [ ] Vector service processing syslogs
- [ ] Screenshot of Vector logs taken

### Step 2: Log Reading Service Validation  
- [ ] Vector service identified and validated
- [ ] Vector health endpoints tested
- [ ] Vector processing logs captured
- [ ] Screenshots of Vector interface taken

### Step 3: Log Transformation and Storage
- [ ] ClickHouse service validated
- [ ] Log storage confirmed in ClickHouse
- [ ] ClickHouse UI accessed and tested
- [ ] Screenshots of ClickHouse interface taken

### Step 4: Data Enrichment and Correlation
- [ ] Benthos correlation service validated  
- [ ] NATS message bus tested
- [ ] Correlation logic tested with multiple anomalies
- [ ] Screenshots of NATS monitoring taken

### Step 5: Anomaly Detection Service
- [ ] Anomaly detection service health validated
- [ ] Service configuration checked
- [ ] Anomaly detection logic tested
- [ ] Incident creation validated
- [ ] Screenshots of anomaly detection taken

### End-to-End Validation
- [ ] Complete pipeline validation executed
- [ ] Grafana dashboards accessed
- [ ] All screenshots collected
- [ ] Troubleshooting guide reviewed

---

## Summary

This guide provides comprehensive manual validation for the AIOps NAAS platform data flow:

1. **Syslog Collection**: Ubuntu system logs → Vector service
2. **Log Processing**: Vector → ClickHouse storage
3. **Data Correlation**: NATS + Benthos correlation engine
4. **Anomaly Detection**: ML-based detection service
5. **Incident Management**: Correlated incidents via API

Each step includes practical commands, UI validation, screenshots, and troubleshooting guidance for test engineers to validate the complete system functionality.