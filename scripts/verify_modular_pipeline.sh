#!/bin/bash

# End-to-End Modular Pipeline Verification Script
# Tests the sequential processing through all pipeline stages

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE} Modular Pipeline End-to-End Verification${NC}"
echo -e "${BLUE}=============================================${NC}"

# Generate tracking ID for this test
TRACKING_ID="PIPELINE-TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo -e "${GREEN}🔍 Tracking ID: $TRACKING_ID${NC}"
echo ""

# Step 1: Verify all services are running
echo -e "${BLUE}Step 1: Verifying Service Health${NC}"

services=("vector:8686" "anomaly-detection:8080" "benthos-enrichment:4196" "benthos-anomaly-enrichment:4197" "enhanced-anomaly-detection:9082" "benthos:4195" "incident-api:8081")
for service in "${services[@]}"; do
    name=${service%:*}
    port=${service#*:}
    
    if curl -sf http://localhost:$port/health > /dev/null 2>&1 || curl -sf http://localhost:$port/stats > /dev/null 2>&1; then
        echo -e "  ✅ $name is healthy (port $port)"
    else
        echo -e "  ${RED}❌ $name is not responding (port $port)${NC}"
        echo -e "${RED}Error: Service $name must be running for pipeline verification${NC}"
        exit 1
    fi
done
echo ""

# Step 2: Send test log message through Vector
echo -e "${BLUE}Step 2: Sending Test Log Message${NC}"
echo "Injecting ERROR log with tracking ID: $TRACKING_ID"

# Send to Vector syslog UDP port (mapped to 1517 externally, 1514 internally)
echo "<11>$(date '+%b %d %H:%M:%S') ship-aurora web-app: ERROR $TRACKING_ID Database connection timeout - testing modular pipeline" | nc -u localhost 1517

echo "  ✅ Test message sent to Vector"
echo ""

# Step 3: Wait for processing through pipeline
echo -e "${BLUE}Step 3: Allowing Pipeline Processing Time${NC}"
echo "Waiting 30 seconds for message to flow through all pipeline stages..."
sleep 30
echo ""

# Step 4: Verify Vector processed the message
echo -e "${BLUE}Step 4: Verifying Vector Processing${NC}"

# Check Vector metrics for events processed
VECTOR_EVENTS_IN=$(curl -s http://localhost:8686/metrics 2>/dev/null | grep 'vector_events_in_total.*syslog' | tail -1 | awk '{print $2}' || echo "0")
VECTOR_EVENTS_OUT=$(curl -s http://localhost:8686/metrics 2>/dev/null | grep 'vector_events_out_total.*anomalous' | tail -1 | awk '{print $2}' || echo "0")

echo "  Vector Input Events: ${VECTOR_EVENTS_IN:-0}"
echo "  Vector Anomalous Output Events: ${VECTOR_EVENTS_OUT:-0}"

if [[ "${VECTOR_EVENTS_IN:-0}" -gt 0 ]] && [[ "${VECTOR_EVENTS_OUT:-0}" -gt 0 ]]; then
    echo -e "  ✅ Vector is processing messages correctly"
else
    echo -e "  ${YELLOW}⚠️  Vector metrics may be delayed or not visible${NC}"
fi

# Check ClickHouse for the stored log
CLICKHOUSE_RESULT=$(docker exec aiops-clickhouse clickhouse-client --query="SELECT count() FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null || echo "0")
if [ "${CLICKHOUSE_RESULT:-0}" -gt 0 ]; then
    echo -e "  ✅ Log stored in ClickHouse (${CLICKHOUSE_RESULT} records)"
else
    echo -e "  ${YELLOW}⚠️  Log not yet visible in ClickHouse (may be delayed)${NC}"
fi
echo ""

# Step 5: Verify Anomaly Detection Service
echo -e "${BLUE}Step 5: Verifying Anomaly Detection Service${NC}"

# Check service stats
ANOMALY_STATS=$(curl -s http://localhost:8080/health 2>/dev/null || echo "{}")
echo "  Anomaly Detection Service Status: $ANOMALY_STATS"

# Check service logs for our tracking ID
if docker logs aiops-anomaly-detection --tail 50 2>/dev/null | grep "$TRACKING_ID" >/dev/null 2>&1; then
    echo -e "  ✅ Anomaly Detection Service processed tracking ID: $TRACKING_ID"
else
    echo -e "  ${YELLOW}⚠️  Tracking ID not found in Anomaly Detection Service logs${NC}"
fi
echo ""

# Step 6: Verify Benthos Enrichment Service  
echo -e "${BLUE}Step 6: Verifying Benthos Enrichment Service${NC}"

# Check enrichment service stats
ENRICHMENT_STATS=$(curl -s http://localhost:4196/stats 2>/dev/null || echo "{}")
echo "  Benthos Enrichment Stats: $ENRICHMENT_STATS"

# Check service logs
if docker logs aiops-benthos-enrichment --tail 50 2>/dev/null | grep "$TRACKING_ID" >/dev/null 2>&1; then
    echo -e "  ✅ Benthos Enrichment Service processed tracking ID: $TRACKING_ID"
else
    echo -e "  ${YELLOW}⚠️  Tracking ID not found in Benthos Enrichment Service logs${NC}"
fi
echo ""

# Step 7: Verify Enhanced Anomaly Detection Service
echo -e "${BLUE}Step 7: Verifying Enhanced Anomaly Detection Service${NC}"

# Check enhanced anomaly detection stats
ENHANCED_STATS=$(curl -s http://localhost:9082/health 2>/dev/null || echo "{}")
echo "  Enhanced Anomaly Detection Status: $ENHANCED_STATS"

# Check service logs
if docker logs aiops-enhanced-anomaly-detection --tail 50 2>/dev/null | grep "$TRACKING_ID" >/dev/null 2>&1; then
    echo -e "  ✅ Enhanced Anomaly Detection Service processed tracking ID: $TRACKING_ID"
else
    echo -e "  ${YELLOW}⚠️  Tracking ID not found in Enhanced Anomaly Detection Service logs${NC}"
fi
echo ""

# Step 8: Verify Benthos Correlation Service
echo -e "${BLUE}Step 8: Verifying Benthos Correlation Service${NC}"

# Check correlation service stats
CORRELATION_STATS=$(curl -s http://localhost:4195/stats 2>/dev/null || echo "{}")
echo "  Benthos Correlation Stats: $CORRELATION_STATS"

# Check service logs
if docker logs aiops-benthos --tail 50 2>/dev/null | grep "$TRACKING_ID" >/dev/null 2>&1; then
    echo -e "  ✅ Benthos Correlation Service processed tracking ID: $TRACKING_ID"
else
    echo -e "  ${YELLOW}⚠️  Tracking ID not found in Benthos Correlation Service logs${NC}"
fi
echo ""

# Step 9: Verify Incident Creation
echo -e "${BLUE}Step 9: Verifying Incident Creation${NC}"

# Check incident API for incidents with our tracking ID
INCIDENT_RESULT=$(curl -s "http://localhost:8081/api/v1/incidents" 2>/dev/null | jq -r ".[] | select(.tracking_id == \"$TRACKING_ID\") | .incident_id" 2>/dev/null || echo "")

if [ -n "$INCIDENT_RESULT" ] && [ "$INCIDENT_RESULT" != "null" ]; then
    echo -e "  ✅ Incident created successfully!"
    echo -e "     Incident ID: $INCIDENT_RESULT"
    
    # Get incident details
    INCIDENT_DETAILS=$(curl -s "http://localhost:8081/api/v1/incidents/$INCIDENT_RESULT" 2>/dev/null | jq . 2>/dev/null || echo "{}")
    echo -e "     Incident Details: $INCIDENT_DETAILS"
else
    echo -e "  ${YELLOW}⚠️  Incident not yet created (may be delayed)${NC}"
    
    # Check ClickHouse incidents table
    INCIDENTS_COUNT=$(docker exec aiops-clickhouse clickhouse-client --query="SELECT count() FROM logs.incidents WHERE tracking_id = '$TRACKING_ID'" 2>/dev/null || echo "0")
    if [ "${INCIDENTS_COUNT:-0}" -gt 0 ]; then
        echo -e "     ✅ Found incident in ClickHouse: $INCIDENTS_COUNT records"
    else
        echo -e "     ${YELLOW}⚠️  No incident found in ClickHouse either${NC}"
    fi
fi
echo ""

# Step 10: Pipeline Health Summary
echo -e "${BLUE}Step 10: Pipeline Health Summary${NC}"

# Count NATS subjects (if nats CLI available)
if command -v nats >/dev/null 2>&1; then
    echo "NATS Topic Activity:"
    for topic in "logs.anomalous" "anomaly.detected" "anomaly.detected.enriched" "anomaly.detected.enriched.final" "incidents.created"; do
        # Note: This would require NATS CLI and proper NATS server configuration
        echo "  Topic: $topic (monitoring requires nats CLI setup)"
    done
else
    echo "  ℹ️  NATS CLI not available - cannot show topic activity"
fi

echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN} Pipeline Verification Complete${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo -e "📊 Summary:"
echo -e "   Tracking ID: $TRACKING_ID"
echo -e "   Pipeline Stages: Vector → Anomaly Detection → Benthos Enrichment → Enhanced Anomaly Detection → Benthos Correlation → Incident API"
echo -e "   NATS Topics: logs.anomalous → anomaly.detected → anomaly.detected.enriched → anomaly.detected.enriched.final → incidents.created"
echo ""
echo -e "🔧 To investigate further:"
echo -e "   - Check service logs: docker logs <service-name>"
echo -e "   - Monitor NATS topics with: nats sub <topic-name>"
echo -e "   - View incident details: curl http://localhost:8081/api/v1/incidents"
echo -e "   - Check ClickHouse data: docker exec aiops-clickhouse clickhouse-client"
echo ""

# Exit with appropriate code
if [ -n "$INCIDENT_RESULT" ] && [ "$INCIDENT_RESULT" != "null" ]; then
    echo -e "${GREEN}✅ End-to-End Pipeline Verification: PASSED${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  End-to-End Pipeline Verification: PARTIAL - Some stages may need more time${NC}"
    exit 1
fi