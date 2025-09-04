#!/bin/bash

# Comprehensive diagnostic script for ClickHouse Vector integration issue
# This script helps identify why messages appear in Vector logs but don't reach ClickHouse

set -e

echo "🔍 DIAGNOSING VECTOR-TO-CLICKHOUSE ISSUE"
echo "========================================"

# Generate unique tracking ID for this diagnostic session
TRACKING_ID="DIAG-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "🏷️  Diagnostic Tracking ID: $TRACKING_ID"

echo ""
echo "1️⃣  CHECKING SERVICE HEALTH"
echo "----------------------------"

# Check Vector health
echo "Vector Health:"
if curl -s http://localhost:8686/health > /dev/null 2>&1; then
    echo "  ✅ Vector API responding"
    curl -s http://localhost:8686/health | jq -r '.status // empty' || echo "  ⚠️  Vector health check returned non-JSON"
else
    echo "  ❌ Vector API not responding"
fi

# Check ClickHouse health  
echo "ClickHouse Health:"
if curl -s http://localhost:8123/ping > /dev/null 2>&1; then
    echo "  ✅ ClickHouse responding"
    echo "  Response: $(curl -s http://localhost:8123/ping)"
else
    echo "  ❌ ClickHouse not responding"
fi

echo ""
echo "2️⃣  CHECKING CLICKHOUSE AUTHENTICATION"
echo "--------------------------------------"

# Test ClickHouse authentication with Docker Compose credentials
echo "Testing ClickHouse auth with default credentials:"
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT 1" 2>/dev/null && echo "  ✅ Auth with default/clickhouse123 works" || echo "  ❌ Auth with default/clickhouse123 failed"

# Check current ClickHouse users
echo "Current ClickHouse users:"
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT name, auth_type FROM system.users" 2>/dev/null || echo "  ⚠️  Could not list users"

echo ""
echo "3️⃣  CHECKING VECTOR CONFIGURATION & ENVIRONMENT"
echo "------------------------------------------------"

# Check Vector container environment variables
echo "Vector container ClickHouse environment variables:"
docker exec aiops-vector env | grep -E "CLICKHOUSE|CH_" || echo "  ⚠️  No ClickHouse env vars found in Vector container"

# Check Vector metrics to see if sink is working
echo "Vector ClickHouse sink metrics:"
if curl -s http://localhost:8686/metrics > /dev/null 2>&1; then
    curl -s http://localhost:8686/metrics | grep -E "vector_component_.*clickhouse" | head -5 || echo "  ⚠️  No ClickHouse sink metrics found"
    
    echo "Vector error metrics:"
    curl -s http://localhost:8686/metrics | grep -E "vector_component_errors.*clickhouse" || echo "  ✅ No ClickHouse-related errors in metrics"
else
    echo "  ❌ Cannot retrieve Vector metrics"
fi

echo ""
echo "4️⃣  TESTING MESSAGE FLOW"
echo "-------------------------"

# Send test message
echo "Sending test message with tracking ID: $TRACKING_ID"
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: DIAGNOSTIC_TEST $TRACKING_ID from diagnostic script" | nc -u localhost 1514

# Wait for processing
echo "Waiting 10 seconds for Vector processing..."
sleep 10

# Check if message appears in Vector logs
echo "Checking Vector logs for tracking ID:"
if docker logs aiops-vector --since=30s 2>&1 | grep -q "$TRACKING_ID"; then
    echo "  ✅ Message found in Vector logs"
    echo "  Raw message:"
    docker logs aiops-vector --since=30s 2>&1 | grep "$TRACKING_ID" | head -2 | sed 's/^/    /'
else
    echo "  ❌ Message NOT found in Vector logs"
fi

echo ""
echo "5️⃣  CHECKING CLICKHOUSE DATA INGESTION"
echo "--------------------------------------"

# Check if message reached ClickHouse
echo "Checking ClickHouse for tracking ID:"
CLICKHOUSE_RESULT=$(docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT count() FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null || echo "0")

if [ "$CLICKHOUSE_RESULT" = "0" ]; then
    echo "  ❌ Message NOT found in ClickHouse"
    
    # Additional diagnostics
    echo ""
    echo "📊 ADDITIONAL CLICKHOUSE DIAGNOSTICS"
    echo "------------------------------------"
    
    # Check table structure
    echo "ClickHouse table structure:"
    docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="DESCRIBE logs.raw" 2>/dev/null | sed 's/^/  /' || echo "  ⚠️  Could not describe table"
    
    # Check recent records count
    echo "Recent records in ClickHouse (last 1 hour):"
    RECENT_COUNT=$(docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT count() FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR" 2>/dev/null || echo "unknown")
    echo "  Total recent records: $RECENT_COUNT"
    
    # Check if any syslog records exist
    SYSLOG_COUNT=$(docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT count() FROM logs.raw WHERE source = 'syslog'" 2>/dev/null || echo "unknown")
    echo "  Syslog records: $SYSLOG_COUNT"
    
    # Show sample recent records
    echo "Sample recent records:"
    docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, level, message, source, host FROM logs.raw ORDER BY timestamp DESC LIMIT 3" 2>/dev/null | sed 's/^/  /' || echo "  ⚠️  Could not retrieve sample records"
    
else
    echo "  ✅ Message FOUND in ClickHouse ($CLICKHOUSE_RESULT records)"
    echo "  Record details:"
    docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC LIMIT 1" 2>/dev/null | sed 's/^/    /'
fi

echo ""
echo "6️⃣  VECTOR SINK HEALTH & ERROR ANALYSIS"
echo "---------------------------------------"

# Check Vector component health
echo "Vector component health:"
if curl -s http://localhost:8686/metrics > /dev/null 2>&1; then
    
    # Check for processing errors
    ERROR_COUNT=$(curl -s http://localhost:8686/metrics | grep -E "vector_component_errors.*clickhouse" | grep -oE '[0-9]+$' | tail -1 || echo "0")
    if [ "$ERROR_COUNT" = "0" ]; then
        echo "  ✅ No Vector processing errors for ClickHouse sink"
    else
        echo "  ⚠️  Vector processing errors detected: $ERROR_COUNT"
    fi
    
    # Check events processed
    EVENTS_IN=$(curl -s http://localhost:8686/metrics | grep 'vector_component_received_events_total.*clickhouse' | grep -oE '[0-9]+$' | tail -1 || echo "0")
    EVENTS_OUT=$(curl -s http://localhost:8686/metrics | grep 'vector_component_sent_events_total.*clickhouse' | grep -oE '[0-9]+$' | tail -1 || echo "0")
    
    echo "  Events received by ClickHouse sink: $EVENTS_IN"
    echo "  Events sent by ClickHouse sink: $EVENTS_OUT"
    
    if [ "$EVENTS_IN" != "$EVENTS_OUT" ] && [ "$EVENTS_IN" != "0" ]; then
        echo "  ⚠️  Mismatch between received and sent events - potential processing issue"
    fi
    
else
    echo "  ❌ Cannot retrieve Vector metrics for analysis"
fi

echo ""
echo "7️⃣  POTENTIAL FIXES TO TRY"
echo "--------------------------"

if [ "$CLICKHOUSE_RESULT" = "0" ]; then
    echo "Based on diagnostics, try these fixes in order:"
    echo ""
    echo "1. Restart Vector service:"
    echo "   docker compose restart vector"
    echo ""
    echo "2. Check Vector container logs for errors:"
    echo "   docker logs aiops-vector --since=5m | grep -i error"
    echo ""
    echo "3. Test ClickHouse connection from Vector container:"
    echo "   docker exec aiops-vector curl -u default:clickhouse123 http://clickhouse:8123/ping"
    echo ""
    echo "4. Check if Vector transform is causing issues:"
    echo "   docker logs aiops-vector --since=5m | grep -A5 -B5 'transform'"
    echo ""
    echo "5. Manually test ClickHouse insertion:"
    echo "   docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 \\"
    echo "     --query=\"INSERT INTO logs.raw (level, message, source, host, service, raw_log, labels) VALUES ('INFO', 'Manual test', 'manual', 'test-host', 'test-service', '{}', {})\""
else
    echo "✅ Everything appears to be working correctly!"
    echo "   Your messages are reaching ClickHouse successfully."
fi

echo ""
echo "🏁 DIAGNOSTIC COMPLETE"
echo "======================"
echo "Tracking ID used: $TRACKING_ID"
echo "Check ClickHouse for this ID to verify if the diagnostic message made it through."