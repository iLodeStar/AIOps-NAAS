# Cruise AIOps Platform (OSS-First, Offline-First)

An AI-powered network observability and operations platform tailored for cruise ships and other intermittently connected environments. Offline-first by design, fully open source, and optimized for high-throughput telemetry, predictive satellite link health, and safe auto-remediation.

## Why
- High likelihood of network breaks; most backhaul via satellite.
- Need for on-ship autonomy: detection, correction, and prevention even when offline.
- Central reporting and remote control when connectivity returns.
- Cost-sensitive: prefer open source or free frameworks.

## Key Capabilities
- Self-learning anomaly detection (streaming + online models)
- Event correlation across logs, metrics, and traces
- Predictive link degradation alerts (e.g., rain fade, dish misalignment)
- Auto-remediation playbooks with approvals and guardrails
- Capacity prediction for seasonal cruise traffic
- Fleet-wide dashboards and centralized control plane
- Rich LLM copilot with RAG over SOPs/configs/incident history
- Email alerting with local spooling during outages

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
2. Read docs/architecture.md to understand the edge+core design.
3. Review docs/roadmap.md for implementation status and milestones.

## Local Bootstrap
Get started quickly with the complete local development environment:
- **[Quickstart Guide](docs/quickstart.md)** - Docker Compose stack for v0.1 MVP testing
- **[v0.3 Features Guide](docs/v0.3-features.md)** - Predictive Link Health + Guarded Auto-Remediation
- **Stack includes**: ClickHouse, VictoriaMetrics, Grafana, Ollama, Qdrant, NATS, MailHog, Vector, VMAlert, Alertmanager
- **v0.3 Services**: Link Health Predictor, Remediation Engine, Open Policy Agent

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