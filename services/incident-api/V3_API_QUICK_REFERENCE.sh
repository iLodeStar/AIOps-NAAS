#!/bin/bash
# Quick Reference: Testing V3 API Endpoints
# This script shows how to test all V3 endpoints with curl

echo "================================================================================"
echo "V3 API Endpoints - Quick Test Guide"
echo "================================================================================"
echo ""
echo "Prerequisites:"
echo "  - Incident API service running on http://localhost:8081"
echo "  - ClickHouse database available"
echo "  - NATS messaging available"
echo ""
echo "================================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8081"

echo -e "${BLUE}Test 1: GET /api/v3/stats (with default 1h time range)${NC}"
echo "================================================================================"
echo "curl -s ${BASE_URL}/api/v3/stats | jq '.'"
echo ""
echo "Expected: Stats with incidents categorized by severity, status, category"
echo "          Plus processing metrics and SLO compliance"
echo ""
echo -e "${YELLOW}Sample command:${NC}"
echo "curl -s ${BASE_URL}/api/v3/stats | jq '.'"
echo ""
echo "================================================================================"
echo ""

echo -e "${BLUE}Test 2: GET /api/v3/stats (with custom time range)${NC}"
echo "================================================================================"
echo "curl -s '${BASE_URL}/api/v3/stats?time_range=24h' | jq '.'"
echo ""
echo "Expected: Stats for last 24 hours"
echo ""
echo -e "${YELLOW}Sample command:${NC}"
echo "curl -s '${BASE_URL}/api/v3/stats?time_range=7d' | jq '.incidents_by_severity'"
echo ""
echo "================================================================================"
echo ""

echo -e "${BLUE}Test 3: GET /api/v3/trace/{tracking_id}${NC}"
echo "================================================================================"
echo "curl -s ${BASE_URL}/api/v3/trace/req-20251003-120000-abc123 | jq '.'"
echo ""
echo "Expected: Complete trace with stages and latency breakdown"
echo ""
echo -e "${YELLOW}Sample command:${NC}"
echo "curl -s ${BASE_URL}/api/v3/trace/req-20251003-120000-abc123 | jq '.stages'"
echo ""
echo "================================================================================"
echo ""

echo -e "${BLUE}Test 4: POST /api/v3/incidents (Create Incident)${NC}"
echo "================================================================================"
cat << 'EOF'
curl -X POST http://localhost:8081/api/v3/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "cpu_pressure",
    "incident_severity": "high",
    "ship_id": "ship-001",
    "service": "cpu-monitor",
    "metric_name": "cpu_usage",
    "metric_value": 95.5,
    "anomaly_score": 0.9,
    "detector_name": "threshold_detector",
    "suggested_runbooks": ["restart_service", "scale_resources"],
    "metadata": {
      "test": true,
      "source": "manual_test"
    }
  }' | jq '.'
EOF
echo ""
echo "Expected: New incident created with generated incident_id and tracking_id"
echo ""
echo "================================================================================"
echo ""

echo -e "${BLUE}Test 5: GET /api/v3/incidents/{incident_id}${NC}"
echo "================================================================================"
echo "# First, create an incident and capture the ID:"
echo "INCIDENT_ID=\$(curl -X POST ${BASE_URL}/api/v3/incidents \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"incident_type\":\"test\",\"incident_severity\":\"low\",\"ship_id\":\"ship-test\",\"service\":\"test\"}' \\"
echo "  | jq -r '.incident_id')"
echo ""
echo "# Then retrieve it:"
echo "curl -s ${BASE_URL}/api/v3/incidents/\${INCIDENT_ID} | jq '.'"
echo ""
echo "Expected: Full incident details with timeline, metadata, and tracking_id"
echo ""
echo "================================================================================"
echo ""

echo -e "${GREEN}Additional Examples:${NC}"
echo ""
echo "# Get only severity breakdown:"
echo "curl -s '${BASE_URL}/api/v3/stats?time_range=1h' | jq '.incidents_by_severity'"
echo ""
echo "# Get only SLO compliance:"
echo "curl -s '${BASE_URL}/api/v3/stats?time_range=24h' | jq '.slo_compliance'"
echo ""
echo "# Get trace total latency:"
echo "curl -s ${BASE_URL}/api/v3/trace/req-test-123 | jq '.total_latency_ms'"
echo ""
echo "# Create minimal incident:"
cat << 'EOF'
curl -X POST http://localhost:8081/api/v3/incidents \
  -H "Content-Type: application/json" \
  -d '{"incident_type":"test","incident_severity":"low","ship_id":"ship-test","service":"test"}' \
  | jq '.incident_id'
EOF
echo ""
echo "================================================================================"
echo ""

echo -e "${GREEN}API Documentation:${NC}"
echo "  • Swagger UI: ${BASE_URL}/docs"
echo "  • ReDoc:      ${BASE_URL}/redoc"
echo ""

echo -e "${GREEN}Health Check:${NC}"
echo "  curl ${BASE_URL}/health"
echo ""

echo "================================================================================"
echo "For detailed documentation, see: V3_API_IMPLEMENTATION_SUMMARY.md"
echo "For unit tests, run: pytest test_v3_api.py -v"
echo "For manual tests, run: python3 manual_test_v3_api.py"
echo "================================================================================"
