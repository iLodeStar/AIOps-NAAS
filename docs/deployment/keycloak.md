# Keycloak Setup (Optional)

This repo includes an optional Keycloak container and a bootstrap script to create:
- A realm: `KC_REALM_NAME` (default: `AIOPS`)
- A public client for Grafana: `KC_GRAFANA_CLIENT_ID` (default: `grafana`)
- A demo user: `KC_DEMO_USER` with password `KC_DEMO_PASSWORD`

Start with one click:
```bash
bash scripts/aiops.sh --with-keycloak
```

- Keycloak URL: http://localhost:8089
- Admin credentials: `KEYCLOAK_ADMIN` / `KEYCLOAK_ADMIN_PASSWORD`

Bootstrap details
- The script waits for `/health/ready`, obtains an admin token, ensures the realm, client, and user exist, and sets the user's password.
- You can re-run the bootstrap anytime:
```bash
bash scripts/keycloak_bootstrap.sh
```

Grafana SSO via Keycloak
- docker-compose.override.yml enables Grafana's Generic OAuth with Keycloak endpoints derived from:
  - Base: `${KC_BASE_URL:-http://localhost:8089}`
  - Realm: `${KC_REALM_NAME}`
- After Keycloak is up and bootstrapped, open Grafana and use the "Sign in with OAuth" button.