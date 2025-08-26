#!/bin/bash
set -euo pipefail

# OLLAMA Bootstrap Script
# Automatically pulls and configures the default LLM model for OLLAMA service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
OLLAMA_DEFAULT_MODEL="${OLLAMA_DEFAULT_MODEL:-mistral}"
OLLAMA_AUTO_PULL="${OLLAMA_AUTO_PULL:-true}"
OLLAMA_HOST="${OLLAMA_HOST:-localhost:11434}"
MAX_RETRIES=30
RETRY_DELAY=10

log() {
  echo "[ollama-bootstrap] $*" >&2
}

error() {
  echo "[ollama-bootstrap] ERROR: $*" >&2
}

# Wait for OLLAMA service to be ready
wait_for_ollama() {
  local retries=0
  log "Waiting for OLLAMA service at ${OLLAMA_HOST}..."
  
  while [[ $retries -lt $MAX_RETRIES ]]; do
    if curl -s "http://${OLLAMA_HOST}/api/version" >/dev/null 2>&1; then
      log "OLLAMA service is ready"
      return 0
    fi
    
    retries=$((retries + 1))
    log "OLLAMA not ready yet (attempt $retries/$MAX_RETRIES), waiting ${RETRY_DELAY}s..."
    sleep $RETRY_DELAY
  done
  
  error "OLLAMA service did not become ready after $((MAX_RETRIES * RETRY_DELAY)) seconds"
  return 1
}

# Check if a model is already pulled
model_exists() {
  local model_name="$1"
  docker compose exec -T ollama ollama list 2>/dev/null | grep -q "^${model_name}" || return 1
}

# Pull a model
pull_model() {
  local model_name="$1"
  log "Pulling model '${model_name}' (this may take several minutes)..."
  
  if docker compose exec -T ollama ollama pull "$model_name"; then
    log "Successfully pulled model '${model_name}'"
    return 0
  else
    error "Failed to pull model '${model_name}'"
    return 1
  fi
}

# Test model functionality
test_model() {
  local model_name="$1"
  log "Testing model '${model_name}'..."
  
  local test_response
  test_response=$(curl -s -X POST "http://${OLLAMA_HOST}/api/generate" \
    -H "Content-Type: application/json" \
    -d "{\"model\":\"${model_name}\",\"prompt\":\"Hello\",\"stream\":false}" | \
    jq -r '.response' 2>/dev/null || echo "")
  
  if [[ -n "$test_response" && "$test_response" != "null" ]]; then
    log "Model '${model_name}' is working correctly"
    return 0
  else
    error "Model '${model_name}' test failed"
    return 1
  fi
}

main() {
  cd "$ROOT_DIR"
  
  # Source environment variables if .env exists
  if [[ -f .env ]]; then
    log "Loading environment from .env"
    set -a
    source .env
    set +a
  fi
  
  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --model)
        OLLAMA_DEFAULT_MODEL="$2"
        shift 2
        ;;
      --no-auto-pull)
        OLLAMA_AUTO_PULL=false
        shift
        ;;
      --host)
        OLLAMA_HOST="$2"
        shift 2
        ;;
      --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo "Options:"
        echo "  --model MODEL        Specify model to pull (default: ${OLLAMA_DEFAULT_MODEL})"
        echo "  --no-auto-pull       Skip automatic model pulling"
        echo "  --host HOST:PORT     OLLAMA service host (default: ${OLLAMA_HOST})"
        echo "  --help, -h           Show this help"
        exit 0
        ;;
      *)
        error "Unknown option: $1"
        exit 1
        ;;
    esac
  done
  
  log "Starting OLLAMA bootstrap with model: ${OLLAMA_DEFAULT_MODEL}"
  
  # Wait for OLLAMA service
  if ! wait_for_ollama; then
    error "Cannot proceed without OLLAMA service"
    exit 1
  fi
  
  # Check if auto-pull is disabled
  if [[ "$OLLAMA_AUTO_PULL" != "true" ]]; then
    log "Auto-pull is disabled (OLLAMA_AUTO_PULL=${OLLAMA_AUTO_PULL})"
    log "Model '${OLLAMA_DEFAULT_MODEL}' will need to be pulled manually if not present"
    exit 0
  fi
  
  # Check if model already exists
  if model_exists "$OLLAMA_DEFAULT_MODEL"; then
    log "Model '${OLLAMA_DEFAULT_MODEL}' already exists, skipping pull"
  else
    log "Model '${OLLAMA_DEFAULT_MODEL}' not found, pulling..."
    if ! pull_model "$OLLAMA_DEFAULT_MODEL"; then
      error "Failed to pull default model"
      exit 1
    fi
  fi
  
  # Test the model
  if test_model "$OLLAMA_DEFAULT_MODEL"; then
    log "OLLAMA bootstrap completed successfully"
    log "Default model '${OLLAMA_DEFAULT_MODEL}' is ready for use"
    log "API endpoint: http://${OLLAMA_HOST}/api/generate"
  else
    error "Model test failed, OLLAMA may not be fully functional"
    exit 1
  fi
}

main "$@"