# AIOps NAAS - End-to-End Flow Quick Reference

## 🚀 One-Command Startup
```bash
git clone https://github.com/iLodeStar/AIOps-NAAS.git
cd AIOps-NAAS
cp .env.example .env
docker compose up -d
```

## 📊 Validate Complete Flow
```bash
# Quick health check
docker compose ps

# Test data collection  
curl "http://localhost:8428/api/v1/query?query=node_cpu_seconds_total" | jq '.data.result | length'

# Test anomaly detection
curl "http://localhost:8080/health" | jq .

# Test incident creation
python3 scripts/publish_test_anomalies.py
curl "http://localhost:8081/incidents" | jq .
```

## 🎯 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Grafana** | http://localhost:3000 | Dashboards & Visualization |
| **VictoriaMetrics** | http://localhost:8428 | Metrics Query Interface |
| **ClickHouse** | http://localhost:8123/play | Log Analysis |
| **NATS Monitor** | http://localhost:8222 | Message Bus Status |
| **Alertmanager** | http://localhost:9093 | Alert Management |
| **MailHog** | http://localhost:8025 | Email Testing |
| **Benthos Enrichment** | http://localhost:4196/ping | L1 Context Enrichment |
| **Enhanced Anomaly** | http://localhost:9082/health | L2 Anomaly Analysis |
| **Benthos Correlation** | http://localhost:4195/ping | Incident Formation |
| **Incident API** | http://localhost:9081/health | Incident REST API |

**Default Login**: admin/admin (or values from .env)

## 🔄 End-to-End Flow Verification

### 1. Data Collection ✅
- **Auto-collected**: CPU, Memory, Disk, Network metrics from Ubuntu
- **Verification**: `curl localhost:8428/api/v1/query?query=up`

### 2. Sequential Event Processing Pipeline ✅  
- **Architecture**: See [Sequential Pipeline Architecture](sequential-pipeline-architecture.md)
- **Flow**: Vector → Anomaly Detection → Benthos Enrichment → Enhanced Detection → Benthos Correlation → Incident API
- **NATS Topics**: `logs.anomalous` → `anomaly.detected` → `anomaly.detected.enriched` → `anomaly.detected.enriched.final` → `incidents.created`
- **Service Ports**: Enrichment:4196, Enhanced:9082, Correlation:4195, Incident:9081
- **Verification**: `./scripts/verify_modular_pipeline.sh`

### 3. Data Correlation ✅
- **Process**: Benthos correlates related anomalies with LLM-enhanced analysis
- **Features**: Deduplication, suppression, cross-system correlation
- **Verification**: `curl localhost:9081/api/v1/incidents` (note: port 9081, not 8081)

### 4. Configurable Anomalies ✅
- **Types**: CPU (70%), Memory (60%), Disk (80%), Network
- **Algorithms**: Statistical, Time-series, Machine Learning
- **Verification**: `curl localhost:8080/health`

### 5. Visualization ✅
- **Dashboards**: System Overview, Anomaly Trends, Incident Timeline
- **Real-time**: Metric graphs, log analysis, alert status
- **Access**: http://localhost:3000

### 6. Alerting ✅
- **Rules**: VMAlert evaluates conditions
- **Routing**: Alertmanager handles delivery
- **Testing**: MailHog shows email alerts
- **Verification**: `curl localhost:9093/api/v1/status`

### 7. Remediation ✅
- **Playbooks**: Service restart, resource cleanup, failover
- **Governance**: OPA policy-driven approvals
- **Execution**: Automated with audit trails
- **Testing**: `python3 scripts/publish_test_anomalies.py`

## 🛠️ Troubleshooting

```bash
# Service issues
docker compose logs [service-name]
docker compose restart [service-name]

# No data flowing  
curl localhost:8428/api/v1/query?query=up

# No incidents
python3 scripts/publish_test_anomalies.py
docker compose logs benthos

# UI access issues
curl localhost:3000/api/health
```

## 📈 Performance Metrics
- **Throughput**: 100K+ events/second
- **Latency**: Sub-second anomaly detection  
- **Storage**: 1TB+ log retention with compression
- **Resources**: ~6-8GB RAM, 2-4 CPU cores

## 🎉 Success Indicators
- ✅ 32+ CPU metrics collected
- ✅ 9+ services running healthy
- ✅ Grafana version 12.1.1+ accessible
- ✅ Anomaly detection connected to VM and NATS
- ✅ Test incidents created successfully
- ✅ Email alerts in MailHog UI
- ✅ All 7 requirements validated

**🎯 Result**: Complete autonomous AIOps pipeline operational with automatic data collection, intelligent anomaly detection, and policy-driven remediation.