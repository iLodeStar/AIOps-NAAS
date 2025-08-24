#!/bin/bash
# AIOps NAAS Soak Test Runner
# 
# Orchestrates a 10-minute soak test of the data simulator and system health.
# Can be run locally or in CI environments.
#
# Usage:
#   bash scripts/run_soak_test.sh
#   bash scripts/run_soak_test.sh --duration 300 --config configs/vendor-integrations.yaml

set -e  # Exit on error

# Script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Default configuration
DURATION=600  # 10 minutes
CONFIG_FILE=""
LOG_LEVEL="INFO"
CLEANUP_ON_EXIT=true
DOCKER_COMPOSE_FILE="docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --duration)
            DURATION="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --compose-file)
            DOCKER_COMPOSE_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --duration SECONDS    Test duration in seconds (default: 600)"
            echo "  --config FILE         Configuration file path"
            echo "  --log-level LEVEL     Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)"
            echo "  --no-cleanup          Don't stop services after test"
            echo "  --compose-file FILE   Docker compose file to use (default: docker-compose.yml)"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}AIOps NAAS Soak Test Runner${NC}"
echo "=================================="
echo "Duration: $DURATION seconds ($(($DURATION / 60)) minutes)"
echo "Config: ${CONFIG_FILE:-default}"
echo "Log Level: $LOG_LEVEL"
echo "Docker Compose: $DOCKER_COMPOSE_FILE"
echo ""

# Function to log with timestamp
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be healthy
wait_for_service() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1
    
    log "Waiting for $service_name to be healthy..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -s -f "$health_url" >/dev/null 2>&1; then
            log "$service_name is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    log "WARNING: $service_name failed to become healthy after $max_attempts attempts"
    return 1
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check for required commands
    local missing_commands=()
    for cmd in docker python3 curl; do
        if ! command_exists "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [[ ${#missing_commands[@]} -ne 0 ]]; then
        echo -e "${RED}Error: Missing required commands: ${missing_commands[*]}${NC}"
        exit 1
    fi
    
    # Check for Python packages
    if ! python3 -c "import asyncio, json, subprocess" >/dev/null 2>&1; then
        echo -e "${RED}Error: Required Python modules not available${NC}"
        exit 1
    fi
    
    # Check if docker compose file exists
    if [[ ! -f "$DOCKER_COMPOSE_FILE" ]]; then
        echo -e "${RED}Error: Docker compose file not found: $DOCKER_COMPOSE_FILE${NC}"
        exit 1
    fi
    
    # Check if configuration file exists (if specified)
    if [[ -n "$CONFIG_FILE" && ! -f "$CONFIG_FILE" ]]; then
        echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    
    log "Prerequisites check passed"
}

# Function to start services
start_services() {
    log "Starting AIOps services..."
    
    # Create necessary directories
    mkdir -p reports logs
    
    # Start services with docker compose
    if ! docker compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        echo -e "${RED}Error: Failed to start services${NC}"
        exit 1
    fi
    
    log "Services started, waiting for health checks..."
    
    # Wait for critical services to be healthy
    local services=(
        "NATS:http://localhost:8222/healthz"
        "ClickHouse:http://localhost:8123/ping"
        "VictoriaMetrics:http://localhost:8428/health"
    )
    
    for service_info in "${services[@]}"; do
        local service_name="${service_info%%:*}"
        local health_url="${service_info##*:}"
        wait_for_service "$service_name" "$health_url"
    done
    
    # Optional: Wait for application services (may not be available immediately)
    local app_services=(
        "Link-Health:http://localhost:8082/health"
        "Remediation:http://localhost:8083/health"
        "Incident-API:http://localhost:8081/health"
    )
    
    for service_info in "${app_services[@]}"; do
        local service_name="${service_info%%:*}"
        local health_url="${service_info##*:}"
        wait_for_service "$service_name" "$health_url" || true  # Don't fail if app services aren't ready
    done
}

# Function to run soak test
run_soak_test() {
    log "Starting soak test (duration: $DURATION seconds)..."
    
    # Build test command
    local test_cmd="python3 tests/e2e/test_simulator_soak.py"
    test_cmd="$test_cmd --duration $DURATION"
    test_cmd="$test_cmd --log-level $LOG_LEVEL"
    
    if [[ -n "$CONFIG_FILE" ]]; then
        test_cmd="$test_cmd --config $CONFIG_FILE"
    fi
    
    echo "Running: $test_cmd"
    
    # Run the soak test
    local start_time=$(date +%s)
    if $test_cmd; then
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        log "Soak test completed successfully in $elapsed seconds"
        return 0
    else
        local end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        log "Soak test failed after $elapsed seconds"
        return 1
    fi
}

# Function to collect artifacts
collect_artifacts() {
    log "Collecting test artifacts..."
    
    local artifacts_dir="reports/soak-test-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$artifacts_dir"
    
    # Copy test results
    if [[ -f "reports/soak-summary.json" ]]; then
        cp "reports/soak-summary.json" "$artifacts_dir/"
        log "Saved soak test summary"
    fi
    
    # Collect service logs
    log "Collecting service logs..."
    local services=("nats" "clickhouse" "victoria-metrics" "link-health" "remediation" "incident-api")
    
    for service in "${services[@]}"; do
        if docker compose -f "$DOCKER_COMPOSE_FILE" ps "$service" >/dev/null 2>&1; then
            docker compose -f "$DOCKER_COMPOSE_FILE" logs --tail=1000 "$service" > "$artifacts_dir/${service}.log" 2>&1 || true
        fi
    done
    
    # System information
    {
        echo "=== System Information ==="
        uname -a
        echo ""
        echo "=== Docker Information ==="
        docker version
        echo ""
        echo "=== Docker Compose Services ==="
        docker compose -f "$DOCKER_COMPOSE_FILE" ps
        echo ""
        echo "=== Docker Stats ==="
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
    } > "$artifacts_dir/system-info.txt" 2>&1
    
    # Create JUnit XML from summary (basic format)
    if [[ -f "reports/soak-summary.json" ]]; then
        python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('reports/soak-summary.json', 'r') as f:
        summary = json.load(f)
    
    test_name = 'soak_test'
    duration = summary.get('test_info', {}).get('duration_seconds', 0)
    assertions = summary.get('assertions', {})
    errors = summary.get('errors', [])
    
    # Simple JUnit XML generation
    junit_xml = '''<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<testsuite name=\"AIOps NAAS Soak Test\" tests=\"1\" failures=\"{failures}\" errors=\"{error_count}\" time=\"{duration}\">
    <testcase name=\"{test_name}\" time=\"{duration}\">
        {failure_content}
    </testcase>
</testsuite>'''.format(
        test_name=test_name,
        duration=duration,
        failures=1 if not all(assertions.values()) else 0,
        error_count=len(errors),
        failure_content='''<failure message=\"Assertions failed\">''' + str(assertions) + '''</failure>''' if not all(assertions.values()) else ''
    )
    
    with open('$artifacts_dir/junit-results.xml', 'w') as f:
        f.write(junit_xml)
    
    print('JUnit XML generated')
except Exception as e:
    print(f'Failed to generate JUnit XML: {e}')
" || true
    fi
    
    log "Artifacts collected in: $artifacts_dir"
    echo "Contents:"
    ls -la "$artifacts_dir"
}

# Function to stop services
stop_services() {
    log "Stopping services..."
    docker compose -f "$DOCKER_COMPOSE_FILE" down || true
    log "Services stopped"
}

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        echo -e "${RED}Script failed with exit code $exit_code${NC}"
    fi
    
    if [[ "$CLEANUP_ON_EXIT" == "true" ]]; then
        stop_services
    else
        log "Skipping cleanup (--no-cleanup specified)"
    fi
    
    exit $exit_code
}

# Function to show final results
show_results() {
    echo ""
    echo -e "${BLUE}===============================================${NC}"
    echo -e "${BLUE}SOAK TEST RESULTS${NC}"
    echo -e "${BLUE}===============================================${NC}"
    
    if [[ -f "reports/soak-summary.json" ]]; then
        # Extract key results using Python
        python3 -c "
import json
import sys

try:
    with open('reports/soak-summary.json', 'r') as f:
        summary = json.load(f)
    
    test_info = summary.get('test_info', {})
    health_info = summary.get('health_monitoring', {})
    assertions = summary.get('assertions', {})
    errors = summary.get('errors', [])
    
    print(f'Duration: {test_info.get(\"duration_seconds\", 0):.1f} seconds')
    print(f'Health Checks: {health_info.get(\"total_checks\", 0)}')
    print(f'Overall Health Rate: {health_info.get(\"overall_health_rate\", 0):.1f}%')
    print(f'Errors: {len(errors)}')
    print('')
    
    all_passed = all(assertions.values())
    print(f'All Assertions Passed: {\"✅ YES\" if all_passed else \"❌ NO\"}')
    
    for assertion, passed in assertions.items():
        status = '✅' if passed else '❌'
        print(f'  {status} {assertion}')
    
    sys.exit(0 if all_passed else 1)
    
except Exception as e:
    print(f'Failed to read results: {e}')
    sys.exit(1)
"
        local result_code=$?
        
        if [[ $result_code -eq 0 ]]; then
            echo -e "${GREEN}✅ SOAK TEST PASSED${NC}"
        else
            echo -e "${RED}❌ SOAK TEST FAILED${NC}"
        fi
        
        return $result_code
    else
        echo -e "${RED}❌ NO RESULTS FOUND${NC}"
        return 1
    fi
}

# Main execution
main() {
    # Set up cleanup trap
    trap cleanup EXIT
    
    # Check prerequisites
    check_prerequisites
    
    # Start services
    start_services
    
    # Run soak test
    if run_soak_test; then
        log "Soak test execution completed"
    else
        log "Soak test execution failed"
    fi
    
    # Collect artifacts
    collect_artifacts
    
    # Show results
    if show_results; then
        log "Soak test PASSED"
        return 0
    else
        log "Soak test FAILED"
        return 1
    fi
}

# Run main function
main "$@"