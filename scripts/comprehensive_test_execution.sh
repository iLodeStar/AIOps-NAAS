#!/bin/bash
# Comprehensive Test Execution Script
# This script provides automated assistance for the manual testing guide
# It does NOT replace manual testing but assists with command execution and validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test session variables
TEST_SESSION_ID="TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
TEST_START_TIME=$(date '+%Y-%m-%d %H:%M:%S')

echo -e "${BLUE}=== COMPREHENSIVE AIOPS NAAS TESTING ASSISTANT ===${NC}"
echo -e "${BLUE}Test Session ID: ${YELLOW}$TEST_SESSION_ID${NC}"
echo -e "${BLUE}Start Time: ${YELLOW}$TEST_START_TIME${NC}"
echo ""

# Function to display test step
display_step() {
    local step_num="$1"
    local description="$2"
    echo -e "${BLUE}Step $step_num:${NC} $description"
}

# Function to display expected output
display_expected() {
    local expected="$1"
    echo -e "${GREEN}Expected Output:${NC} $expected"
}

# Function to prompt for manual execution
prompt_execution() {
    local command="$1"
    echo -e "${YELLOW}Execute this command:${NC}"
    echo -e "${YELLOW}$command${NC}"
    echo ""
    read -p "Press Enter after executing the command and reviewing the output..."
}

# Function to run health checks
run_health_checks() {
    echo -e "${BLUE}=== PHASE 1: ENVIRONMENT SETUP AND VALIDATION ===${NC}"
    echo ""
    
    display_step "1.1" "ClickHouse health check"
    prompt_execution "curl -s http://localhost:8123/ping"
    display_expected "Ok."
    echo ""
    
    display_step "1.2" "Vector health check"
    prompt_execution "curl -s http://localhost:8686/health"
    display_expected '{"status":"ok","version":"..."}'
    echo ""
    
    display_step "1.3" "VictoriaMetrics health check"
    prompt_execution "curl -s http://localhost:8428/health"
    display_expected '{"status":"ok"}'
    echo ""
    
    display_step "1.4" "NATS health check"
    prompt_execution "curl -s http://localhost:8222/healthz"
    display_expected '{"status":"ok"}'
    echo ""
    
    display_step "1.5" "Benthos health check"
    prompt_execution "curl -s http://localhost:4195/ping"
    display_expected "pong"
    echo ""
    
    display_step "1.6" "Anomaly Detection service health"
    prompt_execution "curl -s http://localhost:8080/health"
    display_expected '{"status":"healthy"}'
    echo ""
}

# Function to test normal syslog flow
test_normal_syslog() {
    echo -e "${BLUE}=== TC-001: NORMAL SYSLOG FLOW ===${NC}"
    echo ""
    
    display_step "1" "Send normal UDP syslog message"
    prompt_execution "echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) test-service: NORMAL_OPERATION $TEST_SESSION_ID system startup completed\" | nc -u localhost 1514"
    display_expected "(No output = success)"
    echo ""
    
    display_step "2" "Verify Vector receives the message"
    prompt_execution "docker compose logs vector | grep \"$TEST_SESSION_ID\" | head -1"
    display_expected "JSON formatted syslog message with parsed fields"
    echo ""
    
    display_step "3" "Verify Vector processes and transforms the message"
    prompt_execution "docker compose logs vector | grep \"$TEST_SESSION_ID\" | grep '\"level\":\"INFO\"'"
    display_expected "Transformed message with ClickHouse-compatible fields"
    echo ""
    
    display_step "4" "Verify Vector sends message to ClickHouse"
    prompt_execution "curl -s http://localhost:8686/metrics | grep 'vector_events_out_total.*clickhouse'"
    display_expected "vector_events_out_total{component_id=\"clickhouse\",component_type=\"sink\"} N"
    echo ""
    
    display_step "5" "Verify message stored in ClickHouse"
    prompt_execution "docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query=\"SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 1\""
    display_expected "2025-XX-XX XX:XX:XX.XXX	INFO	NORMAL_OPERATION $TEST_SESSION_ID...	syslog	ubuntu	test-service"
    echo ""
    
    display_step "6" "Verify no anomaly detection triggered"
    prompt_execution "curl -s \"http://localhost:8428/api/v1/query?query=anomaly_detected{session_id=\\\"$TEST_SESSION_ID\\\"}\""
    display_expected '{"status":"success","data":{"resultType":"vector","result":[]}}'
    echo ""
}

# Function to test anomaly detection flow
test_anomaly_detection() {
    echo -e "${BLUE}=== TC-002: ANOMALY DETECTION FLOW ===${NC}"
    echo ""
    
    display_step "1" "Send anomalous error message"
    prompt_execution "echo \"<11>\$(date '+%b %d %H:%M:%S') \$(hostname) critical-service: ERROR $TEST_SESSION_ID CRITICAL_FAILURE database connection lost timeout exceeded\" | nc localhost 1515"
    display_expected "(No output = success)"
    echo ""
    
    display_step "2" "Verify Vector processes anomalous message"
    prompt_execution "docker compose logs vector | grep \"$TEST_SESSION_ID\" | grep \"CRITICAL_FAILURE\""
    display_expected "JSON message with error severity and CRITICAL_FAILURE content"
    echo ""
    
    display_step "3" "Verify message stored in ClickHouse"
    prompt_execution "docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query=\"SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%CRITICAL_FAILURE%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 1\""
    display_expected "Message with CRITICAL_FAILURE content stored in ClickHouse"
    echo ""
    
    display_step "4" "Verify anomaly detection triggers"
    prompt_execution "docker compose logs anomaly-detection | grep \"$TEST_SESSION_ID\""
    display_expected "Anomaly detection processing logs with WARNING/ERROR level"
    echo ""
    
    display_step "5" "Verify NATS message published"
    echo -e "${YELLOW}Run this command in a separate terminal to monitor NATS:${NC}"
    echo -e "${YELLOW}timeout 10s docker exec aiops-nats nats sub \"anomaly.detected\" --count=1 | grep \"$TEST_SESSION_ID\"${NC}"
    display_expected "Anomaly event JSON with session_id, anomaly_type, severity, message"
    read -p "Press Enter after checking NATS output..."
    echo ""
    
    display_step "6" "Verify Benthos processes anomaly event"
    prompt_execution "curl -s http://localhost:4195/stats | jq '.input.broker.received'"
    display_expected "Incremented count showing event received"
    echo ""
    
    display_step "7" "Verify incident creation"
    prompt_execution "curl -s \"http://localhost:8081/api/v1/incidents?session_id=$TEST_SESSION_ID\" | jq '.'"
    display_expected "Created incident JSON with id, session_id, severity, status, correlation details"
    echo ""
}

# Function to test host metrics
test_host_metrics() {
    echo -e "${BLUE}=== TC-003: HOST METRICS FLOW ===${NC}"
    echo ""
    
    display_step "1" "Verify host metrics collection"
    prompt_execution "docker compose logs vector | grep '\"name\":\"host_cpu_seconds_total\"' | head -1"
    display_expected "Host CPU metric JSON with counter value and timestamp"
    echo ""
    
    display_step "2" "Verify metrics transformation for ClickHouse"
    prompt_execution "docker compose logs vector | grep '\"source\":\"host_metrics\"' | head -1"
    display_expected "Transformed metric with ClickHouse fields and readable message"
    echo ""
    
    display_step "3" "Verify metrics stored in ClickHouse"
    prompt_execution "docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query=\"SELECT timestamp, message, source, host FROM logs.raw WHERE source = 'host_metrics' ORDER BY timestamp DESC LIMIT 3\""
    display_expected "Recent host metrics entries with CPU, memory, disk information"
    echo ""
}

# Function to display final summary
display_summary() {
    echo -e "${BLUE}=== TESTING COMPLETE ===${NC}"
    echo -e "${BLUE}Test Session ID: ${YELLOW}$TEST_SESSION_ID${NC}"
    echo -e "${BLUE}End Time: ${YELLOW}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""
    echo -e "${GREEN}Please review all outputs and document results using the template in:${NC}"
    echo -e "${GREEN}COMPREHENSIVE_STEP_BY_STEP_TESTING_GUIDE.md${NC}"
    echo ""
    echo -e "${YELLOW}Key validation points to check:${NC}"
    echo "✓ All health checks passed"
    echo "✓ Normal syslog messages stored in ClickHouse"
    echo "✓ Anomaly detection working for error messages"
    echo "✓ Host metrics flowing through the pipeline"
    echo "✓ No critical errors in service logs"
    echo ""
    echo -e "${RED}If any step failed, create an issue using the template in the testing guide.${NC}"
}

# Main execution flow
main() {
    echo -e "${YELLOW}This script assists with manual testing execution.${NC}"
    echo -e "${YELLOW}It provides commands and expected outputs for validation.${NC}"
    echo -e "${YELLOW}Please execute each command manually and verify the results.${NC}"
    echo ""
    read -p "Press Enter to start the assisted testing process..."
    echo ""
    
    run_health_checks
    test_normal_syslog
    test_anomaly_detection
    test_host_metrics
    display_summary
}

# Script execution
main "$@"