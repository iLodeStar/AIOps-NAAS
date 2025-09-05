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
BUILD_PARALLEL="${BUILD_PARALLEL:-false}"
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

Default (no flags): Interactive wizard with yes/no prompts including step-by-step mode.

Commands:
  (none) | wizard    Run interactive wizard (yes/no prompts)
  up                 Non-interactive startup (use flags)
  monitor            Continuous monitoring mode with live service status and logs
  status             Show docker compose status
  logs <service>     Stream logs for a service
  collect-logs       Collect logs/inspect for all services
  fix                Run auto-fixes (OPA dir, Vector auth, Keycloak bootstrap)
  down               Stop and remove containers

Interactive wizard includes:
  - Step-by-step mode: Start services in dependency order with navigation and retry options
  - Single service mode: Start just one service and exit
  - Minimal/full stack modes: Traditional grouped startup

Common flags (for non-interactive):
  --all | --minimal           Start everything or minimal set
  --service <name>            Start a single service
  --with-keycloak             Include Keycloak stack
  --simulate                  Run data simulation after start
  --ask-creds                 Prompt and set credentials in .env
  --pull                      docker compose pull before start
  --build-parallel            Build services in parallel for faster builds
  --timeout <secs>            Per-service wait (default 120)
  --require-docker-health     Require Docker health=healthy (default: use app health when known)
  --exclude "svc1 svc2"       Exclude services by name
  --no-fix                    Disable auto-fixes
  --ollama-model <model>      Specify OLLAMA model to pull (default: mistral)

Examples:
  bash scripts/aiops.sh                 # wizard (with dependency-aware step-by-step option)
  bash scripts/aiops.sh up --all --pull # non-interactive full stack
  bash scripts/aiops.sh monitor         # continuous monitoring mode
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
    grafana)                    echo "http://localhost:3000/api/health" ;;
    clickhouse)                 echo "http://localhost:8123/ping" ;;
    victoria-metrics)           echo "http://localhost:8428/health" ;;
    nats)                       echo "http://localhost:8222/healthz" ;;
    anomaly-detection)          echo "http://localhost:8080/health" ;;
    incident-api)               echo "http://localhost:8081/health" ;;
    link-health)                echo "http://localhost:8082/health" ;;
    remediation)                echo "http://localhost:8083/health" ;;
    fleet-aggregation)          echo "http://localhost:8084/health" ;;
    capacity-forecasting)       echo "http://localhost:8085/health" ;;
    cross-ship-benchmarking)    echo "http://localhost:8086/health" ;;
    incident-explanation)       echo "http://localhost:8087/health" ;;
    data-flow-visualization)    echo "http://localhost:8089/health" ;;
    application-log-collector)  echo "http://localhost:8090/health" ;;
    opa)                        echo "http://localhost:8181/health" ;;
    mailhog)                    echo "http://localhost:8025/api/v2/status" ;;
    keycloak)                   echo "http://localhost:8089/health/ready" ;;
    benthos)                    echo "http://localhost:4195/ping" ;;
    benthos-enrichment)         echo "http://localhost:4196/ping" ;;
    enhanced-anomaly-detection) echo "http://localhost:8082/health" ;;
    onboarding-service)         echo "http://localhost:8090/health" ;;
    vector)                     echo "http://localhost:8686/health" ;;
    qdrant)                     echo "http://localhost:6333/health" ;;
    ollama)                     echo "http://localhost:11434/api/version" ;;
    *)                          echo "" ;;
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
    # Check for application-level health first
    if [[ -n "$app_url" ]]; then
      if curl -fsS --max-time 2 "$app_url" >/dev/null 2>&1; then
        echo "ok(app)"
        return 0
      fi
    fi
    
    # Check Docker container state
    IFS=":" read -r status health <<<"$(docker_state "$svc")"
    
    # If container is not running, that's a failure
    if [[ "$status" != "running" ]]; then
      if [[ "$status" == "exited" ]]; then
        # Check exit code for immediate failure detection
        local cid; cid="$(dc ps -q "$svc" 2>/dev/null || true)"
        if [[ -n "$cid" ]]; then
          local exit_code; exit_code="$(docker inspect -f '{{.State.ExitCode}}' "$cid" 2>/dev/null || echo "unknown")"
          if [[ "$exit_code" != "0" && "$exit_code" != "unknown" ]]; then
            echo "fail:exited:${exit_code}"
            return 1
          fi
        fi
      fi
    elif [[ "$status" == "running" ]]; then
      # For running containers, check if there are error logs that indicate failure
      if dc logs --tail=50 "$svc" 2>/dev/null | grep -qiE "(error|fail|exception|fatal|panic|crash)" 2>/dev/null; then
        # Still check if app health is available and working
        if [[ -n "$app_url" ]]; then
          # If app health fails, it's definitely a failure
          if ! curl -fsS --max-time 2 "$app_url" >/dev/null 2>&1; then
            echo "fail:running:app_unhealthy"
            return 1
          fi
        fi
      fi
      
      # If Docker health is required and available
      if [[ "$REQUIRE_DOCKER_HEALTH" == "true" && "$health" != "none" ]]; then
        [[ "$health" == "healthy" ]] && { echo "ok(docker)"; return 0; }
        [[ "$health" == "unhealthy" ]] && { echo "fail:running:unhealthy"; return 1; }
      else
        # For services without app health endpoint, assume running = ok
        [[ -z "$app_url" ]] && { echo "ok(running)"; return 0; }
      fi
    fi
    
    sleep 2
  done

  # Timeout reached - final check
  IFS=":" read -r status health <<<"$(docker_state "$svc")"
  if [[ -n "$app_url" ]] && curl -fsS --max-time 2 "$app_url" >/dev/null 2>&1; then
    echo "ok(app_late)"
    return 0
  fi
  
  echo "fail:timeout:${status}:${health}"
  return 1
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

start_service_interactive() {
  local svc="$1"
  log "Starting $svc..."
  
  # Start the service
  dc up -d "$svc" >/dev/null 2>&1 || true
  
  # Show real-time logs for a few seconds
  echo "=== Starting $svc - Showing initial logs ==="
  timeout 10 dc logs -f --tail=20 "$svc" 2>/dev/null || true
  echo "=== End of initial logs ==="
  
  # Check service status
  local state
  state="$(wait_for_service "$svc")"
  
  if [[ "$state" == ok* ]]; then
    log "✅ $svc: STARTED SUCCESSFULLY ($state)"
    return 0
  else
    warn "❌ $svc: FAILED TO START ($state)"
    echo "=== Recent error logs for $svc ==="
    dc logs --tail=30 --no-color "$svc" 2>/dev/null | tail -10
    echo "=== End of error logs ==="
    return 1
  fi
}

# Define dependency-aware service startup order
get_service_startup_order() {
  # Define services in dependency order with clear separation of tiers
  ORDERED_SERVICES=(
    # Tier 1: Core Infrastructure (no dependencies)
    "clickhouse"
    "victoria-metrics" 
    "node-exporter"
    "mailhog"
    "opa"
    "qdrant"
    "ollama"
    
    # Tier 2: Data Collection & Monitoring (depends on Tier 1)
    "vmagent"
    "nats"
    "grafana"
    "alertmanager"
    "vector"
    
    # Tier 3: Stream Processing (depends on Tier 1-2)
    "benthos"
    "benthos-enrichment"
    "vmalert"
    
    # Tier 4: Core Services (depends on infrastructure + messaging)
    "anomaly-detection"
    "network-device-collector"
    "application-log-collector"
    "fleet-aggregation"
    "incident-api"
    "capacity-forecasting"
    "remediation"
    "link-health"
    "onboarding-service"
    
    # Tier 5: Advanced Analytics (depends on core services)
    "incident-explanation"
    "cross-ship-benchmarking"
    "data-flow-visualization"
    "enhanced-anomaly-detection"
  )
}

run_step_by_step_mode() {
  build_compose_args
  detect_services
  get_service_startup_order
  
  echo "=== Step-by-Step Service Startup Mode ==="
  echo "Services will be started in dependency order to ensure proper startup sequence."
  echo "You can navigate forward/backward, skip services, or retry failed ones."
  echo
  
  local current_index=0
  local started_services=() failed_services=() skipped_services=()
  
  # Filter ordered services to only include those that actually exist
  local available_ordered_services=()
  for svc in "${ORDERED_SERVICES[@]}"; do
    for existing in "${ALL_SERVICES[@]}"; do
      [[ "$svc" == "$existing" ]] && { available_ordered_services+=("$svc"); break; }
    done
  done
  
  while (( current_index < ${#available_ordered_services[@]} )); do
    local current_service="${available_ordered_services[$current_index]}"
    
    # Check if service is already started
    local already_started=false
    for started in "${started_services[@]}"; do
      [[ "$current_service" == "$started" ]] && { already_started=true; break; }
    done
    
    if [[ "$already_started" == "true" ]]; then
      ((current_index++))
      continue
    fi
    
    # Show current status and position
    echo
    echo "=== Service Startup Progress ($((current_index + 1))/${#available_ordered_services[@]}) ==="
    echo "🎯 Current: $current_service"
    echo "✅ Started: ${#started_services[@]} services"
    [[ ${#started_services[@]} -gt 0 ]] && echo "   ${started_services[*]}"
    echo "❌ Failed: ${#failed_services[@]} services"
    [[ ${#failed_services[@]} -gt 0 ]] && echo "   ${failed_services[*]}"
    echo "⏭️  Skipped: ${#skipped_services[@]} services"
    [[ ${#skipped_services[@]} -gt 0 ]] && echo "   ${skipped_services[*]}"
    
    # Show upcoming services
    if (( current_index + 1 < ${#available_ordered_services[@]} )); then
      echo "📋 Next up:"
      local end_idx=$((current_index + 4))
      (( end_idx > ${#available_ordered_services[@]} )) && end_idx=${#available_ordered_services[@]}
      for ((i = current_index + 1; i < end_idx; i++)); do
        echo "   ${available_ordered_services[$i]}"
      done
      (( end_idx < ${#available_ordered_services[@]} )) && echo "   ... and $((${#available_ordered_services[@]} - end_idx)) more"
    fi
    echo
    
    # Check if service has failed before
    local has_failed=false
    for failed in "${failed_services[@]}"; do
      [[ "$current_service" == "$failed" ]] && { has_failed=true; break; }
    done
    
    if [[ "$has_failed" == "true" ]]; then
      echo "⚠️  This service has failed before."
    fi
    
    # Show service options
    echo "Options for '$current_service':"
    echo "  [s] Start this service"
    echo "  [k] Skip and go to next service"
    if (( current_index > 0 )); then
      echo "  [p] Go back to previous service"
    fi
    if [[ "$has_failed" == "true" ]]; then
      echo "  [r] Restart this service (retry)"
    fi
    echo "  [l] View logs for this service"
    echo "  [v] View logs for any running service"
    echo "  [t] Check status of all services"
    echo "  [q] Quit step-by-step mode"
    echo
    
    local choice
    read -r -p "Choose option: " choice || choice=""
    
    case "$choice" in
      s|S|""|" ")
        echo "Starting $current_service..."
        if start_service_interactive "$current_service"; then
          started_services+=("$current_service")
          # Remove from failed list if it was there
          local temp_failed=()
          for f in "${failed_services[@]}"; do
            [[ "$f" != "$current_service" ]] && temp_failed+=("$f")
          done
          failed_services=("${temp_failed[@]}")
          log "✅ $current_service started successfully!"
          ((current_index++))
        else
          failed_services+=("$current_service")
          log "❌ $current_service failed to start"
          echo
          echo "What would you like to do with the failed service?"
          echo "  [n] Continue to next service"
          echo "  [r] Retry this service"
          echo "  [l] View detailed logs"
          echo "  [q] Quit"
          
          local fail_choice
          read -r -p "Choose [n/r/l/q]: " fail_choice || fail_choice=""
          
          case "$fail_choice" in
            n|N|"")
              log "Continuing to next service..."
              ((current_index++))
              ;;
            r|R)
              # Remove from failed list to retry
              local temp_failed=()
              for f in "${failed_services[@]}"; do
                [[ "$f" != "$current_service" ]] && temp_failed+=("$f")
              done
              failed_services=("${temp_failed[@]}")
              log "Retrying $current_service..."
              # Stay on same index to retry
              ;;
            l|L)
              echo "=== Detailed logs for $current_service ==="
              dc logs --tail=100 --no-color "$current_service" 2>/dev/null || echo "No logs available"
              echo "=== End of logs ==="
              read -r -p "Press Enter to continue..." || true
              ;;
            q|Q)
              log "Exiting step-by-step mode."
              return
              ;;
            *)
              log "Invalid choice. Continuing to next service..."
              ((current_index++))
              ;;
          esac
        fi
        ;;
        
      k|K)
        log "Skipping $current_service"
        skipped_services+=("$current_service")
        ((current_index++))
        ;;
        
      p|P)
        if (( current_index > 0 )); then
          ((current_index--))
          log "Going back to ${available_ordered_services[$current_index]}"
        else
          warn "Already at the first service."
        fi
        ;;
        
      r|R)
        if [[ "$has_failed" == "true" ]]; then
          # Remove from failed list
          local temp_failed=()
          for f in "${failed_services[@]}"; do
            [[ "$f" != "$current_service" ]] && temp_failed+=("$f")
          done
          failed_services=("${temp_failed[@]}")
          log "Retrying $current_service..."
          # Stay on same index to retry
        else
          warn "Service hasn't failed yet. Use 's' to start it."
        fi
        ;;
        
      l|L)
        echo "=== Logs for $current_service ==="
        dc logs --tail=20 --no-color "$current_service" 2>/dev/null || echo "No logs available yet"
        echo "=== End of logs ==="
        read -r -p "Press Enter to continue..." || true
        ;;
        
      v|V)
        echo "Running services with logs:"
        local running_services=()
        for svc in "${started_services[@]}"; do
          if [[ "$(docker_state "$svc" | cut -d: -f1)" == "running" ]]; then
            running_services+=("$svc")
          fi
        done
        
        if [[ ${#running_services[@]} -eq 0 ]]; then
          echo "No services are currently running."
        else
          local i=1
          for svc in "${running_services[@]}"; do
            echo "  [$i] $svc"
            i=$((i+1))
          done
          echo
          
          local log_choice
          read -r -p "Select service number or name to view logs: " log_choice || log_choice=""
          
          local selected_service=""
          if [[ "$log_choice" =~ ^[0-9]+$ ]]; then
            local idx=$((log_choice-1))
            if (( idx>=0 && idx<${#running_services[@]} )); then
              selected_service="${running_services[$idx]}"
            fi
          else
            for svc in "${running_services[@]}"; do
              [[ "$svc" == "$log_choice" ]] && { selected_service="$svc"; break; }
            done
          fi
          
          if [[ -n "$selected_service" ]]; then
            echo "=== Live logs for $selected_service (Press Ctrl+C to stop) ==="
            dc logs -f --tail=20 "$selected_service" 2>/dev/null || echo "No logs available"
          else
            warn "Invalid service selection."
          fi
        fi
        read -r -p "Press Enter to continue..." || true
        ;;
        
      t|T)
        echo "=== Service Status Check ==="
        for svc in "${available_ordered_services[@]}"; do
          local app_url; app_url="$(app_health_url "$svc")"
          IFS=":" read -r status health <<<"$(docker_state "$svc")"
          local app_status="N/A"
          
          if [[ -n "$app_url" ]]; then
            if curl -fsS --max-time 2 "$app_url" >/dev/null 2>&1; then
              app_status="🟢 HEALTHY"
            else
              app_status="🔴 UNHEALTHY"
            fi
          elif [[ "$status" == "running" ]]; then
            app_status="🟡 RUNNING"
          elif [[ "$status" == "exited" ]]; then
            app_status="🔴 EXITED"
          else
            app_status="⚫ STOPPED"
          fi
          
          printf "%-25s %-10s %-12s %s\n" "$svc" "$status" "$health" "$app_status"
        done
        echo
        read -r -p "Press Enter to continue..." || true
        ;;
        
      q|Q)
        log "Exiting step-by-step mode."
        break
        ;;
        
      *)
        warn "Invalid choice. Please try again."
        ;;
    esac
  done
  
  # Final summary
  echo
  echo "=== Step-by-Step Mode Complete ==="
  echo "✅ Started successfully: ${#started_services[@]} services"
  [[ ${#started_services[@]} -gt 0 ]] && echo "   ${started_services[*]}"
  echo "❌ Failed: ${#failed_services[@]} services"
  [[ ${#failed_services[@]} -gt 0 ]] && echo "   ${failed_services[*]}"
  echo "⏭️  Skipped: ${#skipped_services[@]} services"
  [[ ${#skipped_services[@]} -gt 0 ]] && echo "   ${skipped_services[*]}"
  echo
  
  echo
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

  if ask_yes_no "Do you want to build services in parallel for faster startup?" "Y"; then
    BUILD_PARALLEL=true
  fi

  local single="no" step_by_step="no"
  if ask_yes_no "Do you want to start services step-by-step in dependency order with full control?" "N"; then
    step_by_step="yes"
    MODE="step-by-step"
  elif ask_yes_no "Do you want to start a single service instead of the whole stack?" "N"; then
    single="yes"
    MODE="service"
  fi

  if ask_yes_no "Do you want to include Keycloak (SSO)?" "N"; then
    WITH_KEYCLOAK=true
  fi

  if [[ "$single" == "no" && "$step_by_step" == "no" ]]; then
    if ask_yes_no "Start a minimal, stable set first (recommended)?" "Y"; then
      MODE="minimal"
    else
      MODE="all"
    fi
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
    # Use --parallel to speed up image pulls
    dc pull --parallel || warn "Pull failed/partial, continuing with local images."
  fi

  if [[ "$MODE" == "minimal" && -z "$EXCLUDE_SERVICES" ]]; then
    EXCLUDE_SERVICES="ollama qdrant vector vmalert vmagent node-exporter"
  fi

  log "docker compose up -d (bootstrap)"
  if [[ "$BUILD_PARALLEL" == "true" ]]; then
    dc build --parallel >/dev/null 2>&1 || warn "Parallel build failed, using sequential build"
  fi
  dc up -d >/dev/null 2>&1 || true

  if [[ "$MODE" == "step-by-step" ]]; then
    log "Starting step-by-step interactive mode..."
    run_step_by_step_mode
    compose_snapshot
    log "Step-by-step mode completed."
    exit 0
  fi

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
      --build-parallel) BUILD_PARALLEL=true; shift ;;
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

cmd_monitor() {
  build_compose_args
  detect_services
  
  echo "AIOps-NAAS Continuous Monitoring Mode"
  echo "Press Ctrl+C to exit, 's' + Enter to select service logs, 'r' + Enter to refresh status"
  echo "=========================================="
  
  local selected_service=""
  local show_logs=false
  
  # Setup signal handlers
  trap 'echo; log "Monitoring stopped."; exit 0' INT TERM
  
  while true; do
    # Clear screen and show status
    clear
    echo "AIOps-NAAS Service Status - $(date)"
    echo "=========================================="
    
    local running=0 failed=0 stopped=0
    for svc in "${ALL_SERVICES[@]}"; do
      local app_url; app_url="$(app_health_url "$svc")"
      IFS=":" read -r status health <<<"$(docker_state "$svc")"
      local app_status="N/A"
      local status_color=""
      
      # Check application health
      if [[ -n "$app_url" ]]; then
        if curl -fsS --max-time 2 "$app_url" >/dev/null 2>&1; then
          app_status="HEALTHY"
          status_color="\033[32m" # Green
          ((running++))
        else
          app_status="UNHEALTHY"
          status_color="\033[31m" # Red
          ((failed++))
        fi
      elif [[ "$status" == "running" ]]; then
        app_status="RUNNING"
        status_color="\033[33m" # Yellow
        ((running++))
      elif [[ "$status" == "exited" ]]; then
        app_status="EXITED"
        status_color="\033[31m" # Red
        ((failed++))
      else
        app_status="STOPPED"
        status_color="\033[90m" # Gray
        ((stopped++))
      fi
      
      printf "${status_color}%-25s %-10s %-12s %-10s\033[0m\n" "$svc" "$status" "$health" "$app_status"
    done
    
    echo "=========================================="
    printf "Summary: \033[32m%d Running\033[0m | \033[31m%d Failed\033[0m | \033[90m%d Stopped\033[0m\n" "$running" "$failed" "$stopped"
    echo "Commands: [s] Select service for logs | [r] Refresh | [q] Quit"
    
    # If showing logs for a service
    if [[ "$show_logs" == "true" && -n "$selected_service" ]]; then
      echo "=========================================="
      echo "Recent logs for $selected_service (last 10 lines):"
      echo "=========================================="
      dc logs --tail=10 --no-color "$selected_service" 2>/dev/null || echo "No logs available"
    fi
    
    # Non-blocking input check
    if read -t 5 -n 1 input 2>/dev/null; then
      case "$input" in
        s|S)
          echo
          echo "Available services:"
          local i=1
          for s in "${ALL_SERVICES[@]}"; do
            echo "  [$i] $s"
            i=$((i+1))
          done
          echo -n "Select service number or name: "
          read -r choice
          if [[ "$choice" =~ ^[0-9]+$ ]]; then
            local idx=$((choice-1))
            if (( idx>=0 && idx<${#ALL_SERVICES[@]} )); then
              selected_service="${ALL_SERVICES[$idx]}"
              show_logs=true
            fi
          else
            for s in "${ALL_SERVICES[@]}"; do
              [[ "$s" == "$choice" ]] && { selected_service="$s"; show_logs=true; break; }
            done
          fi
          ;;
        r|R)
          # Just refresh (continue loop)
          ;;
        q|Q)
          echo
          log "Monitoring stopped."
          exit 0
          ;;
        *)
          # Invalid input, just continue
          ;;
      esac
    fi
  done
}

main() {
  cd "$ROOT_DIR"
  local cmd="${1:-wizard}"; shift || true
  case "$cmd" in
    wizard|"") run_wizard ;;
    up)        cmd_up "$@" ;;
    monitor)   cmd_monitor ;;
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