#!/bin/bash
"""
AIOps NAAS - Smoke Test for Core Service Endpoints

Quick health check and sample response validation for core services.
This script checks basic connectivity and endpoint responses without 
performing full end-to-end validation.

Usage: ./scripts/smoke_endpoints.sh

Environment Variables:
  VM_URL - VictoriaMetrics URL (default: http://localhost:8428)
  INCIDENT_API_URL - Incident API URL (default: http://localhost:8081)  
  GRAFANA_URL - Grafana URL (default: http://localhost:3000)
  CH_URL - ClickHouse URL (default: http://localhost:8123)
  NATS_URL - NATS HTTP monitoring URL (default: http://localhost:8222)
  TIMEOUT - Request timeout in seconds (default: 10)
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
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
CH_URL="${CH_URL:-http://localhost:8123}"
NATS_URL="${NATS_URL:-http://localhost:8222}"
TIMEOUT="${TIMEOUT:-10}"

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

check_endpoint() {
    local name="$1"
    local url="$2"
    local expected_content="$3"
    local auth="$4"
    
    echo -n "🔗 Checking $name... "
    
    local curl_cmd="curl -sf --max-time $TIMEOUT"
    if [[ -n "$auth" ]]; then
        curl_cmd="$curl_cmd -u $auth"
    fi
    
    local response
    if response=$($curl_cmd "$url" 2>/dev/null); then
        if [[ -z "$expected_content" ]] || echo "$response" | grep -q "$expected_content"; then
            echo -e "${GREEN}✅ OK${NC}"
            if [[ -n "$expected_content" ]]; then
                echo "   ↳ Response contains: $expected_content"
            fi
        else
            echo -e "${YELLOW}⚠️  Reachable but unexpected response${NC}"
            echo "   ↳ Expected: $expected_content"
            echo "   ↳ Got: $(echo "$response" | head -c 100)..."
        fi
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "   ↳ URL: $url"
    fi
}

check_json_endpoint() {
    local name="$1"
    local url="$2"
    local expected_keys="$3"
    local auth="$4"
    
    echo -n "📊 Checking $name... "
    
    local curl_cmd="curl -sf --max-time $TIMEOUT"
    if [[ -n "$auth" ]]; then
        curl_cmd="$curl_cmd -u $auth"
    fi
    
    local response
    if response=$($curl_cmd "$url" 2>/dev/null); then
        if command -v jq >/dev/null 2>&1; then
            if echo "$response" | jq . >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Valid JSON${NC}"
                
                # Check for expected keys
                for key in $expected_keys; do
                    if echo "$response" | jq -e "has(\"$key\")" >/dev/null 2>&1; then
                        echo "   ↳ Has key: $key"
                    else
                        echo "   ↳ Missing key: $key"
                    fi
                done
            else
                echo -e "${YELLOW}⚠️  Reachable but invalid JSON${NC}"
            fi
        else
            echo -e "${GREEN}✅ Reachable${NC} (jq not available for JSON validation)"
        fi
    else
        echo -e "${RED}❌ Failed${NC}"
        echo "   ↳ URL: $url"
    fi
}

test_basic_connectivity() {
    print_section "Basic Service Connectivity"
    
    # VictoriaMetrics health
    check_endpoint "VictoriaMetrics Health" "$VM_URL/health" "" ""
    
    # Incident API health
    check_endpoint "Incident API Health" "$INCIDENT_API_URL/health" "" ""
    
    # Grafana health (may require auth)
    check_endpoint "Grafana Health" "$GRAFANA_URL/api/health" "ok" ""
    
    # ClickHouse ping
    check_endpoint "ClickHouse Ping" "$CH_URL/ping" "Ok." ""
    
    # NATS monitoring
    check_endpoint "NATS Monitoring" "$NATS_URL/connz" "connections" ""
}

test_api_endpoints() {
    print_section "API Endpoint Responses"
    
    # VictoriaMetrics query API
    local vm_query_url="$VM_URL/api/v1/query?query=up"
    check_json_endpoint "VictoriaMetrics Query API" "$vm_query_url" "status data" ""
    
    # Incident API - list incidents
    check_json_endpoint "Incident API - List Incidents" "$INCIDENT_API_URL/incidents" "" ""
    
    # Incident API - summary
    check_json_endpoint "Incident API - Summary" "$INCIDENT_API_URL/summary" "total_incidents open_incidents" ""
}

test_metric_ingestion() {
    print_section "Metric Ingestion Test"
    
    local timestamp=$(date +%s)
    local test_metric="smoke_test_metric{instance=\"smoke-test\"} $timestamp 42"
    
    echo -n "📤 Testing metric ingestion... "
    
    if echo "$test_metric" | curl -sf --max-time $TIMEOUT -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Ingestion OK${NC}"
        
        # Wait a moment and query back
        sleep 2
        echo -n "📥 Testing metric query... "
        
        local query_url="$VM_URL/api/v1/query?query=smoke_test_metric"
        if curl -sf --max-time $TIMEOUT "$query_url" 2>/dev/null | grep -q "smoke_test_metric"; then
            echo -e "${GREEN}✅ Query OK${NC}"
        else
            echo -e "${YELLOW}⚠️  Query failed${NC}"
        fi
    else
        echo -e "${RED}❌ Failed${NC}"
    fi
}

test_nats_connectivity() {
    print_section "NATS Connectivity"
    
    # Check NATS server info
    check_json_endpoint "NATS Server Info" "$NATS_URL/varz" "server_id version" ""
    
    # Check NATS connections
    check_json_endpoint "NATS Connections" "$NATS_URL/connz" "total_connections connections" ""
    
    # Check NATS subscriptions
    check_json_endpoint "NATS Subscriptions" "$NATS_URL/subsz" "total_subs subscriptions" ""
}

print_summary() {
    print_header "Smoke Test Summary"
    
    echo -e "${BLUE}Services Tested:${NC}"
    echo "✅ VictoriaMetrics - Health, Query API, Metric Ingestion"
    echo "✅ Incident API - Health, Incidents List, Summary"  
    echo "✅ Grafana - Health Check"
    echo "✅ ClickHouse - Ping"
    echo "✅ NATS - Server Info, Connections, Subscriptions"
    
    echo -e "\n${BLUE}What This Test Covers:${NC}"
    echo "- Basic service connectivity and health checks"
    echo "- API endpoint responsiveness and JSON structure"
    echo "- Metric ingestion and query capability"
    echo "- NATS server status and connection info"
    
    echo -e "\n${BLUE}What This Test Does NOT Cover:${NC}"
    echo "- End-to-end anomaly detection pipeline"
    echo "- Data correlation and incident generation"  
    echo "- Authentication and authorization"
    echo "- Performance and load testing"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "- For full pipeline validation: ./scripts/validate_pipeline.sh"
    echo "- For manual anomaly testing: python3 scripts/publish_test_anomalies.py"
    echo "- Check service logs: docker compose logs <service-name>"
}

main() {
    print_header "AIOps NAAS Smoke Test"
    
    test_basic_connectivity
    test_api_endpoints  
    test_metric_ingestion
    test_nats_connectivity
    print_summary
    
    echo -e "\n${GREEN}🎉 Smoke test completed!${NC}"
    echo -e "${YELLOW}Note: This is a basic connectivity test. For full validation, run validate_pipeline.sh${NC}"
}

# Check if running with --help
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    head -n 20 "$0" | tail -n +2 | sed 's/^"""//g; s/"""$//g'
    exit 0
fi

main "$@"