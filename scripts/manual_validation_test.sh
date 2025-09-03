#!/bin/bash
#
# End-to-End Manual Validation Testing Helper Script
# Provides step-by-step message tracking validation for AIOps NAAS platform
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Generate unique tracking ID for this session
TRACKING_ID="E2E-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

print_header() {
    echo -e "\n${PURPLE}=============================================${NC}"
    echo -e "${PURPLE} AIOps NAAS End-to-End Validation Testing${NC}"
    echo -e "${PURPLE}=============================================${NC}"
    echo -e "${BLUE}TRACKING ID: $TRACKING_ID${NC}"
    echo -e "${BLUE}Use this ID to track your test message through all components${NC}"
    echo -e "${PURPLE}=============================================${NC}\n"
}

print_step() {
    echo -e "\n${BLUE}=== STEP $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_command() {
    echo -e "${PURPLE}Command:${NC} $1"
}

# Function to wait for user input with screenshots
wait_for_screenshot() {
    echo -e "\n${YELLOW}📸 SCREENSHOT REQUIRED:${NC} $1"
    echo "Press Enter when screenshot is captured..."
    read -r
}

# Function to wait for user confirmation
wait_for_confirmation() {
    echo -e "\n${BLUE}$1${NC}"
    echo "Press Enter to continue..."
    read -r
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_step "PRE-VALIDATION: Prerequisites Check"
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker not found. Please install Docker first."
        exit 1
    fi
    print_success "Docker is installed"
    
    # Check Docker Compose
    if ! command_exists docker-compose && ! docker compose version > /dev/null 2>&1; then
        print_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    print_success "Docker Compose is available"
    
    # Check netcat
    if ! command_exists nc; then
        print_error "netcat (nc) not found. Please install netcat for syslog testing."
        exit 1
    fi
    print_success "netcat is available for syslog testing"
    
    # Check if in right directory
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found. Please run this script from the AIOps-NAAS root directory."
        exit 1
    fi
    print_success "Found docker-compose.yml in current directory"
}

# Validate service health
validate_services() {
    print_step "PRE-VALIDATION: Service Health Check"
    
    print_info "Checking all Docker services..."
    docker compose ps --format="table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    
    echo -e "\n${BLUE}Key services that must be healthy:${NC}"
    echo "- aiops-vector (ports 8686, 1514)"
    echo "- aiops-clickhouse (ports 8123, 9000)" 
    echo "- aiops-nats (ports 4222, 8222)"
    echo "- aiops-benthos (port 4195)"
    echo "- aiops-anomaly-detection (port 8080)"
    
    wait_for_confirmation "Review the service status above. If any critical services are down, restart them with 'docker compose up -d [service-name]'"
}

# Step 1: Send and track normal message
step1_normal_message() {
    print_step "1: Send Normal Test Message & Track Vector Processing"
    
    echo -e "${BLUE}Objective:${NC} Send a uniquely identifiable test message and verify Vector receives and processes it."
    echo -e "${BLUE}Tracking ID:${NC} $TRACKING_ID"
    
    print_info "Sending NORMAL message to Vector syslog port (1514)..."
    
    print_command "echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) validation-test: NORMAL $TRACKING_ID System operational, all services running\" | nc -u localhost 1514"
    
    # Send the message
    echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) validation-test: NORMAL $TRACKING_ID System operational, all services running" | nc -u localhost 1514
    
    print_success "Normal test message sent with tracking ID: $TRACKING_ID"
    
    # Wait for processing
    sleep 5
    
    print_info "Checking Vector logs for your message..."
    print_command "docker compose logs vector --tail 50 | grep \"$TRACKING_ID\""
    
    if docker compose logs vector --tail 50 | grep "$TRACKING_ID" > /dev/null; then
        print_success "Message found in Vector logs!"
        docker compose logs vector --tail 50 | grep "$TRACKING_ID"
    else
        print_warning "Message not immediately visible in Vector logs - this may be normal"
    fi
    
    # Check Vector health
    print_info "Checking Vector health and metrics..."
    if curl -sf http://localhost:8686/health > /dev/null; then
        print_success "Vector health check passed"
    else
        print_warning "Vector health endpoint not responding"
    fi
    
    # Check Vector port
    print_info "Verifying Vector is listening on syslog port 1514..."
    if netstat -ulnp 2>/dev/null | grep 1514 > /dev/null || ss -ulnp 2>/dev/null | grep 1514 > /dev/null; then
        print_success "Vector is listening on port 1514"
    else
        print_warning "Cannot confirm Vector is listening on port 1514"
    fi
    
    wait_for_screenshot "Screenshot of Vector logs showing your TRACKING_ID message processing"
}

# Step 2: Track message in ClickHouse
step2_clickhouse_storage() {
    print_step "2: Track Message Storage in ClickHouse"
    
    echo -e "${BLUE}Objective:${NC} Verify your test message was transformed and stored in ClickHouse logs.raw table."
    
    print_info "Waiting additional 10 seconds for message processing..."
    sleep 10
    
    print_info "Querying ClickHouse for your specific message..."
    print_command "docker compose exec clickhouse clickhouse-client --query \"SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 5\""
    
    if docker compose exec clickhouse clickhouse-client --query "SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 5" 2>/dev/null; then
        print_success "Message found in ClickHouse!"
    else
        print_error "Message not found in ClickHouse - checking connection..."
        if curl -sf http://localhost:8123/ping > /dev/null; then
            print_info "ClickHouse is responding - message may still be processing"
        else
            print_error "ClickHouse health check failed"
        fi
    fi
    
    print_info "Checking ClickHouse Play UI access..."
    echo -e "${BLUE}ClickHouse Play UI:${NC} http://localhost:8123/play"
    echo -e "${BLUE}Credentials:${NC} default/clickhouse123"
    echo -e "${BLUE}Test Query:${NC} SELECT * FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 1"
    
    wait_for_screenshot "Screenshot of ClickHouse Play UI showing your TRACKING_ID message in the query results"
}

# Step 3: Send anomaly message and track
step3_anomaly_detection() {
    print_step "3: Simulate Anomaly Detection Path"
    
    echo -e "${BLUE}Objective:${NC} Generate an anomaly message, track it through VictoriaMetrics and verify anomaly detection."
    
    print_info "Sending ANOMALY message to simulate high CPU usage..."
    print_command "echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) cpu-monitor: ANOMALY $TRACKING_ID CPU usage critical at 98% - threshold exceeded\" | nc -u localhost 1514"
    
    # Send anomaly message
    echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) cpu-monitor: ANOMALY $TRACKING_ID CPU usage critical at 98% - threshold exceeded" | nc -u localhost 1514
    
    print_success "Anomaly message sent with tracking ID: $TRACKING_ID"
    sleep 10
    
    print_info "Verifying anomaly message in ClickHouse..."
    if docker compose exec clickhouse clickhouse-client --query "SELECT timestamp, message, source, service FROM logs.raw WHERE message LIKE '%ANOMALY%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 1" 2>/dev/null; then
        print_success "Anomaly message found in ClickHouse!"
    else
        print_warning "Anomaly message not yet visible in ClickHouse"
    fi
    
    print_info "Checking VictoriaMetrics for metric data..."
    if curl -s "http://localhost:8428/api/v1/query?query=up" | grep -q "success"; then
        print_success "VictoriaMetrics is responding with metric data"
    else
        print_warning "VictoriaMetrics not responding or no metrics available"
    fi
    
    print_info "Checking anomaly detection service..."
    if curl -sf http://localhost:8080/health > /dev/null; then
        print_success "Anomaly detection service is healthy"
        docker compose logs anomaly-detection --tail 10
    else
        print_warning "Anomaly detection service not responding"
    fi
}

# Step 4: Track NATS message bus
step4_nats_messaging() {
    print_step "4: Track Messages Through NATS Message Bus"
    
    echo -e "${BLUE}Objective:${NC} Monitor NATS for anomaly events and verify message bus functionality."
    
    print_info "Checking NATS server statistics..."
    if curl -sf http://localhost:8222/varz > /dev/null; then
        print_success "NATS monitoring interface is accessible"
        curl -s http://localhost:8222/varz | grep -E "(connections|in_msgs|out_msgs)" | head -5
    else
        print_warning "NATS monitoring interface not responding"
    fi
    
    print_info "Checking NATS subscriptions and topics..."
    if curl -sf http://localhost:8222/subsz > /dev/null; then
        print_success "NATS subscriptions endpoint accessible"
        echo -e "${BLUE}Expected subjects should include:${NC}"
        echo "- anomaly.detected"
        echo "- anomaly.detected.enriched" 
        echo "- incidents.created"
    else
        print_warning "NATS subscriptions endpoint not responding"
    fi
    
    print_info "NATS Monitoring UI: http://localhost:8222"
    
    wait_for_screenshot "Screenshot of NATS monitoring UI at http://localhost:8222 showing message activity"
}

# Step 5: Benthos correlation and incidents
step5_benthos_correlation() {
    print_step "5: Validate Benthos Event Correlation & Incident Creation"
    
    echo -e "${BLUE}Objective:${NC} Verify Benthos processes NATS messages, applies correlation rules, and creates incidents."
    
    print_info "Checking Benthos health and configuration..."
    if curl -sf http://localhost:4195/ping > /dev/null; then
        print_success "Benthos is responding to health checks"
    else
        print_warning "Benthos health check failed"
    fi
    
    print_info "Checking Benthos processing statistics..."
    if curl -sf http://localhost:4195/stats > /dev/null; then
        print_success "Benthos stats endpoint accessible"
        if command_exists jq; then
            curl -s http://localhost:4195/stats | jq '{input: .input, output: .output, processor: .processor}' 2>/dev/null || curl -s http://localhost:4195/stats
        else
            curl -s http://localhost:4195/stats
        fi
    else
        print_warning "Benthos stats endpoint not responding"
    fi
    
    print_info "Checking Benthos logs for correlation activity..."
    if docker compose logs benthos --tail 20 | grep -E "(correlation|incident|anomaly)" > /dev/null; then
        print_success "Found correlation activity in Benthos logs"
        docker compose logs benthos --tail 20 | grep -E "(correlation|incident|anomaly)"
    else
        print_warning "No correlation activity found in recent Benthos logs"
    fi
    
    print_info "Monitoring for incident creation..."
    echo -e "${BLUE}Expected to see:${NC}"
    echo "- incident_id, incident_type, incident_severity"
    echo "- correlation_id, processing_timestamp"
    echo "- suggested_runbooks array"
    
    if docker compose logs benthos --tail 30 | grep -E "(incident_created|event_type.*incident)" > /dev/null; then
        print_success "Found incident creation activity!"
        docker compose logs benthos --tail 30 | grep -E "(incident_created|event_type.*incident)"
    else
        print_warning "No recent incident creation activity found"
    fi
    
    wait_for_screenshot "Screenshot of Benthos logs showing incident creation with correlation details"
}

# Summary and completion
validation_summary() {
    print_step "VALIDATION SUMMARY"
    
    echo -e "${PURPLE}=============================================${NC}"
    echo -e "${PURPLE} End-to-End Validation Complete${NC}"
    echo -e "${PURPLE}=============================================${NC}"
    echo -e "${BLUE}Tracking ID Used: $TRACKING_ID${NC}"
    echo -e "${PURPLE}=============================================${NC}"
    
    echo -e "\n${BLUE}Validation Checklist:${NC}"
    echo "□ Step 1: Normal message tracked through Vector to ClickHouse"
    echo "□ Step 2: Message found in ClickHouse logs.raw table with proper transformation"
    echo "□ Step 3: Anomaly message processed and stored"
    echo "□ Step 4: NATS message bus showed activity and proper topic subscriptions" 
    echo "□ Step 5: Benthos processed messages and created incidents"
    echo "□ All required screenshots captured and documented"
    
    echo -e "\n${BLUE}Message Flow Demonstrated:${NC}"
    echo -e "${GREEN}Normal Path:${NC} Syslog → Vector → ClickHouse → End"
    echo -e "${YELLOW}Anomaly Path:${NC} Syslog → Vector → ClickHouse → VictoriaMetrics → Anomaly Detection → NATS → Benthos → Incidents"
    
    echo -e "\n${BLUE}Key Data Points Tracked:${NC}"
    echo "- Unique tracking ID: $TRACKING_ID"
    echo "- Normal operational message processing"
    echo "- Anomaly detection and correlation pipeline"
    echo "- Message transformation at each stage"
    echo "- Service health and connectivity validation"
    
    wait_for_confirmation "Review the checklist above and mark completed items. Press Enter to finish."
}

# Main execution flow
main() {
    print_header
    
    check_prerequisites
    validate_services
    
    step1_normal_message
    step2_clickhouse_storage  
    step3_anomaly_detection
    step4_nats_messaging
    step5_benthos_correlation
    
    validation_summary
    
    print_success "End-to-End Manual Validation Testing Complete!"
    echo -e "${BLUE}For troubleshooting, refer to docs/validation/manual-testing-guide.md${NC}"
}

# Run main function
main "$@"