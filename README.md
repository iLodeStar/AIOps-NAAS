# Cruise AIOps Platform (OSS-First, Offline-First)

An AI-powered network observability and operations platform tailored for cruise ships and other intermittently connected environments. Offline-first by design, fully open source, and optimized for high-throughput telemetry, predictive satellite link health, and safe auto-remediation.

## Why
- High likelihood of network breaks; most backhaul via satellite.
- Need for on-ship autonomy: detection, correction, and prevention even when offline.
- Central reporting and remote control when connectivity returns.
- Cost-sensitive: prefer open source or free frameworks.

## Key Capabilities
- **Configurable Vendor Integration**: Support for multiple satellite VSAT vendors, network device protocols (SNMP, NetFlow, Syslog), and data rates through YAML configuration and environment variables
- Self-learning anomaly detection (streaming + online models)
- Event correlation across logs, metrics, and traces
- Predictive link degradation alerts (e.g., rain fade, dish misalignment)
- Auto-remediation playbooks with approvals and guardrails
- Capacity prediction for seasonal cruise traffic
- Fleet-wide dashboards and centralized control plane
- Rich LLM copilot with RAG over SOPs/configs/incident history
- Email alerting with local spooling during outages
- **Comprehensive Testing**: 10-minute soak test suite for system validation and performance monitoring

## Architecture
See docs/architecture.md for details, including a Mermaid diagram (all labels quoted) and a full component breakdown.

## Roadmap
See docs/roadmap.md for phased milestones from MVP to self-learning closed-loop automation.

## OSS Stack (Default)
- Logs: Fluent Bit or Vector -> ClickHouse
- Metrics: Prometheus -> VictoriaMetrics (edge), VictoriaMetrics/Mimir (core)
- Traces (opt): OpenTelemetry -> Tempo/Jaeger
- Bus/Processing: NATS JetStream; Benthos/Bytewax for correlation
- LLM + RAG: Ollama + Qdrant + LangChain/LlamaIndex
- Automation: AWX + Nornir/Netmiko; OPA for policy
- UI & Auth: Grafana OSS + custom Ops Console (React) + Keycloak
- Deploy: k3s + Argo CD; Harbor registry cache (opt)

## Getting Started
1. Clone the repo.
2. **Configure for your environment**: Copy and customize vendor-specific parameters
3. Read docs/architecture.md to understand the edge+core design.
4. Review docs/roadmap.md for implementation status and milestones.
5. **For manual testing**: See docs/validation/manual-testing-guide.md for comprehensive validation procedures.

## Configuration
**Vendor Integration**: The platform supports configurable integration with various satellite VSAT vendors, network protocols, and external systems:

```bash
# Copy and customize configuration templates
cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml
cp .env.example .env

# Configure vendor models, data rates, and protocols
# See docs/configuration/vendor-config.md for detailed instructions
```

**Key Configuration Areas**:
- **Satellite RF Equipment**: VSAT vendor APIs, SNMP endpoints, KPI mapping
- **Network Devices**: Syslog, SNMP, NetFlow/sFlow protocols and polling
- **Applications**: Health check endpoints and SLA monitoring
- **External Context**: Weather APIs, NMEA navigation, scheduling feeds

For complete configuration instructions, see **[Vendor Configuration Guide](docs/configuration/vendor-config.md)**.

## Local Bootstrap
Get started quickly with the complete local development environment:
- **[One-Click Setup](docs/deployment/one-click.md)** - Interactive wizard for beginners (recommended)
- **[Quickstart Guide](docs/quickstart.md)** - Docker Compose stack for v0.1 MVP testing
- **[Local & Non-Production Guide](docs/deployment/local-and-nonprod.md)** - Comprehensive manual setup
- **[v0.3 Features Guide](docs/v0.3-features.md)** - Predictive Link Health + Guarded Auto-Remediation
- **Stack includes**: ClickHouse, VictoriaMetrics, Grafana, Ollama, Qdrant, NATS, MailHog, Vector, VMAlert, Alertmanager
- **v0.3 Services**: Link Health Predictor, Remediation Engine, Open Policy Agent

## Optional Services Guide

### Quick Enable/Disable Optional Components

The platform includes several optional services for enhanced functionality. These services are defined in `docker-compose.yml` but can be started independently:

**Optional Services:**
- **Qdrant** - Vector database for RAG/LLM functionality  
- **Benthos** - Stream correlation and incident pipeline
- **Ollama** - Local LLM inference engine

**Note**: The `.env` file toggles (`ENABLE_QDRANT`, `ENABLE_BENTHOS`, `ENABLE_OLLAMA`) are for application logic, not Docker Compose. Use the commands below to control which services run.

### Start/Stop Individual Services

```bash
# Start optional services
docker compose up -d qdrant ollama benthos

# Stop optional services  
docker compose stop qdrant ollama benthos

# View service status
docker compose ps qdrant ollama benthos
```

### Service Quick Links & Usage

**🔍 Qdrant (Vector Database)**
- Dashboard: [http://localhost:6333](http://localhost:6333) 
- Check collections: `curl http://localhost:6333/collections | jq .`
- Docs: [Qdrant Quick Start](https://qdrant.tech/documentation/quick-start/)

**🤖 Ollama (LLM Runtime)**
- API: [http://localhost:11434](http://localhost:11434)
- **Default model**: `mistral` (automatically pulled on startup)
- **Configure different model**: Set `OLLAMA_DEFAULT_MODEL` in `.env` or use `--ollama-model` flag
- Test API: `curl http://localhost:11434/api/generate -d '{"model":"mistral","prompt":"Explain AIOps:","stream":false}'`
- Model library: [https://ollama.com/library](https://ollama.com/library)

**🔀 Benthos (Stream Correlation)**
- Config: `benthos/benthos.yaml`
- Debug/metrics: [http://localhost:4195](http://localhost:4195)
- Pipeline: `anomaly.detected` → correlation logic → `incidents.created`
- Health: `docker compose logs -f benthos`

### Recommended Service Start Order

**1. Core Data Stack:**
```bash
docker compose up -d clickhouse victoria-metrics grafana nats
```

**2. Monitoring & Alerts (optional):**
```bash
docker compose up -d vmagent alertmanager vmalert mailhog vector
```

**3. Incident Pipeline:**
```bash  
docker compose up -d incident-api benthos
```

**4. AI/ML Stack:**
```bash
docker compose up -d qdrant ollama
# Model is automatically pulled - no manual setup needed!
# Default: mistral (configurable via OLLAMA_DEFAULT_MODEL in .env)
```

### Quick Start v0.3/v0.4
```bash
# Start the full stack including v0.3/v0.4 services
docker compose up -d

# Test v0.3 predictive and remediation features  
python3 test_v03_integration.py

# Test v0.4 fleet reporting and capacity forecasting
python3 test_v04_integration.py

# Explore v0.3/v0.4 APIs
./test_v03_apis.sh
./test_v04_apis.sh
```

**New in v0.3**: 
- 🔮 **Predictive Link Health**: ML-based satellite link degradation prediction with 15-min lead time
- 🛡️ **Guarded Auto-Remediation**: Policy-driven automated remediation with approval workflows
- 🔒 **Policy Enforcement**: OPA-based decision making for safe automation

**New in v0.4**:
- 📊 **Fleet Reporting**: Multi-ship aggregation and centralized dashboards
- 📈 **Capacity Forecasting**: ML-based traffic prediction and resource planning
- ⚖️ **Cross-Ship Benchmarking**: Performance comparison and optimization recommendations

### Manual Testing & Validation

**For Test Engineers**: Comprehensive validation procedures are provided for manual testing of the complete data flow:

```bash
# Quick validation guide
./scripts/manual_validation_test.sh

# Troubleshooting diagnostics
./scripts/troubleshoot_validation.sh
```

**Documentation:**
- **Complete Guide**: [docs/validation/manual-testing-guide.md](docs/validation/manual-testing-guide.md) - Step-by-step validation from syslog capture to anomaly detection
- **Quick Reference**: [docs/validation/quick-reference-card.md](docs/validation/quick-reference-card.md) - Essential commands and endpoints
- **Troubleshooting**: Built-in diagnostic tools for common issues

### Quick Links to UIs and APIs

**Core Services:**
- **Grafana Dashboards**: [http://localhost:3000](http://localhost:3000) (admin/admin)
- **ClickHouse UI**: [http://localhost:8123/play](http://localhost:8123/play)  
- **VictoriaMetrics**: [http://localhost:8428](http://localhost:8428)
- **NATS Monitoring**: [http://localhost:8222](http://localhost:8222)

**Optional Services:**
- **Qdrant Dashboard**: [http://localhost:6333](http://localhost:6333)
- **Benthos Debug**: [http://localhost:4195](http://localhost:4195)
- **Ollama API**: [http://localhost:11434](http://localhost:11434)

**Development:**
- **Local Deployment Guide**: [docs/deployment/local-and-nonprod.md](docs/deployment/local-and-nonprod.md)
- **Architecture Overview**: [docs/architecture.md](docs/architecture.md)
- **Quickstart**: [docs/quickstart.md](docs/quickstart.md)

### Troubleshooting Docker Build Failures

If you encounter build failures with v0.4 services (capacity-forecasting, fleet-aggregation, cross-ship-benchmarking):

**Common Issues:**
- `Cannot connect to Docker daemon`: See [troubleshooting guide](docs/deployment/local-and-nonprod.md#15-troubleshooting)
- `asyncio-nats-client not found`: Fixed in latest version (uses `nats-py` now)
- `No matching distribution found`: SSL/network issue - try rebuilding later or check internet connection

## Testing
**Comprehensive Soak Testing**: Validate system operation with realistic workloads:

```bash
# Run 10-minute soak test with data simulator
bash scripts/run_soak_test.sh

# Run with custom configuration and duration
bash scripts/run_soak_test.sh --duration 300 --config configs/vendor-integrations.yaml

# View comprehensive test results
cat reports/soak-summary.json
```

**Integration Testing**: Validate v0.3/v0.4 features:

```bash
# Test v0.3 predictive and remediation features  
python3 test_v03_integration.py

# Test v0.4 fleet reporting and capacity forecasting
python3 test_v04_integration.py
```

For complete testing procedures, see **[Test Plan](docs/testing/test-plan.md)**.

## v1.0 Self-Learning Closed-Loop Automation (NEW!)
**Complete v1.0 implementation now available!**
- See `src/v1.0/` for the complete implementation
- Configuration files in `configs/v1.0/`
- Kubernetes deployment manifests in `deployments/v1.0/`
- Run tests with `python tests/v1.0/test_simple.py`

### v1.0 Quick Start
```bash
# Run component tests
python tests/v1.0/test_simple.py

# Experience full system demo  
python demo_v1.0.py

# Deploy to Kubernetes
kubectl apply -f deployments/v1.0/orchestrator.yaml

# Or run locally (requires Python 3.8+)
cd src/v1.0
python -c "
from auto_remediation.confidence_engine import ConfidenceEngine
engine = ConfidenceEngine('../../configs/v1.0/remediation_scenarios.json')
print('v1.0 Confidence Engine loaded successfully!')
"
```

## Contributing
PRs welcome. Please discuss substantial changes via issues first. Follow conventional commits if possible.

## License
This repo aggregates OSS components under their respective licenses. Content here is licensed under Apache-2.0 unless otherwise noted.