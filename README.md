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

## Getting Started (Docs-first)
1. Clone the repo.
2. Read docs/architecture.md to understand the edge+core design.
3. Review docs/roadmap.md and open issues for the next milestone you want to tackle.

## Local Bootstrap
Get started quickly with the complete local development environment:
- **[Quickstart Guide](docs/quickstart.md)** - Docker Compose stack for v0.1 MVP testing
- **Stack includes**: ClickHouse, VictoriaMetrics, Grafana, Ollama, Qdrant, NATS, MailHog, Vector, VMAlert, Alertmanager
- **One command setup**: `docker compose up -d` brings up the full observability stack

## Contributing
PRs welcome. Please discuss substantial changes via issues first. Follow conventional commits if possible.

## License
This repo aggregates OSS components under their respective licenses. Content here is licensed under Apache-2.0 unless otherwise noted.