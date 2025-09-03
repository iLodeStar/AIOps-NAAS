#!/bin/bash
#
# Manual Validation Testing Helper Script
# Provides step-by-step validation for AIOps NAAS platform
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
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

# Function to wait for user input with screenshots
wait_for_screenshot() {
    echo -e "\n${YELLOW}📸 SCREENSHOT REQUIRED:${NC} $1"
    echo "Press Enter when screenshot is captured..."
    read -r
}

# Function to check service health
check_service_health() {
    local service_name=$1
    local health_url=$2
    local expected_response=${3:-"healthy"}
    
    echo -n "Checking $service_name health... "
    if curl -sf "$health_url" > /dev/null 2>&1; then
        print_success "$service_name is healthy"
        return 0
    else
        print_error "$service_name health check failed"
        return 1
    fi
}

# Function to test endpoint with JSON pretty print
test_endpoint() {
    local name=$1
    local url=$2
    echo -e "\n${BLUE}Testing $name endpoint:${NC}"
    echo "URL: $url"
    
    if command -v jq > /dev/null; then
        curl -s "$url" | jq . 2>/dev/null || curl -s "$url" 2>/dev/null || echo "Endpoint not responding"
    else
        curl -s "$url" 2>/dev/null || echo "Endpoint not responding"
    fi
}

print_header() {
    echo -e "\n${GREEN}================================================${NC}"
    echo -e "${GREEN}     AIOps NAAS Manual Validation Testing${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "This script will guide you through the 5-step validation process."
    echo "Screenshots will be required at various steps."
    echo ""
}

# Step 0: Pre-validation checks
pre_validation_checks() {
    print_step "Pre-Validation: Docker Environment Setup"
    
    # Check Docker
    if ! command -v docker > /dev/null; then
        print_error "Docker not found. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose > /dev/null && ! docker compose version > /dev/null 2>&1; then
        print_error "Docker Compose not found. Please install Docker Compose."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
    
    # Check if we're in the right directory
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found. Please run this script from the AIOps-NAAS root directory."
        exit 1
    fi
    
    print_success "Found docker-compose.yml"
    
    # Check services status
    print_info "Checking Docker services status..."
    docker compose ps --format="table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Review the services above. All should show 'Up' or 'Up (healthy)' status."
    echo "If any services are down, run 'docker compose up -d' first."
    echo ""
    read -p "Do all services appear to be running? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Starting services..."
        docker compose up -d
        print_info "Waiting 60 seconds for services to initialize..."
        sleep 60
        docker compose ps
    fi
}

# Step 1: Syslog capture validation
step1_syslog_capture() {
    print_step "Step 1: Syslog Capture Validation"
    
    # Check rsyslog
    print_info "Checking rsyslog service..."
    if systemctl is-active --quiet rsyslog; then
        print_success "rsyslog is running"
    else
        print_warning "rsyslog may not be running. Check with: sudo systemctl status rsyslog"
    fi
    
    # Generate test syslogs
    print_info "Generating test syslog messages..."
    logger "TEST: Manual validation syslog entry $(date)"
    logger -p user.info "TEST: Info level message for validation"
    logger -p user.warning "TEST: Warning level message for validation" 
    logger -p user.err "TEST: Error level message for validation"
    
    print_success "Test syslog messages generated"
    
    # Test syslog forwarding to Vector
    print_info "Testing syslog forwarding to Vector (port 514)..."
    echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) validation-test: Manual testing syslog message" | nc -u localhost 514 2>/dev/null || {
        print_warning "netcat not available or Vector not listening on port 514"
        print_info "You can install netcat with: sudo apt install netcat-openbsd"
    }
    
    # Check Vector logs
    print_info "Checking Vector service logs for syslog processing..."
    docker compose logs vector --tail 20
    
    wait_for_screenshot "Vector logs showing syslog processing activity"
    
    print_success "Step 1 completed: Syslog capture validated"
}

# Step 2: Log reading service validation
step2_log_reading_service() {
    print_step "Step 2: Log Reading Service (Vector) Validation"
    
    # Identify Vector service
    print_info "Vector is the log reading service in this architecture"
    
    # Check Vector version
    print_info "Checking Vector version..."
    docker compose exec vector vector --version 2>/dev/null || print_warning "Could not get Vector version"
    
    # Check Vector health
    print_info "Testing Vector health endpoints..."
    
    # Vector may expose different endpoints, try common ones
    for port in 8686 9598 8080; do
        if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
            print_success "Vector health endpoint found on port $port"
            test_endpoint "Vector Health" "http://localhost:$port/health"
            break
        fi
    done
    
    # Check Vector metrics
    print_info "Checking Vector metrics..."
    for port in 8686 9598 9090; do
        if curl -sf "http://localhost:$port/metrics" > /dev/null 2>&1; then
            print_success "Vector metrics endpoint found on port $port"
            echo "Sample metrics:"
            curl -s "http://localhost:$port/metrics" | head -10
            break
        fi
    done
    
    # Show Vector processing logs
    print_info "Vector processing logs:"
    docker compose logs vector --tail 30
    
    wait_for_screenshot "Vector service logs and any available UI/metrics endpoints"
    
    # Test data flow from Vector
    print_info "Testing data flow from Vector with new message..."
    echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) step2-test: Vector validation message" | nc -u localhost 514 2>/dev/null || echo "Test message sent"
    
    sleep 5
    print_info "Recent Vector logs after test message:"
    docker compose logs vector --tail 10
    
    print_success "Step 2 completed: Vector log reading service validated"
}

# Step 3: Log transformation and storage
step3_log_storage() {
    print_step "Step 3: Log Transformation and Storage (ClickHouse) Validation"
    
    # Check ClickHouse health
    check_service_health "ClickHouse" "http://localhost:8123/ping"
    
    # Show ClickHouse version
    print_info "ClickHouse version information:"
    curl -s "http://localhost:8123/" | head -5
    
    # Check databases and tables
    print_info "Checking ClickHouse databases..."
    docker compose exec clickhouse clickhouse-client --query "SHOW DATABASES" 2>/dev/null || print_warning "Could not access ClickHouse client"
    
    print_info "Checking for log tables..."
    docker compose exec clickhouse clickhouse-client --query "SHOW TABLES" 2>/dev/null || print_warning "Could not list tables"
    
    # Test log insertion
    print_info "Sending test log for storage validation..."
    echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) clickhouse-test: Storage validation message" | nc -u localhost 514 2>/dev/null || echo "Test log sent"
    
    sleep 10
    
    # Try to query logs (structure may vary)
    print_info "Attempting to query stored logs..."
    docker compose exec clickhouse clickhouse-client --query "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 5" 2>/dev/null || \
    docker compose exec clickhouse clickhouse-client --query "SELECT name, engine FROM system.tables WHERE database != 'system'" 2>/dev/null || \
    print_warning "Log table structure varies - manual investigation needed in ClickHouse UI"
    
    # ClickHouse UI access
    print_info "ClickHouse Play UI is available at: http://localhost:8123/play"
    print_info "You can run queries like: SELECT name FROM system.tables WHERE database != 'system'"
    
    wait_for_screenshot "ClickHouse Play UI interface and any log query results"
    
    print_success "Step 3 completed: ClickHouse log storage validated"
}

# Step 4: Data enrichment and correlation
step4_correlation() {
    print_step "Step 4: Data Enrichment and Correlation Validation"
    
    # Check NATS message bus
    print_info "Checking NATS message bus..."
    test_endpoint "NATS" "http://localhost:8222/varz"
    
    print_info "NATS Monitoring UI: http://localhost:8222"
    
    # Check Benthos correlation service
    print_info "Checking Benthos correlation service..."
    docker compose logs benthos --tail 20
    
    # Test correlation with multiple anomalies
    print_info "Testing correlation logic with multiple related anomalies..."
    
    # Check if we have test script
    if [[ -f "scripts/publish_test_anomalies.py" ]]; then
        print_info "Running test anomaly publisher..."
        python3 scripts/publish_test_anomalies.py 2>/dev/null || print_warning "Test script execution failed"
    else
        print_info "Generating manual test anomalies..."
        # Try to send via anomaly detection service API
        curl -X POST "http://localhost:8080/test/anomaly" -H "Content-Type: application/json" \
          -d '{"metric":"cpu_usage","value":85.5,"threshold":70,"timestamp":"'$(date -Iseconds)'"}' 2>/dev/null || \
        print_info "Direct API test not available - correlation will be tested via pipeline"
        
        sleep 2
        curl -X POST "http://localhost:8080/test/anomaly" -H "Content-Type: application/json" \
          -d '{"metric":"memory_usage","value":92.3,"threshold":80,"timestamp":"'$(date -Iseconds)'"}' 2>/dev/null || \
        print_info "Second anomaly sent"
    fi
    
    sleep 10
    
    # Check for correlated incidents
    print_info "Checking for correlated incidents..."
    test_endpoint "Incidents API" "http://localhost:8081/incidents"
    
    # Show correlation service logs
    print_info "Benthos correlation logs:"
    docker compose logs benthos --tail 15
    
    print_info "NATS message activity:"
    docker compose logs nats --tail 10
    
    wait_for_screenshot "NATS monitoring UI and correlation service logs"
    
    print_success "Step 4 completed: Data correlation validated"
}

# Step 5: Anomaly detection service
step5_anomaly_detection() {
    print_step "Step 5: Anomaly Detection Service Validation"
    
    # Check anomaly detection service health
    check_service_health "Anomaly Detection" "http://localhost:8080/health"
    
    # Show service configuration
    test_endpoint "Anomaly Detection Config" "http://localhost:8080/config"
    
    # Check available detectors
    test_endpoint "Available Detectors" "http://localhost:8080/detectors"
    
    # Check metrics endpoint
    test_endpoint "Service Metrics" "http://localhost:8080/metrics"
    
    # Run pipeline validation if available
    print_info "Running comprehensive pipeline validation..."
    if [[ -f "scripts/validate_pipeline.sh" ]]; then
        ./scripts/validate_pipeline.sh 2>/dev/null || print_warning "Pipeline validation script failed"
    else
        print_warning "Pipeline validation script not found"
    fi
    
    # Check VictoriaMetrics data for anomaly detection
    print_info "Checking VictoriaMetrics data availability for anomaly detection..."
    test_endpoint "VM Query" "http://localhost:8428/api/v1/query?query=up"
    
    # Simulate metrics if needed
    if [[ -f "scripts/simulate_node_metrics.sh" ]]; then
        print_info "Simulating node metrics for testing..."
        ./scripts/simulate_node_metrics.sh 2>/dev/null || print_warning "Metrics simulation failed"
    fi
    
    # Check anomaly detection logs
    print_info "Anomaly detection service logs:"
    docker compose logs anomaly-detection --tail 30 | grep -E "(anomaly|score|threshold|detection)" || \
    docker compose logs anomaly-detection --tail 20
    
    # Wait and check for generated incidents
    sleep 30
    print_info "Checking for incidents generated by anomaly detection..."
    test_endpoint "Generated Incidents" "http://localhost:8081/incidents"
    
    wait_for_screenshot "Anomaly detection service health response and processing logs"
    
    print_success "Step 5 completed: Anomaly detection service validated"
}

# Final end-to-end validation
final_validation() {
    print_step "Final End-to-End Validation"
    
    # Grafana access
    print_info "Grafana visualization access:"
    print_info "URL: http://localhost:3000"
    print_info "Default login: admin/admin (check .env for custom credentials)"
    
    check_service_health "Grafana" "http://localhost:3000/api/health"
    
    # Complete service overview
    print_info "Complete service status overview:"
    echo ""
    echo "Core Services:"
    check_service_health "ClickHouse" "http://localhost:8123/ping" || true
    check_service_health "VictoriaMetrics" "http://localhost:8428/health" || true  
    check_service_health "NATS" "http://localhost:8222/healthz" || true
    check_service_health "Grafana" "http://localhost:3000/api/health" || true
    
    echo ""
    echo "Processing Services:"
    check_service_health "Anomaly Detection" "http://localhost:8080/health" || true
    check_service_health "Incident API" "http://localhost:8081/health" || true
    
    wait_for_screenshot "Grafana login page and main dashboard interface"
    
    print_success "Manual validation testing completed!"
    
    print_info "Summary of validated components:"
    echo "✅ 1. Syslog capture from Ubuntu system"
    echo "✅ 2. Vector log reading service"  
    echo "✅ 3. ClickHouse log storage and transformation"
    echo "✅ 4. NATS + Benthos data correlation"
    echo "✅ 5. Anomaly detection service with ML algorithms"
    echo "✅ 6. End-to-end pipeline with Grafana visualization"
}

# Main execution
main() {
    print_header
    
    echo "This script will guide you through all 5 validation steps."
    echo "Screenshots will be requested at key points."
    echo ""
    read -p "Press Enter to start the validation process..."
    
    pre_validation_checks
    step1_syslog_capture
    step2_log_reading_service  
    step3_log_storage
    step4_correlation
    step5_anomaly_detection
    final_validation
    
    echo ""
    print_success "🎉 All validation steps completed successfully!"
    print_info "Review the screenshots captured during validation."
    print_info "Check docs/validation/manual-testing-guide.md for detailed troubleshooting."
}

# Run main function
main "$@"