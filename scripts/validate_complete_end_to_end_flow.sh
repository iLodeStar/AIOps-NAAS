#!/bin/bash

# AIOps NAAS - Comprehensive End-to-End Validation Script  
# Validates complete message flow with console evidence
# Usage: ./validate_complete_end_to_end_flow.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Generate unique tracking ID
TRACKING_ID="E2E-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

echo "============================================="
echo "🚀 AIOps NAAS - COMPREHENSIVE END-TO-END VALIDATION"
echo "============================================="
echo ""
echo "🆔 TRACKING ID: $TRACKING_ID"
echo ""

# Step 1: Service Health Checks
log "Step 1: Validating Service Health..."

# ClickHouse health check
if curl -s http://localhost:8123/ping | grep -q "Ok."; then
    success "ClickHouse: Healthy (Ok.)"
else
    error "ClickHouse: Not responding"
    exit 1
fi

# Vector health check
if curl -s http://localhost:8686/health | grep -q '"status":"ok"'; then
    success "Vector: Healthy"
else
    error "Vector: Not responding"
    exit 1
fi

# NATS health check  
if curl -s http://localhost:8222/healthz | grep -q '"status":"ok"'; then
    success "NATS: Healthy"
else
    error "NATS: Not responding"
    exit 1
fi

# Benthos health check
if curl -s http://localhost:4195/ping | grep -q "pong"; then
    success "Benthos: Healthy"
else
    warning "Benthos: Not responding (may not be critical for basic flow)"
fi

echo ""

# Step 2: Send Test Messages
log "Step 2: Sending Test Messages with Tracking ID..."

# Send UDP message
log "Sending UDP message to Vector (port 1514)..."
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID UDP message from validation script" | nc -u localhost 1514

# Send TCP message  
log "Sending TCP message to Vector (port 1515)..."
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: NORMAL_TEST $TRACKING_ID TCP message from validation script" | nc localhost 1515

echo ""

# Step 3: Verify Vector Reception (immediate)
log "Step 3: Verifying Vector Reception..."

# Wait 5 seconds for Vector to process
sleep 5

VECTOR_LOGS=$(docker logs aiops-vector --tail=50 2>/dev/null | grep "$TRACKING_ID" | wc -l)
if [ "$VECTOR_LOGS" -gt 0 ]; then
    success "Vector: Found $VECTOR_LOGS log entries with tracking ID"
    log "Sample Vector log entry:"
    docker logs aiops-vector --tail=50 2>/dev/null | grep "$TRACKING_ID" | head -1 | jq -C 2>/dev/null || docker logs aiops-vector --tail=50 2>/dev/null | grep "$TRACKING_ID" | head -1
else
    error "Vector: No log entries found with tracking ID"
    warning "Debug: Last 5 Vector log entries:"
    docker logs aiops-vector --tail=5 2>/dev/null
fi

echo ""

# Step 4: Check Vector Metrics
log "Step 4: Checking Vector Processing Metrics..."

# Get Vector input metrics
EVENTS_IN=$(curl -s http://localhost:8686/metrics | grep "vector_events_in_total" | grep "syslog" | awk -F' ' '{total+=$NF} END {print total}')
EVENTS_OUT=$(curl -s http://localhost:8686/metrics | grep "vector_events_out_total" | grep "clickhouse" | awk -F' ' '{print $NF}')

if [ ! -z "$EVENTS_IN" ] && [ "$EVENTS_IN" -gt 0 ]; then
    success "Vector Input: $EVENTS_IN total events processed"
else
    warning "Vector Input: No syslog events found in metrics"
fi

if [ ! -z "$EVENTS_OUT" ] && [ "$EVENTS_OUT" -gt 0 ]; then
    success "Vector Output: $EVENTS_OUT events sent to ClickHouse"  
else
    error "Vector Output: No events sent to ClickHouse - CHECK CLICKHOUSE AUTHENTICATION"
    warning "Check Vector logs for ClickHouse sink errors:"
    docker logs aiops-vector --tail=20 2>/dev/null | grep -i "clickhouse\|error" || echo "No obvious errors found"
fi

echo ""

# Step 5: Verify ClickHouse Storage (with retry)
log "Step 5: Verifying ClickHouse Storage..."

# Wait for Vector to send batch to ClickHouse (Vector batches every 5 seconds)
log "Waiting 15 seconds for Vector batch processing..."
sleep 15

# Query ClickHouse for tracking ID
CLICKHOUSE_RECORDS=$(docker exec aiops-clickhouse clickhouse-client --query "SELECT count() FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null || echo "0")

if [ "$CLICKHOUSE_RECORDS" -gt 0 ]; then
    success "ClickHouse: Found $CLICKHOUSE_RECORDS record(s) with tracking ID"
    
    log "ClickHouse record details:"
    docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 3" 2>/dev/null || warning "Could not retrieve record details"
    
else
    error "ClickHouse: No records found with tracking ID"
    
    # Diagnostic checks
    log "Performing diagnostic checks..."
    
    # Check ClickHouse connectivity from Vector
    if docker exec aiops-vector curl -s http://clickhouse:8123/ping 2>/dev/null | grep -q "Ok."; then
        success "Vector can reach ClickHouse"
    else
        error "Vector CANNOT reach ClickHouse"
    fi
    
    # Check recent ClickHouse logs
    warning "Recent ClickHouse logs:"
    docker logs aiops-clickhouse --tail=10 2>/dev/null | grep -v "^$" || echo "No relevant logs"
    
    # Check total records in ClickHouse
    TOTAL_RECORDS=$(docker exec aiops-clickhouse clickhouse-client --query "SELECT count() FROM logs.raw" 2>/dev/null || echo "ERROR")
    if [ "$TOTAL_RECORDS" != "ERROR" ]; then
        log "Total records in ClickHouse: $TOTAL_RECORDS"
        if [ "$TOTAL_RECORDS" -eq 0 ]; then
            error "ClickHouse has NO records at all - Vector-to-ClickHouse flow is broken"
        fi
    fi
fi

echo ""

# Step 6: Understanding Benthos Flow  
log "Step 6: Understanding Benthos Data Flow..."

log "Checking Benthos processing statistics..."
BENTHOS_STATS=$(curl -s http://localhost:4195/stats 2>/dev/null | jq -r '.input.total_received // "N/A"' 2>/dev/null || echo "N/A")
if [ "$BENTHOS_STATS" != "N/A" ]; then
    success "Benthos: Processing stats available (received: $BENTHOS_STATS)"
else
    warning "Benthos: Stats not available or Benthos not responding"
fi

log "Note: Benthos processes ANOMALY events, not normal messages"
log "Your test message follows: Syslog → Vector → ClickHouse (normal flow)"
log "For Benthos processing, message needs: ClickHouse → VictoriaMetrics → Anomaly Detection → NATS → Benthos"

echo ""

# Step 7: SNMP Data Flow Check
log "Step 7: Checking SNMP Data Flow..."

SNMP_LOGS=$(docker logs aiops-vector --tail=50 2>/dev/null | grep -i "snmp" | wc -l)
if [ "$SNMP_LOGS" -gt 0 ]; then
    success "Vector: Found $SNMP_LOGS SNMP-related log entries"
    log "Recent SNMP processing:"
    docker logs aiops-vector --tail=50 2>/dev/null | grep -i "snmp" | tail -3
else
    log "Vector: No SNMP data processed (normal if no SNMP collector active)"
fi

# Check network device collector
if curl -s http://localhost:8088/metrics >/dev/null 2>&1; then
    success "Network Device Collector: Responding on port 8088"
else
    log "Network Device Collector: Not responding (normal if not started)"
fi

echo ""

# Step 8: Summary and Recommendations
echo "============================================="
echo "📊 VALIDATION SUMMARY"
echo "============================================="

if [ "$CLICKHOUSE_RECORDS" -gt 0 ]; then
    success "END-TO-END VALIDATION: SUCCESSFUL"
    echo ""
    success "✅ Message sent via syslog (UDP/TCP)"
    success "✅ Message received and processed by Vector"
    success "✅ Message stored in ClickHouse"
    success "✅ Complete data flow verified"
    
    echo ""
    echo "🎯 YOUR TEST MESSAGE COMPLETED THE FULL PIPELINE:"
    echo "   Test Message → Syslog → Vector → ClickHouse ✅"
    
    echo ""
    echo "📋 TRACKING ID FOR YOUR RECORDS:"
    echo "   $TRACKING_ID"
    
else
    error "END-TO-END VALIDATION: FAILED"
    echo ""
    success "✅ Message sent via syslog (UDP/TCP)"
    if [ "$VECTOR_LOGS" -gt 0 ]; then
        success "✅ Message received by Vector"
    else
        error "❌ Message NOT received by Vector"
    fi
    error "❌ Message NOT stored in ClickHouse"
    
    echo ""
    echo "🔧 TROUBLESHOOTING NEXT STEPS:"
    echo "   1. Check Vector ClickHouse authentication (now fixed)"
    echo "   2. Restart Vector container: docker compose restart vector"
    echo "   3. Wait 30 seconds and run this script again"
    echo "   4. Check Vector logs: docker logs aiops-vector --tail=50"
fi

echo ""
echo "📚 For detailed troubleshooting, see: COMPREHENSIVE_END_TO_END_VALIDATION.md"
echo "============================================="