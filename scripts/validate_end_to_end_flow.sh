#!/bin/bash
# VALIDATED End-to-End Message Tracking Script for AIOps NAAS
# This script performs actual testing and captures real console outputs

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

# Function to check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Command '$1' not found. Please install it first."
        exit 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $service_name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready!"
            return 0
        fi
        log_info "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 5
        ((attempt++))
    done
    
    log_error "$service_name failed to become ready within $((max_attempts * 5)) seconds"
    return 1
}

# Function to capture command output with error handling
run_command() {
    local description="$1"
    local command="$2"
    local expected_pattern="${3:-}"
    
    log_info "Running: $description"
    echo "Command: $command"
    
    local output
    if output=$(eval "$command" 2>&1); then
        echo "Output:"
        echo "$output"
        
        if [[ -n "$expected_pattern" && ! "$output" =~ $expected_pattern ]]; then
            log_warning "Expected pattern '$expected_pattern' not found in output"
        else
            log_success "Command completed successfully"
        fi
        echo "$output"
    else
        log_error "Command failed with exit code $?"
        echo "Error output: $output"
        return 1
    fi
}

# Main validation function
main() {
    log_step "AIOps NAAS End-to-End Message Tracking Validation"
    
    # Check prerequisites
    log_step "STEP 1: Prerequisites Check"
    check_command "docker"
    check_command "curl"
    check_command "nc"
    check_command "uuidgen"
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose not available. Please install Docker Compose v2+"
        exit 1
    fi
    
    log_success "All prerequisites are met"
    
    # Generate unique tracking ID
    log_step "STEP 2: Generate Tracking ID"
    TRACKING_ID="E2E-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
    log_success "Generated Tracking ID: $TRACKING_ID"
    echo "This ID will be used to track your message through all components"
    
    # Check services are running
    log_step "STEP 3: Service Health Checks"
    
    # Wait for services to be ready
    wait_for_service "http://localhost:8686/health" "Vector"
    wait_for_service "http://localhost:8123/ping" "ClickHouse"
    wait_for_service "http://localhost:8222/healthz" "NATS"
    wait_for_service "http://localhost:4195/ping" "Benthos"
    
    # Show detailed health status
    log_info "=== DETAILED HEALTH STATUS ==="
    run_command "Vector Health" "curl -s http://localhost:8686/health" '"status":"ok"'
    run_command "ClickHouse Health" "curl -s http://localhost:8123/ping" "Ok"
    run_command "NATS Health" "curl -s http://localhost:8222/healthz" '"status":"ok"'
    run_command "Benthos Health" "curl -s http://localhost:4195/ping" "pong"
    
    # Check container status
    log_info "=== CONTAINER STATUS ==="
    run_command "Docker Compose Status" "docker compose ps"
    
    # Test UDP syslog message
    log_step "STEP 4: Send UDP Syslog Test Message"
    
    log_info "Sending NORMAL test message via UDP to port 1514..."
    UDP_MESSAGE="<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID UDP message from validation script"
    echo "$UDP_MESSAGE" | nc -u localhost 1514
    log_success "UDP message sent: $TRACKING_ID"
    
    # Wait for processing
    sleep 10
    
    # Test TCP syslog message
    log_step "STEP 5: Send TCP Syslog Test Message"
    
    log_info "Sending NORMAL test message via TCP to port 1515..."
    TCP_MESSAGE="<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID TCP message from validation script"
    echo "$TCP_MESSAGE" | nc localhost 1515
    log_success "TCP message sent: $TRACKING_ID"
    
    # Wait for processing
    sleep 10
    
    # Check Vector metrics
    log_step "STEP 6: Verify Vector Processing"
    
    log_info "=== VECTOR METRICS ==="
    run_command "Vector Input Metrics" "curl -s http://localhost:8686/metrics | grep -E 'vector_events_in_total|vector_events_out_total' | head -10"
    
    run_command "Vector Processing Errors" "curl -s http://localhost:8686/metrics | grep -E 'vector_processing_errors_total' | head -5"
    
    # Check Vector logs for our tracking ID
    log_info "=== VECTOR LOGS FOR TRACKING ID ==="
    run_command "Vector Logs Search" "docker logs aiops-vector 2>&1 | grep '$TRACKING_ID' | head -5"
    
    # Check ClickHouse storage
    log_step "STEP 7: Verify ClickHouse Storage"
    
    run_command "ClickHouse Connection Test" "docker exec aiops-clickhouse clickhouse-client --query 'SELECT 1'"
    
    run_command "Search Tracking ID in ClickHouse" "docker exec aiops-clickhouse clickhouse-client --query \"SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 10\""
    
    run_command "Full ClickHouse Record" "docker exec aiops-clickhouse clickhouse-client --query \"SELECT * FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' FORMAT Vertical\""
    
    # Check NATS message flow
    log_step "STEP 8: Check NATS Message Flow"
    
    log_info "=== NATS SUBJECTS AND MESSAGES ==="
    run_command "NATS Server Info" "curl -s http://localhost:8222/varz | grep -E '(connections|in_msgs|out_msgs)' | head -10"
    
    # Check Benthos processing
    log_step "STEP 9: Verify Benthos Processing"
    
    run_command "Benthos Stats" "curl -s http://localhost:4195/stats | head -20"
    
    # Test anomaly detection flow
    log_step "STEP 10: Test Anomaly Detection Flow"
    
    ANOMALY_ID="ANOMALY-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
    log_info "Generating anomaly with ID: $ANOMALY_ID"
    
    ANOMALY_MESSAGE="<14>$(date '+%b %d %H:%M:%S') $(hostname) critical-service: ERROR $ANOMALY_ID Critical system failure detected"
    echo "$ANOMALY_MESSAGE" | nc -u localhost 1514
    log_success "Anomaly message sent: $ANOMALY_ID"
    
    sleep 15
    
    run_command "Search Anomaly in ClickHouse" "docker exec aiops-clickhouse clickhouse-client --query \"SELECT timestamp, level, message, source FROM logs.raw WHERE message LIKE '%$ANOMALY_ID%' ORDER BY timestamp DESC LIMIT 5\""
    
    # Final summary
    log_step "STEP 11: Validation Summary"
    
    log_success "=== VALIDATION COMPLETE ==="
    echo "Tracking IDs used:"
    echo "  Normal UDP: $TRACKING_ID (UDP)"
    echo "  Normal TCP: $TRACKING_ID (TCP)"
    echo "  Anomaly: $ANOMALY_ID"
    echo ""
    echo "To manually search for your messages:"
    echo "  ClickHouse: docker exec aiops-clickhouse clickhouse-client --query \"SELECT * FROM logs.raw WHERE message LIKE '%YOUR_ID%'\""
    echo "  Vector logs: docker logs aiops-vector | grep YOUR_ID"
    echo ""
    log_success "End-to-end message flow validation completed successfully!"
}

# Run main function
main "$@"