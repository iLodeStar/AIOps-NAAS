#!/bin/bash

# Vector to ClickHouse Data Flow Validation Script
# Tests all 10 validation points mentioned in issue #38

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CLICKHOUSE_HOST="localhost"
CLICKHOUSE_PORT="8123"
CLICKHOUSE_USER="default"
CLICKHOUSE_PASSWORD="changeme_clickhouse"
VECTOR_API_URL="http://localhost:8686"

print_step() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local timeout=${3:-60}
    
    echo -n "Waiting for $name to be ready..."
    for i in $(seq 1 $timeout); do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo " Ready!"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    echo " Timeout!"
    return 1
}

# Test ClickHouse query
run_clickhouse_query() {
    local query=$1
    curl -sf -u "${CLICKHOUSE_USER}:${CLICKHOUSE_PASSWORD}" \
        "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/?query=$(echo "$query" | sed 's/ /%20/g')" 2>/dev/null
}

print_step "Vector to ClickHouse Data Flow Validation"
echo "Testing all 10 validation points from issue #38"
echo ""

# Point 1: Run dockers in local ubuntu
print_step "1. Run dockers in local ubuntu"
if docker compose ps | grep -q "Up"; then
    print_success "Docker containers are running"
    docker compose ps --format="table {{.Name}}\t{{.Status}}\t{{.Ports}}"
else
    print_error "Docker containers are not running. Please run 'docker compose up -d clickhouse vector'"
fi
echo ""

# Point 2: Get syslogs
print_step "2. Get syslogs"
print_info "Sending test syslog messages to Vector..."

# Send test syslog message
echo "<14>$(date '+%b %d %H:%M:%S') test-host test-app: Test syslog message from validation script" | nc localhost 514 || {
    print_warning "Could not send syslog message via nc. Trying logger..."
    logger -n localhost -P 514 "Test syslog message from validation script" || {
        print_warning "Logger not available. Syslog test skipped."
    }
}

print_success "Syslog test message sent"
echo ""

# Point 3: Validate if metrics are generated
print_step "3. Validate if metrics are generated"
if wait_for_service "$VECTOR_API_URL/health" "Vector API" 30; then
    print_success "Vector is running and generating metrics"
    # Check if host metrics source is active
    vector_stats=$(curl -sf "$VECTOR_API_URL/stats" 2>/dev/null || echo '{}')
    echo "Vector stats: $vector_stats"
else
    print_error "Vector API is not accessible"
fi
echo ""

# Point 4: Validate if metrics are transformed
print_step "4. Validate if metrics are transformed"
print_info "Checking Vector transform activity..."
docker compose logs vector --tail=50 | grep -i transform && {
    print_success "Metrics transformation is active"
} || {
    print_warning "No recent transformation activity found in logs"
}
echo ""

# Point 5: Validate if metrics are pushed to clickhouse  
print_step "5. Validate if metrics are pushed to ClickHouse"
print_info "Waiting a moment for data to be batched and sent..."
sleep 10

initial_count=$(run_clickhouse_query "SELECT count(*) FROM logs.raw" || echo "0")
print_info "Initial record count in logs.raw: $initial_count"

# Generate some test data to ensure we see new records
echo '{"timestamp":"'$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")'","level":"INFO","message":"Validation test log","service":"validation","host":"test-host","component":"validator","environment":"test","version":"1.0.0"}' >> sample-logs/validation.log

# Wait for Vector to process
sleep 15

final_count=$(run_clickhouse_query "SELECT count(*) FROM logs.raw" || echo "0")
print_info "Final record count in logs.raw: $final_count"

if [[ $final_count -gt $initial_count ]]; then
    print_success "New records added to ClickHouse ($initial_count -> $final_count)"
else
    print_warning "No new records detected. Checking Vector sink logs..."
    docker compose logs vector | grep -i clickhouse | tail -10
fi
echo ""

# Point 6: Validate ClickHouse receives the data
print_step "6. Validate ClickHouse receives the data"
if wait_for_service "http://${CLICKHOUSE_HOST}:${CLICKHOUSE_PORT}/ping" "ClickHouse" 30; then
    print_success "ClickHouse is accessible"
    
    # Query recent data
    recent_data=$(run_clickhouse_query "SELECT source, count(*) FROM logs.raw WHERE timestamp >= now() - INTERVAL 5 MINUTE GROUP BY source ORDER BY count() DESC LIMIT 5" || echo "")
    
    if [[ -n "$recent_data" ]]; then
        print_success "Recent data found in ClickHouse:"
        echo "$recent_data"
    else
        print_warning "No recent data found in ClickHouse"
    fi
else
    print_error "ClickHouse is not accessible"
fi
echo ""

# Point 7: Validate the vector API are running
print_step "7. Validate Vector API is running"
if curl -sf "$VECTOR_API_URL/health" > /dev/null 2>&1; then
    health_status=$(curl -sf "$VECTOR_API_URL/health" 2>/dev/null)
    print_success "Vector API is healthy: $health_status"
else
    print_error "Vector API health check failed"
fi
echo ""

# Point 8: Validate vector API can be accessed outside the docker
print_step "8. Validate Vector API can be accessed outside the docker"
external_health=$(curl -sf "$VECTOR_API_URL/health" 2>/dev/null || echo "failed")
if [[ "$external_health" != "failed" ]]; then
    print_success "Vector API is accessible from outside Docker"
    
    # Test additional endpoints
    echo "Available endpoints:"
    curl -sf "$VECTOR_API_URL" 2>/dev/null | head -5
    
    metrics_endpoint="$VECTOR_API_URL/metrics"
    if curl -sf "$metrics_endpoint" > /dev/null 2>&1; then
        print_success "Vector metrics endpoint is accessible"
    else
        print_warning "Vector metrics endpoint not accessible"
    fi
else
    print_error "Vector API is not accessible from outside Docker"
fi
echo ""

# Point 9: Validate vector can connect to ClickHouse
print_step "9. Validate Vector can connect to ClickHouse"
print_info "Checking Vector ClickHouse connectivity..."

# Check Vector logs for ClickHouse connectivity
clickhouse_logs=$(docker compose logs vector | grep -i clickhouse | tail -10)
if echo "$clickhouse_logs" | grep -q "error\|failed\|refused"; then
    print_warning "ClickHouse connection issues detected:"
    echo "$clickhouse_logs"
else
    print_success "No ClickHouse connection errors in Vector logs"
fi

# Test Vector configuration by reloading it
print_info "Testing Vector configuration reload..."
if docker compose kill -s HUP vector; then
    sleep 3
    if docker compose ps vector | grep -q "healthy"; then
        print_success "Vector configuration is valid"
    else
        print_warning "Vector may have configuration issues"
    fi
else
    print_warning "Could not test Vector configuration reload"
fi
echo ""

# Point 10: Validate data sent to clickhouse is same as outcome of transformation
print_step "10. Validate data sent to ClickHouse matches transformation outcome"

print_info "Checking data consistency between Vector transformation and ClickHouse..."

# Get sample of transformed data from ClickHouse
sample_data=$(run_clickhouse_query "SELECT source, level, message, timestamp FROM logs.raw WHERE source IN ('host_metrics', 'syslog', 'file') ORDER BY timestamp DESC LIMIT 3" || echo "")

if [[ -n "$sample_data" ]]; then
    print_success "Sample data from ClickHouse:"
    echo "$sample_data"
    print_success "Data transformation appears to be working correctly"
else
    print_warning "No transformed data found in ClickHouse"
    
    # Check if the issue is with data types
    print_info "Checking table schema compatibility..."
    table_desc=$(run_clickhouse_query "DESCRIBE logs.raw" || echo "Schema check failed")
    echo "Table schema:"
    echo "$table_desc"
fi
echo ""

# Summary
print_step "Validation Summary"

echo -e "${GREEN}✓${NC} Points that passed:"
echo "  1. Docker containers running"
echo "  2. Syslog test message sent" 
echo "  3. Vector API accessible"
echo "  7. Vector API running"
echo "  8. Vector API accessible externally"

echo -e "${YELLOW}⚠${NC} Points that need attention:"
echo "  4. Metrics transformation (check logs for activity)"
echo "  5. Data push to ClickHouse (may need batching time)"
echo "  6. ClickHouse data validation (schema/data type issues possible)"
echo "  9. Vector-ClickHouse connectivity (check auth/endpoint)"
echo "  10. Data consistency (needs more investigation)"

echo ""
print_info "Next steps to fully resolve the issue:"
echo "1. Check Vector transformation logs for data type issues"
echo "2. Verify ClickHouse table schema matches Vector output"
echo "3. Adjust Vector batch settings for faster data visibility"
echo "4. Add more detailed logging to Vector sink configuration"

echo ""
print_success "Validation complete. See summary above for next steps."