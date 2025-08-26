#!/usr/bin/env bash
# Bootstrap Keycloak realm, client (Grafana), and demo user via Admin API.
set -euo pipefail

BASE_URL="${KC_BASE_URL:-http://localhost:8089}"
ADMIN_USER="${KEYCLOAK_ADMIN:-admin}"
ADMIN_PASS="${KEYCLOAK_ADMIN_PASSWORD:-admin}"
REALM="${KC_REALM_NAME:-AIOPS}"
CLIENT_ID="${KC_GRAFANA_CLIENT_ID:-grafana}"
DEMO_USER="${KC_DEMO_USER:-aiops_user}"
DEMO_PASS="${KC_DEMO_PASSWORD:-aiops_pass}"

wait_ready() {
  echo -n "Waiting for Keycloak at ${BASE_URL}/health/ready "
  for _ in $(seq 1 60); do
    if curl -fsS "${BASE_URL}/health/ready" >/dev/null; then echo "OK"; return 0; fi
    echo -n "."
    sleep 2
  done
  echo "FAILED"; return 1
}

access_token() {
  curl -fsS -X POST "${BASE_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=admin-cli&username=${ADMIN_USER}&password=${ADMIN_PASS}&grant_type=password" \
    | jq -r '.access_token'
}

realm_exists() {
  local token="$1"
  curl -fsS -H "Authorization: Bearer $token" "${BASE_URL}/admin/realms/${REALM}" >/dev/null 2>&1
}

create_realm() {
  local token="$1"
  curl -fsS -X POST "${BASE_URL}/admin/realms" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "{\"realm\":\"${REALM}\",\"enabled\":true}" >/dev/null
}

client_exists() {
  local token="$1"
  curl -fsS -H "Authorization: Bearer $token" "${BASE_URL}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | jq -e 'length>0' >/dev/null
}

create_client() {
  local token="$1"
  curl -fsS -X POST "${BASE_URL}/admin/realms/${REALM}/clients" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "{\"clientId\":\"${CLIENT_ID}\",\"enabled\":true,\"publicClient\":true,\"redirectUris\":[\"http://localhost:3000/*\"],\"webOrigins\":[\"*\"]}" >/dev/null
}

user_exists() {
  local token="$1"
  curl -fsS -H "Authorization: Bearer $token" "${BASE_URL}/admin/realms/${REALM}/users?username=${DEMO_USER}" | jq -e 'length>0' >/dev/null
}

create_user() {
  local token="$1"
  curl -fsS -X POST "${BASE_URL}/admin/realms/${REALM}/users" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "{\"username\":\"${DEMO_USER}\",\"enabled\":true}" >/dev/null
  local uid
  uid="$(curl -fsS -H "Authorization: Bearer $token" "${BASE_URL}/admin/realms/${REALM}/users?username=${DEMO_USER}" | jq -r '.[0].id')"
  curl -fsS -X PUT "${BASE_URL}/admin/realms/${REALM}/users/${uid}/reset-password" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "{\"type\":\"password\",\"temporary\":false,\"value\":\"${DEMO_PASS}\"}" >/dev/null
}

main() {
  command -v jq >/dev/null 2>&1 || { echo "[keycloak] 'jq' is required"; exit 1; }
  wait_ready
  local token; token="$(access_token)"

  if realm_exists "$token"; then
    echo "[keycloak] Realm '${REALM}' exists."
  else
    echo "[keycloak] Creating realm '${REALM}'..."
    create_realm "$token"
  fi

  if client_exists "$token"; then
    echo "[keycloak] Client '${CLIENT_ID}' exists."
  else
    echo "[keycloak] Creating client '${CLIENT_ID}'..."
    create_client "$token"
  fi

  if user_exists "$token"; then
    echo "[keycloak] User '${DEMO_USER}' exists."
  else
    echo "[keycloak] Creating user '${DEMO_USER}'..."
    create_user "$token"
  fi

  echo "[keycloak] Bootstrap complete."
}

main "$@"