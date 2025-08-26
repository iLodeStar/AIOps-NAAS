# Local and Non-Production Deployment Guide (Beginner Friendly)

This guide walks you through setting up the AIOps NAAS platform on your own computer for learning, demos, or team testing. It assumes no prior experience with Docker or backend systems.

- Target readers: first-time users and non-infra engineers
- Estimated time: 15–30 minutes
- Works on: macOS, Windows 10/11 (with WSL2), Linux (Ubuntu/Debian/Fedora)

If you get stuck at any point, see the Troubleshooting section at the end.

References:
- **One-Click Setup** (recommended for beginners): ./one-click.md
- Edge vs Core architecture: ../architecture.md
- Keycloak OIDC setup (step-by-step with screenshots): ../onboarding/oidc-keycloak-setup.md
- Keycloak quick setup: ./keycloak.md
- Onboarding Service user guide: ../onboarding/guide.md
- Production deployment (hardening, TLS, HA): ./production.md

---

## What You Will Get

When you complete this guide, you will have a local AIOps stack running in Docker containers:

- Data & Storage (“sinks”)
  - [Edge/Core] ClickHouse: fast SQL database for events/logs
  - [Edge/Core] VictoriaMetrics: time-series database for metrics
  - [Edge/Core] Qdrant: vector database for AI embeddings (optional)
- Platform Services
  - [Edge] NATS: message bus for streaming data between services
  - [Edge] Benthos/Vector: stream processing & log shipping (optional)
- AIOps Microservices
  - [Edge] Anomaly Detection: detects anomalies from telemetry streams
  - [Edge] Incident API: stores and manages incidents
  - [Edge] Link Health: predicts satellite link performance
  - [Edge] Remediation: auto-remediation engine
  - [Core] Fleet Aggregation (optional)
  - [Core] Capacity Forecasting (optional)
  - [Core] Cross-Ship Benchmarking (optional)
- Monitoring & UI
  - [Edge/Core] Grafana: dashboards and data exploration
  - [Edge/Core] Alertmanager/VMAlert: alerting for metrics
  - [Edge] MailHog: catch-all email inbox for alerts/tests
- Authentication (optional but recommended for UI/API logins)
  - [Core] Keycloak: identity provider (OIDC) for SSO/RBAC

You’ll also run starter tests and learn how to explore data using both UI and command-line queries.

---

## Edge vs Core (Cloud) Components

The platform is designed for “Edge” (on-ship) and “Core” (shore/cloud) deployment. Locally, you can run either or both. Full details and diagrams: ../architecture.md

- Edge (Ship) — close to devices; resilient to low bandwidth/outages:
  - [Edge] NATS, Vector/Benthos
  - [Edge] ClickHouse, VictoriaMetrics
  - [Edge] Anomaly Detection, Link Health, Remediation (and OPA when used)
  - [Edge] Grafana, VMAlert, Alertmanager, MailHog
- Core (Shore/Cloud) — fleet aggregation, centralized auth/UI:
  - [Core] ClickHouse (fleet), VictoriaMetrics/Mimir
  - [Core] Fleet Aggregation, Capacity Forecasting, Cross-Ship Benchmarking
  - [Core] Keycloak (SSO), Onboarding Service, Grafana (fleet), Qdrant

How to run subsets with Docker Compose (examples; service names may vary):
- Edge-only (minimal):
  ```
  docker compose up -d clickhouse victoria-metrics grafana nats vmagent vmalert alertmanager mailhog vector \
    anomaly-detection link-health remediation
  ```
- Core-only (example set):
  ```
  docker compose up -d clickhouse grafana keycloak onboarding-service qdrant
  ```

---

## 1) System Requirements

- OS: macOS, Windows 10/11 with WSL2, Linux (Ubuntu 20.04+)
- Memory: Minimum 8GB (16GB recommended)
- CPU: 4+ cores recommended
- Disk: 20GB free

Tip: If your machine is tight on resources, run a smaller subset (see commands above).

---

## 2) Install Required Software

Choose your OS:

- macOS:
  - Install Docker Desktop: https://docs.docker.com/desktop/install/mac-install/
  - Optional: Homebrew for extras (https://brew.sh/)
- Windows 10/11:
  - Enable WSL2: https://learn.microsoft.com/windows/wsl/install
  - Install Docker Desktop (with WSL2 backend): https://docs.docker.com/desktop/install/windows-install/
- Linux (Ubuntu/Debian):
  - Option A (quick install)
    ```bash
    sudo apt-get update
    sudo apt-get install -y docker.io docker-compose-plugin python3 python3-pip git curl
    sudo usermod -aG docker $USER
    newgrp docker
    docker --version
    docker compose version
    python3 --version
    ```
  - Option B (if docker-compose-plugin is missing)
    ```
    sudo apt update
    sudo apt install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin python3 python3-pip git curl
    sudo usermod -aG docker $USER
    newgrp docker
    ```

No separate binaries are required—Docker will pull everything.

---

## 3) Download the Repository

Pick one:

- Option A: Download ZIP (easiest)
  - Go to https://github.com/iLodeStar/AIOps-NAAS
  - Click the green “Code” button > “Download ZIP”
  - Unzip it and open a terminal in the folder
- Option B: Git clone (recommended if you know Git)
  ```bash
  git clone https://github.com/iLodeStar/AIOps-NAAS.git
  cd AIOps-NAAS
  ```

---

## 4) Create Required Accounts and API Keys (Optional but Recommended)

Some features use external APIs (e.g., weather or schedules). You can skip these for a basic local run; the platform will still work with simulated data.

- OpenWeatherMap (for weather context)
  - Sign up: https://home.openweathermap.org/users/sign_up
  - Verify email and log in
  - Get API key: https://home.openweathermap.org/api_keys
  - Save your API key as WEATHER_API_KEY
- Scheduling Provider (optional)
  - Use your organization’s scheduling API (or placeholder)
  - Obtain an API key/token from your provider
  - Save it as SCHEDULE_API_KEY

You will put these values in your .env file in the next step.

Security tip: Do not commit real API keys to Git.

---

## 5) Configure the Environment

1) Copy the example environment file and edit
```bash
cp .env.example .env
# Open it in a text editor and update values:
# - Change default passwords
# - Add WEATHER_API_KEY and SCHEDULE_API_KEY if you have them
```

Key variables commonly used:
```
CLICKHOUSE_PASSWORD=your_secure_password
GRAFANA_PASSWORD=your_admin_password
WEATHER_API_KEY=your_openweather_api_key   # optional
SCHEDULE_API_KEY=your_scheduling_api_key   # optional
LOG_LEVEL=INFO
DEBUG_MODE=false
SIMULATION_MODE=false
```

2) Configure vendor integrations (optional, recommended later)
```bash
cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml
# Open configs/vendor-integrations.yaml and adjust as needed
```
See the Vendor Configuration Guide for details: ../configuration/vendor-config.md

3) Create local folders for logs/reports
```bash
mkdir -p logs reports data/backup
```

---

## 6) Start the Platform

Start everything (recommended for first run):
```bash
docker compose up -d
docker compose ps
docker compose logs -f  # press Ctrl+C to stop viewing logs
```

Health checks:
```bash
curl http://localhost:8123/ping          # [Edge/Core] ClickHouse
curl http://localhost:8428/health        # [Edge/Core] VictoriaMetrics
curl http://localhost:3000/api/health    # [Edge/Core] Grafana
curl http://localhost:8222/healthz       # [Edge] NATS

# Application services (may take 1–2 minutes)
curl http://localhost:8080/health        # [Edge] Anomaly Detection
curl http://localhost:8081/health        # [Edge] Incident API
curl http://localhost:8082/health        # [Edge] Link Health
curl http://localhost:8083/health        # [Edge] Remediation
```

Expected resource usage (all services):
- Memory: 6–8GB
- CPU: 10–20% on a modern laptop
- Disk: ~2GB images, ~1GB data initial

If you need to run fewer services, see “Selective Service Deployment” below.

---

## 7) Access UIs and Passwords

Web interfaces:
- [Edge/Core] Grafana: http://localhost:3000 (admin / admin or use GRAFANA_PASSWORD if changed)
- [Edge/Core] ClickHouse HTTP: http://localhost:8123 (default / CLICKHOUSE_PASSWORD)
- [Edge] NATS Monitor: http://localhost:8222
- [Edge/Core] VictoriaMetrics: http://localhost:8428
- [Edge/Core] VMAlert: http://localhost:8880
- [Edge/Core] Alertmanager: http://localhost:9093
- [Edge] MailHog (email testing): http://localhost:8025
- [Edge/Core] Qdrant: http://localhost:6333
- [Core] Keycloak Admin Console (if running locally): http://localhost:8089 (admin / admin)

Tip: Keep this page open in a browser and test each URL.

---

## 8) Understand the Services (What They Do)

- [Edge] NATS (Message Bus): the “highway” for streaming telemetry and events between services
- [Edge/Core] ClickHouse (SQL DB): stores events/logs/records for fast queries and reporting
- [Edge/Core] VictoriaMetrics (TSDB): stores numeric time-series metrics for alerting and dashboards
- [Edge/Core] Qdrant (Vector DB): stores embeddings for AI similarity search (optional)
- [Edge/Core] Grafana (Dashboards): visualizes metrics and data from ClickHouse/VictoriaMetrics
- [Edge/Core] VMAlert and [Edge/Core] Alertmanager: evaluate alert rules and route notifications
- [Edge] MailHog: catches emails locally so you can see alert notifications safely
- [Edge] Vector/Benthos: optional log shipping and stream processing
- [Edge] AIOps Microservices:
  - Anomaly Detection: detects unusual patterns from telemetry
  - Incident API: creates and manages incidents
  - Link Health: predicts satellite link performance and degradation
  - Remediation: triggers automated actions to resolve known issues
- [Core] Advanced analytics:
  - Fleet Aggregation, Capacity Forecasting, Cross-Ship Benchmarking

Architecture overview and placement details: ../architecture.md

---

## 9) Single Sign-On (Keycloak) Setup and “Keys”

You can run Keycloak locally for SSO/OIDC. To avoid port conflicts with the Anomaly service on 8080, map Keycloak to 8089 on your host.

A) Start Keycloak locally
- Option 1: Quick dev mode (embedded DB, for local only)
  ```bash
  docker run --name keycloak-dev --rm -p 8089:8080 \
    -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
    quay.io/keycloak/keycloak:22.0 start-dev
  ```
  Admin Console: http://localhost:8089 (login admin/admin)

- Option 2: With Postgres (persistence)
  ```bash
  # Example compose snippet (adapt as needed)
  version: "3.8"
  services:
    postgres:
      image: postgres:15
      environment:
        POSTGRES_DB: keycloak
        POSTGRES_USER: keycloak
        POSTGRES_PASSWORD: password
    keycloak:
      image: quay.io/keycloak/keycloak:22.0
      environment:
        KEYCLOAK_ADMIN: admin
        KEYCLOAK_ADMIN_PASSWORD: admin
        KC_DB: postgres
        KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
        KC_DB_USERNAME: keycloak
        KC_DB_PASSWORD: password
      ports:
        - "8089:8080"
      command: start-dev
      depends_on: [postgres]
  ```

B) Configure Keycloak (Realm, Client, Roles, Users)
- Create Realm: aiops (Admin Console > Realm settings > Create realm)
- Create Client for onboarding-service:
  - Client type: OpenID Connect, Client ID: onboarding-service
  - Client authentication: ON (confidential), Standard flow: ON, Direct access grants: ON
  - Root URL: http://localhost:8090, Valid redirect URIs: /auth/callback
- Get Client Secret (“how to get keys”):
  - Clients > onboarding-service > Credentials > copy Secret
  - This is your OIDC_CLIENT_SECRET
- Realm keys and JWKS (public keys for token validation):
  - Discovery: http://localhost:8089/realms/aiops/.well-known/openid-configuration
  - JWKS: http://localhost:8089/realms/aiops/protocol/openid-connect/certs
- Create roles and test users (recommended):
  - Roles: aiops-requester, aiops-deployer, aiops-authoriser, aiops-admin, aiops-viewer
  - Groups named per role; assign users into groups

C) Wire services to Keycloak
- Add to your .env (or compose env):
  ```
  OIDC_ISSUER_URL=http://localhost:8089/realms/aiops
  OIDC_CLIENT_ID=onboarding-service
  OIDC_CLIENT_SECRET=your-client-secret-from-keycloak
  OIDC_REDIRECT_URI=http://localhost:8090/auth/callback
  SECRET_KEY=your-secure-random-secret-key
  ```
- If services talk over Docker network to “keycloak” container, use internal URL for backend calls:
  - Internal (service-to-service): http://keycloak:8080/realms/aiops
  - Browser redirects must use host URL http://localhost:8089

D) Test OIDC
```bash
curl -s http://localhost:8089/realms/aiops/.well-known/openid-configuration | jq .
```
- Open http://localhost:8090 (onboarding service), click Login, authenticate, return to app, validate roles.

Full step-by-step Keycloak guide with screenshots and advanced options: ../onboarding/oidc-keycloak-setup.md

---

## 10) Run the Built-In Tests

These tests generate activity and validate the platform.

From the repository root:

Make scripts executable (Linux/macOS):
```bash
chmod +x test_v03_apis.sh test_v04_apis.sh scripts/run_soak_test.sh
```

Run integration tests:
```bash
# v0.3 features test
python3 test_v03_integration.py

# v0.4 features test
python3 test_v04_integration.py
```

Run API functionality tests:
```bash
./test_v03_apis.sh
./test_v04_apis.sh
```

Soak test (10-minute comprehensive run):
```bash
bash scripts/run_soak_test.sh
# or custom
bash scripts/run_soak_test.sh --duration 300 --config configs/vendor-integrations.yaml

# View results
cat reports/soak-summary.json
```

What to expect:
- Services should report healthy
- Test scripts will output PASS/FAIL for endpoints
- Soak test will generate a summary with health checks, message counts, and anomalies

---

## 11) Explore the Data Sinks (UI and Queries)

A) [Edge/Core] Grafana (UI-first exploration)
- Open http://localhost:3000 (admin/admin)
- Explore dashboards:
  - System Overview
  - AIOps Platform (app performance and alerts)
  - Satellite Link Health (v0.3)
  - Fleet Management (v0.4)
- Use “Explore” to query:
  - Select data source: VictoriaMetrics or ClickHouse (if configured)
  - Browse available metrics/tables and build queries visually

B) [Edge/Core] VictoriaMetrics (metrics)
- List metric names:
  ```bash
  curl 'http://localhost:8428/api/v1/label/__name__/values' | jq .
  ```
- Instant query (replace METRIC_NAME):
  ```bash
  curl --get 'http://localhost:8428/api/v1/query' --data-urlencode 'query=METRIC_NAME'
  ```
- Range query over last hour:
  ```bash
  curl --get 'http://localhost:8428/api/v1/query_range' \
    --data-urlencode 'query=METRIC_NAME' \
    --data-urlencode 'start='$(date -u -d '-1 hour' +%s) \
    --data-urlencode 'end='$(date -u +%s) \
    --data-urlencode 'step=30'
  ```

C) [Edge/Core] ClickHouse (events/logs via SQL)
- Quick peek via HTTP:
  ```bash
  curl 'http://localhost:8123/?query=SHOW%20DATABASES'
  curl 'http://localhost:8123/?query=SHOW%20TABLES'
  ```
- Interactive client:
  ```bash
  docker compose exec clickhouse clickhouse-client -u default --password $CLICKHOUSE_PASSWORD

  -- inside the shell:
  SHOW DATABASES;
  USE default;
  SHOW TABLES;

  -- discover likely tables
  SELECT database, name FROM system.tables
  WHERE database NOT IN ('system')
    AND (name ILIKE '%event%' OR name ILIKE '%log%' OR name ILIKE '%anomal%' OR name ILIKE '%incident%' OR name ILIKE '%telemetry%')
  ORDER BY database, name;

  -- sample rows
  DESCRIBE TABLE my_table;
  SELECT * FROM my_table LIMIT 10;
  ```

D) [Edge] NATS (message bus)
- Monitor:
  ```bash
  curl http://localhost:8222/varz | jq .
  curl http://localhost:8222/connz | jq .
  curl http://localhost:8222/subsz?subs=1 | jq .
  ```
- Consume:
  ```bash
  python3 tools/data-simulator/consumer.py --subjects "telemetry.*" --duration 60
  ```

E) [Edge/Core] Qdrant (vector DB)
- List collections:
  ```bash
  curl http://localhost:6333/collections | jq .
  ```

F) [Edge] MailHog (email testing)
- Open http://localhost:8025 to see captured emails from Alertmanager.

Tip: Use Grafana Explore, ClickHouse “SHOW TABLES”, and VictoriaMetrics label values to discover what data exists.

---

## 12) Selective Service Deployment (Resource-Saving)

Only core data services:
```bash
docker compose up -d clickhouse victoria-metrics grafana nats
```

Add monitoring stack:
```bash
docker compose up -d vmagent alertmanager vmalert mailhog vector
```

Add AIOps services:
```bash
docker compose up -d anomaly-detection incident-api link-health remediation
```

Stop optional services to save memory:
```bash
docker compose stop ollama qdrant benthos
```

---

## 13) Monitoring and Logs

- Tail logs for all services:
  ```bash
  docker compose logs -f
  ```
- Tail for specific service:
  ```bash
  docker compose logs -f link-health
  ```
- Search errors:
  ```bash
  docker compose logs | grep -E "ERROR|WARN"
  ```

---

## 14) Development Workflow (Optional)

- Rebuild a service after code changes:
  ```bash
  docker compose build service-name
  docker compose up -d service-name
  docker compose logs -f service-name
  ```
- Run quick tests:
  ```bash
  python3 test_v03_integration.py
  bash scripts/run_soak_test.sh --duration 120
  python3 tools/data-simulator/data_simulator.py --duration 30 --anomalies
  ```

---

## 15) Troubleshooting

Common issues and fixes:

- Services fail to start
  ```bash
  systemctl status docker          # Linux
  free -h                          # memory check
  df -h                            # disk space
  # Check for port conflicts (Linux/macOS)
  netstat -tulpn | grep -E ':(3000|8123|8428|4222|8025|8222|9093|8880|6333|8089)'
  ```
- Health check failures
  ```bash
  docker compose logs service-name
  docker compose restart service-name
  docker compose exec service-name ping clickhouse
  ```
- Config errors
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('configs/vendor-integrations.yaml'))"
  docker compose config
  ```
- OIDC issues
  - Invalid client credentials: verify OIDC_CLIENT_SECRET
  - Invalid redirect URI: must exactly match /auth/callback
  - No roles found: ensure roles/groups and client scopes are configured
  - Issuer mismatch: OIDC_ISSUER_URL must be the exact realm URL (includes /realms/aiops)
- Windows tips
  - Ensure Docker Desktop uses WSL2 backend
  - Allocate enough resources (Settings > Resources)
- Proxy/corporate networks
  - Configure Docker proxy in settings or systemd drop-ins (Linux)
- Memory/performance
  ```bash
  docker stats
  docker compose stop ollama qdrant benthos   # optional components
  ```

---

## 16) Cleanup and Reset

- Stop everything:
  ```bash
  docker compose down
  ```
- Remove volumes (deletes data):
  ```bash
  docker compose down -v
  ```
- Remove images:
  ```bash
  docker compose down --rmi all
  ```
- Full reset:
  ```bash
  docker compose down -v --rmi all
  docker system prune -af
  rm -f .env configs/vendor-integrations.yaml
  cp .env.example .env
  cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml
  ```

---

## 17) Next Steps

- Architecture deep dive and Edge/Core patterns: ../architecture.md
- Keycloak OIDC setup (roles, scopes, client secret, JWKS): ../onboarding/oidc-keycloak-setup.md
- Onboarding Service usage (UI/API): ../onboarding/guide.md
- Production deployment hardening: ./production.md
- Vendor configuration: ../configuration/vendor-config.md
- Full Test Plan: ../testing/test-plan.md

---

## Appendix: Reference Commands

- Verify services
  ```bash
  docker compose ps
  curl http://localhost:3000/api/health
  curl http://localhost:8428/health
  ```
- Discover VictoriaMetrics metrics
  ```bash
  curl 'http://localhost:8428/api/v1/label/__name__/values' | jq .
  ```
- Discover ClickHouse tables
  ```bash
  docker compose exec clickhouse clickhouse-client -u default --password $CLICKHOUSE_PASSWORD -q "SHOW DATABASES"
  docker compose exec clickhouse clickhouse-client -u default --password $CLICKHOUSE_PASSWORD -q "SHOW TABLES FROM default"
  ```
- Monitor NATS
  ```bash
  curl http://localhost:8222/varz | jq .
  curl http://localhost:8222/connz | jq .
  curl http://localhost:8222/subsz?subs=1 | jq .
  ```

Security note: This guide is for local and non-production use. Always rotate default credentials, use TLS, and restrict network access for production environments.
