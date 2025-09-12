#!/bin/bash

# Comprehensive diagnostic script for incomplete incident data issue
# This script helps trace where missing data should originate in the pipeline
# Address issue where incidents show unknown-ship, unknown_service, unknown_metric

set -e

echo "🔍 INCIDENT DATA COMPLETENESS DIAGNOSTIC"
echo "========================================"
echo "This script traces data through the pipeline to identify missing field sources"
echo ""

# Generate tracking ID for this diagnostic session
TRACKING_ID="DATA-TRACE-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "🏷️  Diagnostic Tracking ID: $TRACKING_ID"
echo ""

echo "1️⃣  CHECKING SERVICE HEALTH & BASIC CONNECTIVITY"
echo "------------------------------------------------"

# Check Vector health
echo "Vector Service:"
if curl -s http://localhost:8686/health > /dev/null 2>&1; then
    echo "  ✅ Vector API responding"
    # Get Vector metrics to see component health
    echo "  Component Status:"
    curl -s http://localhost:8686/metrics | grep "vector_component_sent_events_total" | head -3 | sed 's/^/    /'
else
    echo "  ❌ Vector API not responding - Vector may not be running"
fi

# Check ClickHouse health  
echo ""
echo "ClickHouse Service:"
if docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT 1" 2>/dev/null > /dev/null; then
    echo "  ✅ ClickHouse responding with admin/admin credentials"
else
    echo "  ❌ ClickHouse not responding with admin/admin credentials"
fi

# Check NATS health
echo ""
echo "NATS Service:"
if docker exec aiops-nats nats-server --help > /dev/null 2>&1; then
    echo "  ✅ NATS container accessible"
else
    echo "  ❌ NATS container not accessible"
fi

echo ""
echo "2️⃣  ANALYZING CURRENT INCIDENT DATA QUALITY"
echo "-------------------------------------------"

# Check recent incidents and their data completeness
echo "Recent incidents in ClickHouse:"
RECENT_INCIDENTS=$(docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT count() FROM logs.incidents WHERE created_at > now() - INTERVAL 1 HOUR" 2>/dev/null || echo "0")
echo "  Total incidents in last hour: $RECENT_INCIDENTS"

if [ "$RECENT_INCIDENTS" != "0" ]; then
    echo ""
    echo "  Sample recent incident data quality:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
    SELECT 
        incident_id,
        ship_id,
        service,
        metric_name,
        metric_value,
        anomaly_score,
        host,
        event_source
    FROM (
        SELECT 
            incident_id,
            ship_id,
            service,
            metric_name,
            metric_value,
            anomaly_score,
            JSONExtractString(metadata, 'host') as host,
            JSONExtractString(metadata, 'event_source') as event_source
        FROM logs.incidents 
        ORDER BY created_at DESC 
        LIMIT 1
    )
    " 2>/dev/null | sed 's/^/    /' || echo "    ⚠️  Could not retrieve incident details"

    echo ""
    echo "  Data quality analysis for recent incidents:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
    SELECT
        'Ship ID Quality' as field,
        countIf(ship_id != 'unknown-ship') as complete_count,
        countIf(ship_id = 'unknown-ship') as fallback_count,
        count() as total_count
    FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
    UNION ALL
    SELECT
        'Service Quality' as field,
        countIf(service != 'unknown_service') as complete_count,
        countIf(service = 'unknown_service') as fallback_count,
        count() as total_count  
    FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
    UNION ALL
    SELECT
        'Metric Name Quality' as field,
        countIf(metric_name != 'unknown_metric') as complete_count,
        countIf(metric_name = 'unknown_metric') as fallback_count,
        count() as total_count
    FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
    " 2>/dev/null | sed 's/^/    /' || echo "    ⚠️  Could not analyze data quality"
fi

echo ""
echo "3️⃣  TRACING DATA SOURCES - VECTOR INPUTS"
echo "----------------------------------------"

echo "Vector input sources (where raw data should come from):"

echo ""
echo "  Host Metrics Source:"
curl -s http://localhost:8686/metrics | grep "vector_component_received_events_total.*host_metrics" && echo "    ✅ Host metrics being received" || echo "    ❌ No host metrics being received"

echo ""
echo "  Syslog Sources:"
curl -s http://localhost:8686/metrics | grep "vector_component_received_events_total.*syslog" && echo "    ✅ Syslog data being received" || echo "    ❌ No syslog data being received"

echo ""
echo "  NATS Sources:"
curl -s http://localhost:8686/metrics | grep "vector_component_received_events_total.*nats" && echo "    ✅ NATS data being received" || echo "    ❌ No NATS data being received"

echo ""
echo "4️⃣  CHECKING VECTOR TO CLICKHOUSE DATA FLOW"
echo "-------------------------------------------"

echo "Recent data in ClickHouse logs.raw table:"
RAW_COUNT=$(docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT count() FROM logs.raw WHERE timestamp > now() - INTERVAL 1 HOUR" 2>/dev/null || echo "0")
echo "  Total raw log entries in last hour: $RAW_COUNT"

if [ "$RAW_COUNT" != "0" ]; then
    echo ""
    echo "  Sample raw data field population:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
    SELECT 
        source,
        count() as count,
        uniq(host) as unique_hosts,
        uniq(service) as unique_services,
        countIf(host != 'unknown') as valid_hosts,
        countIf(service != 'unknown') as valid_services
    FROM logs.raw 
    WHERE timestamp > now() - INTERVAL 1 HOUR
    GROUP BY source
    ORDER BY count DESC
    " 2>/dev/null | sed 's/^/    /' || echo "    ⚠️  Could not analyze raw data"

    echo ""
    echo "  Sample raw log entries with field details:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
    SELECT 
        timestamp,
        source,
        host,
        service,
        left(message, 50) as message_preview,
        level
    FROM logs.raw 
    ORDER BY timestamp DESC 
    LIMIT 3
    " 2>/dev/null | sed 's/^/    /' || echo "    ⚠️  Could not retrieve raw log samples"
fi

echo ""
echo "5️⃣  CHECKING NATS DATA FLOW FOR ANOMALY DETECTION"
echo "--------------------------------------------------"

echo "Testing NATS anomaly detection data flow..."

# Check if anomaly detection service is publishing events
echo ""
echo "  Checking if anomaly-detection service is running:"
if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo "    ✅ Anomaly detection service responding"
    # Get some metrics from the anomaly service
    curl -s http://localhost:8081/metrics 2>/dev/null | head -3 | sed 's/^/      /' || echo "    ⚠️  No metrics endpoint available"
else
    echo "    ❌ Anomaly detection service not responding"
fi

echo ""
echo "6️⃣  DEVICE REGISTRY INTEGRATION TEST"  
echo "-----------------------------------"

echo "Testing device registry for ship_id resolution:"
if curl -s http://localhost:8082/health > /dev/null 2>&1; then
    echo "  ✅ Device registry service responding"
    
    # Test hostname resolution
    echo ""
    echo "  Testing hostname resolution examples:"
    for hostname in "dhruv-system-01" "ship-01" "unknown-host" "localhost"; do
        response=$(curl -s "http://localhost:8082/lookup/$hostname" 2>/dev/null || echo '{"error": "connection failed"}')
        echo "    $hostname -> $(echo $response | jq -r '.mapping.ship_id // "no mapping"')"
    done
else
    echo "  ❌ Device registry service not responding"
    echo "    This would cause ship_id to fallback to 'unknown-ship'"
fi

echo ""
echo "7️⃣  BENTHOS CORRELATION SERVICE CHECK"
echo "------------------------------------"

echo "Checking Benthos correlation service:"
if curl -s http://localhost:4195/ping > /dev/null 2>&1; then
    echo "  ✅ Benthos API responding"
    
    # Check Benthos metrics for data processing
    echo ""
    echo "  Benthos processing metrics:"
    curl -s http://localhost:4195/metrics 2>/dev/null | grep -E "(input|output|processed)" | head -5 | sed 's/^/    /' || echo "    ⚠️  Could not retrieve Benthos metrics"
else
    echo "  ❌ Benthos API not responding"
fi

echo ""
echo "8️⃣  GENERATING TEST DATA TO TRACE PIPELINE"
echo "-----------------------------------------"

echo "Generating test data with tracking ID: $TRACKING_ID"

# Test 1: Send a syslog message with proper fields
echo ""
echo "  Test 1: Sending test syslog message with tracking ID..."
echo "<14>$(date '+%b %d %H:%M:%S') test-ship-01 test-service: DATA_TRACE_TEST tracking_id=$TRACKING_ID metric_name=cpu_usage metric_value=85.5 level=ERROR" | nc -u localhost 1514 2>/dev/null && echo "    ✅ Syslog message sent" || echo "    ❌ Failed to send syslog message"

# Wait for processing
echo "  Waiting 10 seconds for pipeline processing..."
sleep 10

# Check if test data made it to ClickHouse raw logs
echo ""
echo "  Checking if test data reached ClickHouse logs.raw:"
RAW_TEST_COUNT=$(docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT count() FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null || echo "0")
echo "    Test records in logs.raw: $RAW_TEST_COUNT"

if [ "$RAW_TEST_COUNT" != "0" ]; then
    echo "    ✅ Test data found in raw logs - Vector pipeline working"
    echo "    Raw data details:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="
    SELECT 
        timestamp, source, host, service, level, left(message, 100) as message 
    FROM logs.raw 
    WHERE message LIKE '%$TRACKING_ID%' 
    LIMIT 1
    " 2>/dev/null | sed 's/^/      /'
else
    echo "    ❌ Test data NOT found in raw logs - Vector pipeline issue"
fi

echo ""
echo "9️⃣  RECOMMENDATIONS BASED ON FINDINGS"
echo "------------------------------------"

echo "Based on this diagnostic, here are the likely issues and solutions:"
echo ""

if [ "$RAW_COUNT" = "0" ]; then
    echo "🚨 CRITICAL: No data reaching ClickHouse from Vector"
    echo "   - Check Vector configuration and ClickHouse connectivity"
    echo "   - Verify Vector sinks are properly configured"
    echo "   - Check Vector logs: docker logs aiops-vector"
fi

if [ "$RAW_TEST_COUNT" = "0" ]; then
    echo "🚨 CRITICAL: Vector not processing syslog data"
    echo "   - Vector syslog source may not be configured correctly"
    echo "   - Check if Vector container port 1514 is accessible"
    echo "   - Verify Vector transforms are working"
fi

echo ""
echo "🔧 TYPICAL MISSING DATA SOURCES:"
echo ""
echo "Field: ship_id (currently: unknown-ship)"
echo "  Should come from: Device registry lookup using hostname"
echo "  Required: Device registry service at localhost:8082"
echo "  Fallback: Hostname parsing (e.g., 'ship-01' -> 'ship-01')"
echo ""
echo "Field: service (currently: unknown_service)"  
echo "  Should come from: Application logs 'appname' field or Vector service mapping"
echo "  Required: Proper syslog/application log format with service identifier"
echo "  Fallback: Parse from log source or message content"
echo ""
echo "Field: metric_name (currently: unknown_metric)"
echo "  Should come from: Anomaly detection service when publishing anomalies" 
echo "  Required: Anomaly detection service properly identifying metric names"
echo "  Fallback: Extract from log message or metadata"
echo ""
echo "Field: host (currently: unknown)"
echo "  Should come from: Vector transforms extracting hostname from logs"
echo "  Required: Proper hostname in syslog messages or metric labels"
echo "  Fallback: Container hostname or system hostname"
echo ""

echo "📋 NEXT DEBUGGING STEPS:"
echo "1. Check Vector logs: docker logs aiops-vector"
echo "2. Check Benthos logs: docker logs aiops-benthos"
echo "3. Verify device registry has proper hostname mappings"
echo "4. Send test data with proper field structure"
echo "5. Monitor NATS subjects for anomaly events"
echo ""
echo "🔍 Diagnostic complete - Tracking ID: $TRACKING_ID"