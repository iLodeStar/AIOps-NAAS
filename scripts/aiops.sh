#!/usr/bin/env bash
# AIOps-NAAS One-Click Interactive Wizard
# - Yes/No prompts for: credentials, Keycloak, simulation, minimal vs all, per-service start
# - Auto-fixes known issues, waits for health, captures logs for failures
# - You can still use flags for CI: run 'bash scripts/aiops.sh --help'
set -euo pipefail

TIMEOUT_SECS="${TIMEOUT_SECS:-120}"
REQUIRE_DOCKER_HEALTH="${REQUIRE_DOCKER_HEALTH:-false}"
AUTO_FIX="${AUTO_FIX:-true}"
EXCLUDE_SERVICES="${EXCLUDE_SERVICES:-}"
WITH_KEYCLOAK="${WITH_KEYCLOAK:-false}"
ASK_CREDS="${ASK_CREDS:-false}"
RUN_SIMULATION="${RUN_SIMULATION:-false}"
PULL_IMAGES="${PULL_IMAGES:-false}"
MODE="${MODE:-wizard}" # wizard|minimal|all|service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_TS="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT_DIR/logs/session-$SESSION_TS"
mkdir -p "$OUT_DIR" "$ROOT_DIR/logs" "$ROOT_DIR/reports" "$ROOT_DIR/opa/policies" "$ROOT_DIR/keycloak"

COMPOSE_ARGS=()
dc() { docker compose "${COMPOSE_ARGS[@]}" "$@"; }

command_exists() { command -v "$1" >/dev/null 2>&1; }
log()   { echo "[aiops] $*"; }
warn()  { echo "[aiops][WARN] $*"; }
error() { echo "[aiops][ERROR] $*" >&2; }

usage() {
  cat <<'EOF'
Usage: bash scripts/aiops.sh [COMMAND] [FLAGS]

Default (no flags): Interactive wizard with yes/no prompts.

Commands:
  (none) | wizard    Run interactive wizard (yes/no prompts)
  up                 Non-interactive startup (use flags)
  status             Show docker compose status
  logs <service>     Stream logs for a service
  collect-logs       Collect logs/inspect for all services
  fix                Run auto-fixes (OPA dir, Vector auth, Keycloak bootstrap)
  down               Stop and remove containers

Common flags (for non-interactive):
  --all | --minimal           Start everything or minimal set
  --service <name>            Start a single service
  --with-keycloak             Include Keycloak stack
  --simulate                  Run data simulation after start
  --ask-creds                 Prompt and set credentials in .env
  --pull                      docker compose pull before start
  --timeout <secs>            Per-service wait (default 120)
  --require-docker-health     Require Docker health=healthy (default: use app health when known)
  --exclude "svc1 svc2"       Exclude services by name
  --no-fix                    Disable auto-fixes
  --ollama-model <model>      Specify OLLAMA model to pull (default: mistral)

Examples:
  bash scripts/aiops.sh                 # wizard (yes/no prompts)
  bash scripts/aiops.sh up --all --pull # non-interactive
EOF
}

ask_yes_no() {
  local q="$1" def="${2:-Y}" ans
  local hint="[Y/n]"; [[ "$def" =~ ^[Nn]$ ]] && hint="[y/N]"
  while true; do
    read -r -p "$q $hint " ans || ans=""
    ans="${ans:-$def}"
    case "$ans" in
      [Yy]|[Yy][Ee][Ss]) return 0 ;;
      [Nn]|[Nn][Oo]) return 1 ;;
      *) echo "Please answer yes or no (y/n)." ;;
    esac
  done
}

ask_input() {
  local prompt="$1" def="${2:-}" secret="${3:-false}" reply
  if [[ "$secret" == "true" ]]; then
    read -r -s -p "$prompt [$def]: " reply || reply=""
    # Write newline to stderr to properly separate prompts
    echo >&2
  else
    read -r -p "$prompt [$def]: " reply || reply=""
  fi
  echo "${reply:-$def}"
}

set_env_kv() {
  local key="$1" value="$2" file="$ROOT_DIR/.env"
  
  if grep -qE "^${key}=" "$file" 2>/dev/null; then
    # Use grep -v to remove the line, then append the new one
    # This avoids sed delimiter issues entirely
    grep -v "^${key}=" "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
    echo "${key}=${value}" >> "$file"
  else
    echo "${key}=${value}" >> "$file"
  fi
}

ensure_env() {
  cd "$ROOT_DIR"
  if [[ ! -f .env && -f .env.example ]]; then
    cp .env.example .env
    log "Created .env from .env.example"
  elif [[ ! -f .env ]]; then
    touch .env
    log "Created blank .env"
  fi
  grep -q '^SIMULATION_MODE=' .env 2>/dev/null || echo 'SIMULATION_MODE=true' >> .env
  grep -q '^DEBUG_MODE=' .env 2>/dev/null || echo 'DEBUG_MODE=true' >> .env
}

prompt_credentials() {
  echo "Let's set credentials (press Enter to keep defaults):"
  local gf_user gf_pass ch_user ch_pass kc_admin kc_pass realm client demo_user demo_pass
  gf_user="$(ask_input "Grafana admin username" "admin" "false")"
  gf_pass="$(ask_input "Grafana admin password" "admin" "true")"
  ch_user="$(ask_input "ClickHouse username" "default" "false")"
  ch_pass="$(ask_input "ClickHouse password" "" "true")"
  kc_admin="$(ask_input "Keycloak admin username" "admin" "false")"
  kc_pass="$(ask_input "Keycloak admin password" "admin" "true")"
  realm="$(ask_input "Keycloak realm name" "AIOPS" "false")"
  client="$(ask_input "Keycloak Grafana client ID" "grafana" "false")"
  demo_user="$(ask_input "Keycloak demo username" "aiops_user" "false")"
  demo_pass="$(ask_input "Keycloak demo password" "aiops_pass" "true")"

  set_env_kv "GF_SECURITY_ADMIN_USER" "$gf_user"
  set_env_kv "GF_SECURITY_ADMIN_PASSWORD" "$gf_pass"
  set_env_kv "CLICKHOUSE_USER" "$ch_user"
  set_env_kv "CLICKHOUSE_PASSWORD" "$ch_pass"
  set_env_kv "KEYCLOAK_ADMIN" "$kc_admin"
  set_env_kv "KEYCLOAK_ADMIN_PASSWORD" "$kc_pass"
  set_env_kv "KC_REALM_NAME" "$realm"
  set_env_kv "KC_GRAFANA_CLIENT_ID" "$client"
  set_env_kv "KC_DEMO_USER" "$demo_user"
  set_env_kv "KC_DEMO_PASSWORD" "$demo_pass"
}

port_in_use() {
  local port="$1"
  if command_exists lsof; then
    lsof -i -P -n | grep -q ":${port} "
  elif command_exists ss; then
    ss -ltn | grep -q ":${port} "
  else
    return 1
  fi
}

check_ports() {
  local ports=("3000" "8080" "8081" "8082" "8083" "8123" "8428" "8181" "8222" "8025" "8089")
  local conflicts=()
  for p in "${ports[@]}"; do
    if port_in_use "$p"; then conflicts+=("$p"); fi
  done
  if (( ${#conflicts[@]} > 0 )); then
    warn "Port conflicts detected: ${conflicts[*]}"
    warn "Use: lsof -i -P -n | grep -E ':($(IFS=\|; echo "${conflicts[*]}") )'"
  fi
}

detect_services() {
  mapfile -t ALL_SERVICES < <(dc config --services)
  if [[ ${#ALL_SERVICES[@]} -eq 0 ]]; then
    error "No services found. Are you in the repo root with docker-compose.yml?"
    exit 1
  fi
}

choose_service() {
  detect_services
  echo "Available services:"
  local i=1
  for s in "${ALL_SERVICES[@]}"; do
    echo "  [$i] $s"
    i=$((i+1))
  done
  local choice
  read -r -p "Type service name or number: " choice || choice=""
  if [[ "$choice" =~ ^[0-9]+$ ]]; then
    local idx=$((choice-1))
    if (( idx>=0 && idx<${#ALL_SERVICES[@]} )); then
      echo "${ALL_SERVICES[$idx]}"
      return 0
    else
      error "Invalid number."
      return 1
    fi
  else
    for s in "${ALL_SERVICES[@]}"; do
      [[ "$s" == "$choice" ]] && { echo "$s"; return 0; }
    done
    error "Unknown service '$choice'."
    return 1
  fi
}

app_health_url() {
  case "$1" in
    grafana)             echo "http://localhost:3000/api/health" ;;
    clickhouse)          echo "http://localhost:8123/ping" ;;
    victoria-metrics)    echo "http://localhost:8428/health" ;;
    nats)                echo "http://localhost:8222/healthz" ;;
    anomaly-detection)   echo "http://localhost:8080/health" ;;
    incident-api)        echo "http://localhost:8081/health" ;;
    link-health)         echo "http://localhost:8082/health" ;;
    remediation)         echo "http://localhost:8083/health" ;;
    opa)                 echo "http://localhost:8181/health" ;;
    mailhog)             echo "http://localhost:8025/api/v2/status" ;;
    keycloak)            echo "http://localhost:8089/health/ready" ;;
    *)                   echo "" ;;
  esac
}

docker_state() {
  local svc="$1" cid status health
  cid="$(dc ps -q "$svc" 2>/dev/null || true)"
  [[ -z "$cid" ]] && { echo "none:none"; return 0; }
  status="$(docker inspect -f '{{.State.Status}}' "$cid" 2>/dev/null || echo "unknown")"
  health="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid" 2>/dev/null || echo "unknown")"
  echo "$status:$health"
}

wait_for_service() {
  local svc="$1"
  local deadline=$((SECONDS + TIMEOUT_SECS))
  local app_url; app_url="$(app_health_url "$svc")"

  dc up -d "$svc" >/dev/null 2>&1 || true

  while (( SECONDS < deadline )); do
    if [[ -n "$app_url" ]]; then
      if curl -fsS --max-time 2 "$app_url" >/dev/null; then
        echo "ok(app)"
        return 0
      fi
    fi
    IFS=":" read -r status health <<<"$(docker_state "$svc")"
    if [[ "$status" == "running" ]]; then
      if [[ "$REQUIRE_DOCKER_HEALTH" == "true" && "$health" != "none" ]]; then
        [[ "$health" == "healthy" ]] && { echo "ok(docker)"; return 0; }
      else
        echo "ok(running)"
        return 0
      fi
    fi
    sleep 2
  done

  IFS=":" read -r status health <<<"$(docker_state "$svc")"
  echo "fail:${status}:${health}"
}

auto_fix_service() {
  local svc="$1"
  case "$svc" in
    opa)
      mkdir -p "$ROOT_DIR/opa/policies"
      dc restart opa >/dev/null 2>&1 || true
      return 0
      ;;
    vector)
      if dc logs vector 2>/dev/null | grep -q "401 Unauthorized"; then
        warn "Vector ClickHouse sink unauthorized; stopping optional 'vector'."
        dc stop vector >/dev/null 2>&1 || true
        return 0
      fi
      ;;
    keycloak)
      if [[ -x "$ROOT_DIR/scripts/keycloak_bootstrap.sh" ]]; then
        bash "$ROOT_DIR/scripts/keycloak_bootstrap.sh" || true
        return 0
      fi
      ;;
  esac
  return 1
}

start_services() {
  local services=("$@") failures=()
  for svc in "${services[@]}"; do
    for x in $EXCLUDE_SERVICES; do
      [[ "$x" == "$svc" ]] && { log " - $svc: skipped (excluded)"; continue 2; }
    done

    log "Starting $svc"
    dc up -d "$svc" >/dev/null 2>&1 || true
    state="$(wait_for_service "$svc")"
    if [[ "$state" == ok* ]]; then
      log " - $svc: OK ($state)"
      continue
    fi

    warn " - $svc: not ready ($state)"
    if [[ "$AUTO_FIX" == "true" ]]; then
      if auto_fix_service "$svc"; then
        log " - $svc: applied auto-fix, rechecking..."
        state="$(wait_for_service "$svc")"
        if [[ "$state" == ok* ]]; then
          log " - $svc: OK after fix ($state)"
          continue
        fi
      fi
    fi
    failures+=("$svc|$state")
  done

  if (( ${#failures[@]} > 0 )); then
    warn "Some services failed: ${#failures[@]}"
    for item in "${failures[@]}"; do
      local svc="${item%%|*}"
      dc logs --no-color --timestamps --tail=1000 "$svc" > "$OUT_DIR/${svc}.log" 2>&1 || true
      cid="$(dc ps -q "$svc" || true)"
      [[ -n "$cid" ]] && docker inspect "$cid" > "$OUT_DIR/${svc}.inspect.json" 2>/dev/null || true
      warn " - $svc (details in $OUT_DIR/${svc}.log)"
    done
    return 1
  fi
  return 0
}

compose_snapshot() {
  {
    echo "# docker compose ps -a"
    dc ps -a
    echo
    echo "# docker compose config (rendered)"
    dc config
  } > "$OUT_DIR/compose_snapshot.txt" 2>&1 || true
}

run_wizard() {
  ensure_env

  echo "Welcome to AIOps-NAAS One-Click Setup"
  echo "This wizard will start your stack and help troubleshoot if anything fails."
  echo

  if ask_yes_no "Do you want to update usernames/passwords now?" "N"; then
    ASK_CREDS=true
    prompt_credentials
  fi

  if ask_yes_no "Do you want to pull the latest images first?" "Y"; then
    PULL_IMAGES=true
  fi

  local single="no"
  if ask_yes_no "Do you want to start a single service instead of the whole stack?" "N"; then
    single="yes"
  fi

  if ask_yes_no "Do you want to include Keycloak (SSO)?" "N"; then
    WITH_KEYCLOAK=true
  fi

  if [[ "$single" == "no" ]]; then
    if ask_yes_no "Start a minimal, stable set first (recommended)?" "Y"; then
      MODE="minimal"
    else
      MODE="all"
    fi
  else
    MODE="service"
  fi

  if [[ "$MODE" != "service" ]]; then
    if [[ "$MODE" == "all" ]] && ask_yes_no "Do you want to configure OLLAMA LLM model (included in full mode)?" "Y"; then
      local ollama_model
      ollama_model="$(ask_input "OLLAMA model to use" "mistral" "false")"
      if [[ -n "$ollama_model" && "$ollama_model" != "mistral" ]]; then
        log "Setting OLLAMA_DEFAULT_MODEL to: $ollama_model"
        set_env_kv "OLLAMA_DEFAULT_MODEL" "$ollama_model"
      fi
    fi
    
    if ask_yes_no "Run data simulation after startup (sends synthetic metrics)?" "Y"; then
      RUN_SIMULATION=true
    fi
    if ask_yes_no "Require Docker health=healthy for services that define healthchecks?" "N"; then
      REQUIRE_DOCKER_HEALTH=true
    fi
  fi

  local t
  t="$(ask_input "Per-service timeout seconds" "$TIMEOUT_SECS" "false")"
  [[ "$t" =~ ^[0-9]+$ ]] && TIMEOUT_SECS="$t" || true

  start_by_plan
}

build_compose_args() {
  COMPOSE_ARGS=()
  if [[ -f "$ROOT_DIR/docker-compose.yml" ]]; then
    COMPOSE_ARGS+=(-f "$ROOT_DIR/docker-compose.yml")
  fi
  if [[ -f "$ROOT_DIR/docker-compose.override.yml" ]]; then
    COMPOSE_ARGS+=(-f "$ROOT_DIR/docker-compose.override.yml")
  fi
  if [[ "$WITH_KEYCLOAK" == "true" && -f "$ROOT_DIR/docker-compose.keycloak.yml" ]]; then
    COMPOSE_ARGS+=(-f "$ROOT_DIR/docker-compose.keycloak.yml")
  fi
}

start_by_plan() {
  build_compose_args
  check_ports

  if [[ "$PULL_IMAGES" == "true" ]]; then
    log "Pulling images..."
    dc pull || warn "Pull failed/partial, continuing with local images."
  fi

  if [[ "$MODE" == "minimal" && -z "$EXCLUDE_SERVICES" ]]; then
    EXCLUDE_SERVICES="ollama qdrant vector vmalert vmagent node-exporter"
  fi

  log "docker compose up -d (bootstrap)"
  dc up -d >/dev/null 2>&1 || true

  if [[ "$MODE" == "service" ]]; then
    local svc
    while true; do
      if svc="$(choose_service)"; then break; else echo "Try again."; fi
    done
    log "Starting single service: $svc (timeout=${TIMEOUT_SECS}s)"
    start_services "$svc" || { warn "Service '$svc' not ready. See $OUT_DIR/${svc}.log"; exit 1; }
    compose_snapshot
    log "Service '$svc' ready."
    exit 0
  fi

  detect_services

  local core=("clickhouse" "victoria-metrics" "nats" "mailhog")
  local ui=("grafana")
  local micro=("anomaly-detection" "incident-api" "link-health")
  local rest=()
  for s in "${ALL_SERVICES[@]}"; do
    local skip=""
    for a in "${core[@]}" "${ui[@]}" "${micro[@]}"; do [[ "$s" == "$a" ]] && { skip="yes"; break; }; done
    [[ -z "$skip" ]] && rest+=("$s")
  done

  log "Starting core..."
  start_services "${core[@]}" || true
  log "Starting UI..."
  start_services "${ui[@]}" || true
  log "Starting microservices..."
  start_services "${micro[@]}" || true

  if [[ "$WITH_KEYCLOAK" == "true" ]]; then
    log "Starting Keycloak..."
    start_services "keycloak" || true
    if [[ -x "$ROOT_DIR/scripts/keycloak_bootstrap.sh" ]]; then
      bash "$ROOT_DIR/scripts/keycloak_bootstrap.sh" || warn "Keycloak bootstrap failed; check logs."
    fi
  fi

  if [[ "$MODE" == "all" ]]; then
    log "Starting remaining services..."
    start_services "${rest[@]}" || true
  else
    log "Skipping heavy services in minimal mode. Choose 'Start everything' in wizard to include them."
  fi

  # OLLAMA bootstrap - pull and configure default model if service is running
  if docker compose ps ollama | grep -q "Up"; then
    log "OLLAMA service detected, running bootstrap..."
    if [[ -x "$ROOT_DIR/scripts/ollama_bootstrap.sh" ]]; then
      bash "$ROOT_DIR/scripts/ollama_bootstrap.sh" || warn "OLLAMA bootstrap failed; check logs. You may need to manually run: docker compose exec ollama ollama pull mistral"
    else
      warn "OLLAMA bootstrap script not found."
    fi
  elif [[ "$MODE" == "all" ]]; then
    log "OLLAMA service not running, skipping model bootstrap."
  fi

  if [[ "$RUN_SIMULATION" == "true" ]]; then
    if [[ -x "$ROOT_DIR/scripts/simulate_data.sh" ]]; then
      log "Running data simulation..."
      bash "$ROOT_DIR/scripts/simulate_data.sh" || warn "Simulation failed; see logs."
    else
      warn "Simulation script not found."
    fi
  fi

  compose_snapshot

  log "Done. Summary:"
  echo " - Session logs: $OUT_DIR"
  echo " - Grafana: http://localhost:3000"
  echo " - Anomaly:  http://localhost:8080/health"
  echo " - Incident: http://localhost:8081/health"
  echo " - Link:     http://localhost:8082/health"
  [[ "$WITH_KEYCLOAK" == "true" ]] && echo " - Keycloak: http://localhost:8089"
  echo
  echo "Tips:"
  echo " - Start one service: bash scripts/aiops.sh (choose 'single service')"
  echo " - Collect logs:      bash scripts/aiops.sh collect-logs"
  echo " - Apply fixes only:  bash scripts/aiops.sh fix"
}

cmd_up() {
  local service="" ollama_model=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all) MODE="all"; shift ;;
      --minimal) MODE="minimal"; shift ;;
      --service) MODE="service"; service="${2:-}"; shift 2 ;;
      --timeout) TIMEOUT_SECS="${2:-120}"; shift 2 ;;
      --pull) PULL_IMAGES=true; shift ;;
      --exclude) EXCLUDE_SERVICES="${2:-}"; shift 2 ;;
      --no-fix) AUTO_FIX="false"; shift ;;
      --require-docker-health) REQUIRE_DOCKER_HEALTH="true"; shift ;;
      --ask-creds) ASK_CREDS=true; shift ;;
      --with-keycloak) WITH_KEYCLOAK=true; shift ;;
      --simulate) RUN_SIMULATION=true; shift ;;
      --ollama-model) ollama_model="${2:-}"; shift 2 ;;
      --help|-h) usage; exit 0 ;;
      *) error "Unknown flag: $1"; usage; exit 1 ;;
    esac
  done

  ensure_env
  
  # Set OLLAMA model if specified via command line
  if [[ -n "$ollama_model" ]]; then
    log "Setting OLLAMA_DEFAULT_MODEL to: $ollama_model"
    set_env_kv "OLLAMA_DEFAULT_MODEL" "$ollama_model"
  fi
  
  [[ "$ASK_CREDS" == "true" ]] && prompt_credentials
  start_by_plan
}

cmd_status() { build_compose_args; dc ps -a; }
cmd_logs()   { build_compose_args; local s="${1:-}"; [[ -z "$s" ]] && { error "Usage: $0 logs <service>"; exit 1; }; dc logs -f "$s"; }
cmd_fix()    { build_compose_args; AUTO_FIX=true; auto_fix_service opa || true; auto_fix_service vector || true; auto_fix_service keycloak || true; log "Auto-fix attempted."; }
cmd_down()   { build_compose_args; dc down; }
cmd_collect_logs() {
  build_compose_args
  detect_services
  for s in "${ALL_SERVICES[@]}"; do
    dc logs --no-color --timestamps --tail=1000 "$s" > "$OUT_DIR/${s}.log" 2>&1 || true
    cid="$(dc ps -q "$s" || true)"
    [[ -n "$cid" ]] && docker inspect "$cid" > "$OUT_DIR/${s}.inspect.json" 2>/dev/null || true
  done
  {
    echo "# docker compose ps -a";
    dc ps -a;
    echo;
    echo "# docker compose config (rendered)";
    dc config;
  } > "$OUT_DIR/compose_snapshot.txt" 2>&1 || true
  log "Logs collected to $OUT_DIR"
}

main() {
  cd "$ROOT_DIR"
  local cmd="${1:-wizard}"; shift || true
  case "$cmd" in
    wizard|"") run_wizard ;;
    up)        cmd_up "$@" ;;
    status)    cmd_status ;;
    logs)      cmd_logs "${1:-}" ;;
    collect-logs) cmd_collect_logs ;;
    fix)       cmd_fix ;;
    down)      cmd_down ;;
    --help|-h) usage ;;
    *) error "Unknown command: $cmd"; usage; exit 1 ;;
  esac
}

main "$@"