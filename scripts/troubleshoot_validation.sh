#!/bin/bash
#
# AIOps NAAS Troubleshooting Script
# Diagnoses common issues in the validation pipeline
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_section() {
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

# Check system resources
check_system_resources() {
    print_section "System Resources Check"
    
    # Memory check
    local mem_total=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    local mem_used=$(free -m | awk 'NR==2{printf "%.0f", $3}')
    local mem_percent=$((mem_used * 100 / mem_total))
    
    echo "Memory: ${mem_used}MB / ${mem_total}MB (${mem_percent}%)"
    if [[ $mem_percent -gt 90 ]]; then
        print_error "High memory usage detected"
    elif [[ $mem_percent -gt 75 ]]; then
        print_warning "Memory usage is high"
    else
        print_success "Memory usage is acceptable"
    fi
    
    # Disk space check
    local disk_usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
    echo "Disk usage: ${disk_usage}%"
    if [[ $disk_usage -gt 90 ]]; then
        print_error "Low disk space"
    elif [[ $disk_usage -gt 80 ]]; then
        print_warning "Disk space is getting low"
    else
        print_success "Disk space is sufficient"
    fi
    
    # Docker space check
    print_info "Docker system usage:"
    docker system df
}

# Check Docker environment
check_docker_environment() {
    print_section "Docker Environment Check"
    
    # Docker daemon
    if docker info > /dev/null 2>&1; then
        print_success "Docker daemon is running"
    else
        print_error "Docker daemon is not accessible"
        echo "Try: sudo systemctl start docker"
        return 1
    fi
    
    # Docker compose version
    if docker compose version > /dev/null 2>&1; then
        print_success "Docker Compose is available"
        docker compose version
    elif docker-compose --version > /dev/null 2>&1; then
        print_success "Docker Compose (legacy) is available"
        docker-compose --version
    else
        print_error "Docker Compose not found"
        return 1
    fi
    
    # Check for docker-compose.yml
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found in current directory"
        echo "Make sure you're in the AIOps-NAAS root directory"
        return 1
    else
        print_success "docker-compose.yml found"
    fi
}

# Check service status
check_service_status() {
    print_section "Service Status Check"
    
    echo "Current service status:"
    docker compose ps --format="table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    
    echo -e "\nDetailed health checks:"
    
    # Define services with their health endpoints
    declare -A services=(
        ["clickhouse"]="http://localhost:8123/ping"
        ["victoria-metrics"]="http://localhost:8428/health"
        ["grafana"]="http://localhost:3000/api/health"
        ["nats"]="http://localhost:8222/healthz"
        ["anomaly-detection"]="http://localhost:8080/health"
        ["incident-api"]="http://localhost:8081/health"
    )
    
    local failed_services=()
    
    for service in "${!services[@]}"; do
        local url="${services[$service]}"
        echo -n "Checking $service... "
        
        if curl -sf "$url" > /dev/null 2>&1; then
            print_success "$service is healthy"
        else
            print_error "$service health check failed"
            failed_services+=("$service")
        fi
    done
    
    if [[ ${#failed_services[@]} -gt 0 ]]; then
        echo -e "\n${YELLOW}Failed services detected. Checking logs:${NC}"
        for service in "${failed_services[@]}"; do
            echo -e "\n--- $service logs ---"
            docker compose logs "$service" --tail 10 || echo "Could not retrieve logs for $service"
        done
    fi
}

# Check network connectivity
check_network_connectivity() {
    print_section "Network Connectivity Check"
    
    # Check if ports are listening
    local ports=(8123 8428 3000 8222 8080 8081)
    
    for port in "${ports[@]}"; do
        if netstat -ln 2>/dev/null | grep -q ":$port "; then
            print_success "Port $port is listening"
        else
            if ss -ln 2>/dev/null | grep -q ":$port "; then
                print_success "Port $port is listening"
            else
                print_warning "Port $port is not listening"
            fi
        fi
    done
    
    # Test internal Docker network
    print_info "Testing Docker network connectivity..."
    if docker compose exec clickhouse ping -c 1 victoria-metrics > /dev/null 2>&1; then
        print_success "Internal Docker network is working"
    else
        print_warning "Internal Docker network connectivity issues detected"
    fi
}

# Check data flow
check_data_flow() {
    print_section "Data Flow Check"
    
    # Check if VictoriaMetrics has data
    print_info "Checking VictoriaMetrics data availability..."
    local vm_data=$(curl -s "http://localhost:8428/api/v1/query?query=up" 2>/dev/null)
    if echo "$vm_data" | grep -q '"result":\s*\[.*\]' && [[ $(echo "$vm_data" | jq '.data.result | length' 2>/dev/null) -gt 0 ]]; then
        print_success "VictoriaMetrics has metric data"
    else
        print_warning "VictoriaMetrics appears to have no metric data"
        echo "Try running: ./scripts/simulate_node_metrics.sh"
    fi
    
    # Check ClickHouse for logs
    print_info "Checking ClickHouse for log data..."
    if docker compose exec clickhouse clickhouse-client --query "SHOW TABLES" 2>/dev/null | grep -q "logs\|events"; then
        print_success "ClickHouse has log tables"
    else
        print_warning "ClickHouse log tables not found or not accessible"
    fi
    
    # Check NATS message flow
    print_info "Checking NATS message activity..."
    local nats_stats=$(curl -s "http://localhost:8222/varz" 2>/dev/null)
    if echo "$nats_stats" | grep -q "in_msgs"; then
        local in_msgs=$(echo "$nats_stats" | jq '.in_msgs' 2>/dev/null || echo "0")
        local out_msgs=$(echo "$nats_stats" | jq '.out_msgs' 2>/dev/null || echo "0")
        if [[ $in_msgs -gt 0 || $out_msgs -gt 0 ]]; then
            print_success "NATS has message activity (in: $in_msgs, out: $out_msgs)"
        else
            print_warning "NATS shows no message activity"
        fi
    else
        print_warning "Could not retrieve NATS statistics"
    fi
    
    # Check for incidents
    print_info "Checking for generated incidents..."
    local incidents=$(curl -s "http://localhost:8081/incidents" 2>/dev/null)
    if echo "$incidents" | jq '. | length' 2>/dev/null | grep -q "^[1-9]"; then
        local count=$(echo "$incidents" | jq '. | length' 2>/dev/null)
        print_success "Found $count incidents in the system"
    else
        print_warning "No incidents found - may indicate pipeline is not processing anomalies"
    fi
}

# Generate diagnostic report
generate_diagnostic_report() {
    print_section "Generating Diagnostic Report"
    
    local report_file="diagnostic_report_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "AIOps NAAS Diagnostic Report"
        echo "Generated: $(date)"
        echo "========================================="
        echo
        
        echo "System Information:"
        uname -a
        echo
        
        echo "Docker Version:"
        docker --version
        docker compose version 2>/dev/null || docker-compose --version
        echo
        
        echo "System Resources:"
        free -h
        df -h
        echo
        
        echo "Docker Resources:"
        docker system df
        echo
        
        echo "Service Status:"
        docker compose ps
        echo
        
        echo "Port Status:"
        netstat -ln 2>/dev/null | grep -E ":(8123|8428|3000|8222|8080|8081) " || \
        ss -ln | grep -E ":(8123|8428|3000|8222|8080|8081) "
        echo
        
        echo "Recent Service Logs:"
        for service in clickhouse victoria-metrics anomaly-detection incident-api; do
            echo "--- $service ---"
            docker compose logs "$service" --tail 5 2>/dev/null || echo "Logs not available"
            echo
        done
        
    } > "$report_file"
    
    print_success "Diagnostic report saved to: $report_file"
}

# Suggest fixes
suggest_fixes() {
    print_section "Suggested Fixes"
    
    echo "Based on the diagnostic results, try these solutions:"
    echo
    
    print_info "1. If services are not healthy:"
    echo "   docker compose restart [service-name]"
    echo "   docker compose logs [service-name] --tail 50"
    echo
    
    print_info "2. If no data is flowing:"
    echo "   ./scripts/simulate_node_metrics.sh"
    echo "   python3 scripts/publish_test_anomalies.py"
    echo
    
    print_info "3. If memory/disk issues:"
    echo "   docker system prune -f"
    echo "   docker volume prune -f"
    echo
    
    print_info "4. Complete restart:"
    echo "   docker compose down"
    echo "   docker compose up -d"
    echo "   # Wait 2-3 minutes for services to initialize"
    echo
    
    print_info "5. For persistent issues:"
    echo "   Check the generated diagnostic report"
    echo "   Review logs in detail with: docker compose logs -f"
}

# Main troubleshooting function
main() {
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}     AIOps NAAS Troubleshooting Diagnostics${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo
    
    check_system_resources
    check_docker_environment
    check_service_status
    check_network_connectivity
    check_data_flow
    generate_diagnostic_report
    suggest_fixes
    
    echo
    print_success "Troubleshooting diagnostics completed!"
    print_info "Review the diagnostic report and try the suggested fixes."
}

# Run main function
main "$@"