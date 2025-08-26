# One-Click Deployment (Interactive Yes/No Wizard)

Run:
```bash
chmod +x scripts/aiops.sh scripts/simulate_data.sh scripts/keycloak_bootstrap.sh
bash scripts/aiops.sh
```

The wizard will ask:
- Do you want to update usernames/passwords?
- Pull images first?
- Start a single service?
- Include Keycloak (SSO)?
- Start minimal (recommended) or everything?
- Run data simulation?
- Require Docker health=healthy?
- Per-service timeout?

It will then:
- Start core infra → Grafana → core microservices (and optional Keycloak) → remaining services (if selected)
- Wait for health (prefer app health endpoints where available)
- Attempt auto-fixes (OPA policy dir, Vector unauthorized, Keycloak bootstrap)
- Capture logs for any failures to logs/session-YYYYmmdd-HHMMSS/

Open:
- Grafana: http://localhost:3000
- APIs: http://localhost:8080/health, :8081/health, :8082/health
- Keycloak (if enabled): http://localhost:8089

Tips:
- Start one service: run the wizard and choose "single service"
- Collect logs: `bash scripts/aiops.sh collect-logs`
- Apply fixes: `bash scripts/aiops.sh fix`
- Stop everything: `bash scripts/aiops.sh down`

Non-interactive (CI) is still available:
```bash
bash scripts/aiops.sh up --all --with-keycloak --simulate --pull
```