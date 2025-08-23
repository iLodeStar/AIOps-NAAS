# Roadmap (OSS-First)

## v0.1 — MVP (Single Ship)
- Vector/Fluent Bit -> ClickHouse; Prometheus exporters -> VictoriaMetrics.
- Grafana dashboards and basic alerts; local Postfix/msmtp spooler.
- Ollama + Qdrant RAG over SOPs/configs; natural language queries to metrics/logs via LangChain tools.
- k3s + Argo CD GitOps; SOPS for secrets; WireGuard for secure mgmt.

Success: Operators see ship health, get queued email alerts during outages, and query telemetry with the LLM.

## v0.2 — Anomaly + Correlation
- Streaming anomaly detection with River (Z-score/ESD/STL, EWMA, Robust MAD).
- Benthos/Bytewax rule-based correlation (topology-aware); suppression and dedup; incident timelines in Ops Console.
- Manual runbook execution (AWX/Nornir) with OPA guardrails and full audit.

Success: Reduced noise; correlated incidents; safe guided remediations.

## v0.3 — Predict + Guarded Remediation
- Predictive satellite link health using modem KPIs + weather/location.
- Approval-gated playbooks (failover, QoS shaping, config flips); dry-run and auto-rollback.
- GitOps one-click deployments with Argo CD; Harbor cache for low-bandwidth updates.

Success: Proactive degradation alerts; safe semi-automatic remediation; reliable remote upgrades.

## v0.4 — Fleet + Forecast
- Core ClickHouse + VictoriaMetrics/Mimir; async/periodic replication from ships.
- Fleet dashboards and reports (per-ship and fleet-wide); capacity forecasting for seasonal routes.
- Cross-ship benchmarking and correlation.

Success: Central visibility across ships; capacity planning; consistent SLO reporting.

## v1.0 — Self-Learning Closed-Loop
- Confidence-scored auto-remediation for known scenarios; expand policy coverage gradually.
- Drift monitoring; periodic retraining/promotion via MLflow; shadow deployments.
- Compliance/audit, change windows, and automated post-incident reviews.

## Cost Notes
- All stack components are free/OSS. Cost is primarily hardware and satellite bandwidth.
- Use compression (zstd), downsampling, sketches (TDigest/HyperLogLog), and replication windows to minimize backhaul costs.