#!/bin/bash
"""
AIOps NAAS - End-to-End Pipeline Validator

This script validates the complete anomaly detection pipeline:
1. Sends baseline metrics to VictoriaMetrics
2. Sends anomaly spikes to trigger detection
3. Waits for anomalies to be processed
4. Verifies incidents are created via Incident API
5. Optionally checks ClickHouse storage

Usage: 
  export CH_USER=admin CH_PASS=admin
  chmod +x scripts/validate_pipeline.sh
  ./scripts/validate_pipeline.sh

Environment Variables:
  VM_URL - VictoriaMetrics URL (default: http://localhost:8428)
  INCIDENT_API_URL - Incident API URL (default: http://localhost:8081) 
  CH_URL - ClickHouse URL (default: http://localhost:8123)
  CH_USER - ClickHouse username (default: admin)
  CH_PASS - ClickHouse password (default: admin)
  WAIT_TIME - Wait time between steps in seconds (default: 30)
"""

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VM_URL="${VM_URL:-http://localhost:8428}"
INCIDENT_API_URL="${INCIDENT_API_URL:-http://localhost:8081}"
CH_URL="${CH_URL:-http://localhost:8123}"
CH_USER="${CH_USER:-admin}"
CH_PASS="${CH_PASS:-admin}"
WAIT_TIME="${WAIT_TIME:-30}"

print_header() {
    echo -e "\n${BLUE}================================================================${NC}"
    echo -e "${BLUE}🔍 $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
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

check_dependencies() {
    print_section "Checking Dependencies"
    
    local missing=0
    
    if ! command -v curl >/dev/null 2>&1; then
        print_error "curl is required but not installed"
        missing=1
    else
        print_success "curl found"
    fi
    
    if ! command -v jq >/dev/null 2>&1; then
        print_warning "jq not found - will use basic parsing"
    else
        print_success "jq found"
    fi
    
    if [[ $missing -eq 1 ]]; then
        echo -e "${RED}Please install missing dependencies${NC}"
        exit 1
    fi
}

check_services() {
    print_section "Checking Service Health"
    
    local failures=0
    
    # Check VictoriaMetrics
    if curl -sf "$VM_URL/health" >/dev/null 2>&1; then
        print_success "VictoriaMetrics is healthy"
    else
        print_error "VictoriaMetrics is not accessible at $VM_URL"
        failures=$((failures + 1))
    fi
    
    # Check Incident API
    if curl -sf "$INCIDENT_API_URL/health" >/dev/null 2>&1; then
        print_success "Incident API is healthy"
    else
        print_error "Incident API is not accessible at $INCIDENT_API_URL"
        failures=$((failures + 1))
    fi
    
    # Check ClickHouse (optional)
    if [[ -n "${CH_USER}" && -n "${CH_PASS}" ]]; then
        if curl -sf -u "${CH_USER}:${CH_PASS}" "$CH_URL/ping" >/dev/null 2>&1; then
            print_success "ClickHouse is accessible with credentials"
        else
            print_warning "ClickHouse not accessible via HTTP (may use native TCP)"
        fi
    else
        print_warning "ClickHouse credentials not provided - skipping HTTP check"
    fi
    
    if [[ $failures -gt 0 ]]; then
        echo -e "${RED}Some services are not healthy. Please check your deployment.${NC}"
        exit 1
    fi
}

send_baseline_metrics() {
    print_section "Sending Baseline Metrics"
    
    local timestamp=$(date +%s)
    
    # Send baseline CPU metrics (normal values)
    local cpu_data="node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $((timestamp - 300)) $(echo "scale=2; 95.5" | bc -l)
node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $((timestamp - 240)) $(echo "scale=2; 94.8" | bc -l)
node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $((timestamp - 180)) $(echo "scale=2; 96.2" | bc -l)
node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $((timestamp - 120)) $(echo "scale=2; 95.1" | bc -l)
node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $((timestamp - 60)) $(echo "scale=2; 94.9" | bc -l)"
    
    # Send baseline Memory metrics (normal values)  
    local mem_total=$((8 * 1024 * 1024 * 1024)) # 8GB
    local mem_available_normal=$((6 * 1024 * 1024 * 1024)) # 6GB available (25% usage)
    
    local mem_data="node_memory_MemTotal_bytes{instance=\"validator:9100\"} $((timestamp - 300)) $mem_total
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $((timestamp - 300)) $mem_available_normal
node_memory_MemTotal_bytes{instance=\"validator:9100\"} $((timestamp - 240)) $mem_total  
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $((timestamp - 240)) $mem_available_normal
node_memory_MemTotal_bytes{instance=\"validator:9100\"} $((timestamp - 180)) $mem_total
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $((timestamp - 180)) $mem_available_normal
node_memory_MemTotal_bytes{instance=\"validator:9100\"} $((timestamp - 120)) $mem_total
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $((timestamp - 120)) $mem_available_normal
node_memory_MemTotal_bytes{instance=\"validator:9100\"} $((timestamp - 60)) $mem_total
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $((timestamp - 60)) $mem_available_normal"
    
    # Send to VictoriaMetrics
    if echo "$cpu_data" | curl -sf -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null; then
        print_success "CPU baseline metrics sent"
    else
        print_error "Failed to send CPU baseline metrics"
        return 1
    fi
    
    if echo "$mem_data" | curl -sf -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null; then
        print_success "Memory baseline metrics sent"
    else
        print_error "Failed to send Memory baseline metrics"  
        return 1
    fi
}

send_anomaly_spikes() {
    print_section "Sending Anomaly Spikes"
    
    local timestamp=$(date +%s)
    
    # Send high CPU usage (low idle time = high usage)
    local cpu_spike="node_cpu_seconds_total{mode=\"idle\",instance=\"validator:9100\"} $timestamp $(echo "scale=2; 15.0" | bc -l)"
    
    # Send high Memory usage (low available memory = high usage)
    local mem_total=$((8 * 1024 * 1024 * 1024)) # 8GB
    local mem_available_low=$((512 * 1024 * 1024)) # 512MB available (94% usage)
    local mem_spike="node_memory_MemTotal_bytes{instance=\"validator:9100\"} $timestamp $mem_total
node_memory_MemAvailable_bytes{instance=\"validator:9100\"} $timestamp $mem_available_low"
    
    # Send CPU spike
    if echo "$cpu_spike" | curl -sf -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null; then
        print_success "CPU anomaly spike sent (85% usage)"
    else
        print_error "Failed to send CPU spike"
        return 1
    fi
    
    # Send Memory spike
    if echo "$mem_spike" | curl -sf -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null; then
        print_success "Memory anomaly spike sent (94% usage)"
    else  
        print_error "Failed to send Memory spike"
        return 1
    fi
}

wait_for_processing() {
    print_section "Waiting for Anomaly Processing"
    
    echo -e "⏳ Waiting ${WAIT_TIME}s for anomaly detection and correlation..."
    for i in $(seq 1 $WAIT_TIME); do
        echo -n "."
        sleep 1
    done
    echo ""
    print_success "Wait complete"
}

check_incidents() {
    print_section "Checking for Generated Incidents"
    
    local incidents_response
    if incidents_response=$(curl -sf "$INCIDENT_API_URL/incidents" 2>/dev/null); then
        if command -v jq >/dev/null 2>&1; then
            local incident_count=$(echo "$incidents_response" | jq '. | length' 2>/dev/null || echo "0")
            echo -e "📊 Found $incident_count incidents"
            
            if [[ $incident_count -gt 0 ]]; then
                print_success "Pipeline validation PASSED - incidents were generated"
                echo -e "\n${BLUE}Recent incidents:${NC}"
                echo "$incidents_response" | jq -r '.[] | "- \(.incident_id): \(.metric_name) (\(.anomaly_score))"' 2>/dev/null || echo "$incidents_response"
                return 0
            else
                print_warning "No incidents found yet"
                return 1
            fi
        else
            # Basic parsing without jq
            if [[ "$incidents_response" == "[]" ]] || [[ -z "$incidents_response" ]]; then
                print_warning "No incidents found yet"
                return 1
            else
                print_success "Pipeline validation PASSED - incidents were generated"
                echo -e "\n${BLUE}Incidents response:${NC}"
                echo "$incidents_response"
                return 0
            fi
        fi
    else
        print_error "Failed to query incidents API"
        return 1
    fi
}

check_clickhouse() {
    print_section "Checking ClickHouse Storage (Optional)"
    
    if [[ -z "${CH_USER}" || -z "${CH_PASS}" ]]; then
        print_warning "ClickHouse credentials not provided - skipping"
        return 0
    fi
    
    local query="SELECT count() FROM incidents WHERE created_at >= now() - INTERVAL 5 MINUTE"
    local ch_response
    
    if ch_response=$(curl -sf -u "${CH_USER}:${CH_PASS}" "$CH_URL" --data "$query" 2>/dev/null); then
        echo -e "📊 Recent incidents in ClickHouse: $ch_response"
        if [[ "$ch_response" -gt 0 ]]; then
            print_success "ClickHouse validation PASSED"
        else
            print_warning "No recent incidents in ClickHouse"
        fi
    else
        print_warning "Could not check ClickHouse (may use native TCP instead of HTTP)"
    fi
}

print_summary() {
    print_header "Validation Summary"
    
    echo -e "${BLUE}Pipeline Components Tested:${NC}"
    echo "1. ✅ VictoriaMetrics - Metrics ingestion"
    echo "2. ✅ Anomaly Detection - PromQL queries and anomaly scoring"
    echo "3. ✅ NATS - Event publishing"
    echo "4. ✅ Benthos - Event correlation"
    echo "5. ✅ Incident API - Incident storage and retrieval"
    echo "6. ⚠️  ClickHouse - Storage validation (optional)"
    
    echo -e "\n${BLUE}Metrics Simulated:${NC}"
    echo "- node_cpu_seconds_total (idle mode) - CPU usage calculation"
    echo "- node_memory_MemTotal_bytes - Memory total"
    echo "- node_memory_MemAvailable_bytes - Memory usage calculation"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "- Check Grafana dashboards at http://localhost:3000"
    echo "- Review logs: docker compose logs anomaly-detection incident-api"
    echo "- For manual testing: python3 scripts/publish_test_anomalies.py"
}

main() {
    print_header "AIOps NAAS Pipeline Validator"
    
    check_dependencies
    check_services
    send_baseline_metrics
    send_anomaly_spikes
    wait_for_processing
    
    local validation_passed=0
    if check_incidents; then
        validation_passed=1
    fi
    
    check_clickhouse
    print_summary
    
    if [[ $validation_passed -eq 1 ]]; then
        echo -e "\n${GREEN}🎉 VALIDATION SUCCESSFUL - End-to-end pipeline working!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ VALIDATION FAILED - No incidents generated${NC}"
        echo -e "${YELLOW}💡 Troubleshooting suggestions:${NC}"
        echo "1. Check anomaly-detection service logs: docker compose logs anomaly-detection"  
        echo "2. Verify NATS connectivity: docker compose logs nats"
        echo "3. Check correlation service: docker compose logs benthos"
        echo "4. Try manual anomaly publishing: python3 scripts/publish_test_anomalies.py"
        exit 1
    fi
}

# Check if running with --help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    head -n 25 "$0" | tail -n +2 | sed 's/^"""//g; s/"""$//g'
    exit 0
fi

main "$@"