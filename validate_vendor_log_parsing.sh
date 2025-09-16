#!/bin/bash
# Comprehensive validation script for unified network log normalization
# Tests Vector vendor parsing and ClickHouse schema extensions

set -e

echo "🚀 Unified Network Log Normalization Validation"
echo "==============================================="

# Configuration
CLICKHOUSE_URL="http://localhost:8123"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-clickhouse123}"
VECTOR_METRICS_URL="http://localhost:8686/metrics"
VECTOR_HEALTH_URL="http://localhost:8686/health"
TEST_SESSION_ID="VALIDATION-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"

echo "Test Session ID: $TEST_SESSION_ID"
echo ""

# Helper functions
query_clickhouse() {
    local query="$1"
    curl -s -X POST "$CLICKHOUSE_URL/?user=$CLICKHOUSE_USER&password=$CLICKHOUSE_PASSWORD" \
         -H "Content-Type: text/plain" \
         -d "$query"
}

send_syslog_udp() {
    local message="$1"
    local port="${2:-1517}"
    echo "$message" | nc -u localhost "$port"
}

wait_for_processing() {
    local seconds="${1:-8}"
    echo "⏳ Waiting ${seconds}s for Vector processing and ClickHouse ingestion..."
    sleep "$seconds"
}

check_service_health() {
    echo "🔍 Checking service health..."
    
    # Check Vector health
    if curl -s -f "$VECTOR_HEALTH_URL" > /dev/null; then
        echo "✅ Vector is healthy"
    else
        echo "❌ Vector health check failed"
        return 1
    fi
    
    # Check ClickHouse health  
    if query_clickhouse "SELECT 1" | grep -q "1"; then
        echo "✅ ClickHouse is responding"
    else
        echo "❌ ClickHouse health check failed"
        return 1
    fi
    
    echo ""
}

test_schema_extensions() {
    echo "🧪 Testing ClickHouse schema extensions..."
    
    # Check if new columns exist
    schema_query="DESCRIBE logs.raw FORMAT JSONEachRow"
    schema_result=$(query_clickhouse "$schema_query")
    
    required_fields=("vendor" "device_type" "cruise_segment" "facility" "severity" "category" "event_id" "ip_address" "ingestion_time")
    
    for field in "${required_fields[@]}"; do
        if echo "$schema_result" | grep -q "\"name\":\"$field\""; then
            echo "✅ Field '$field' exists in schema"
        else
            echo "❌ Field '$field' missing from schema"
            return 1
        fi
    done
    
    echo ""
}

test_cisco_parsing() {
    echo "🧪 Testing Cisco IOS log parsing..."
    
    # Test Cisco messages with different severity levels and device types
    cisco_messages=(
        "<189>Jan 15 10:30:00 bridge-sw01 %LINK-3-UPDOWN: Interface GigabitEthernet1/1, changed state to up $TEST_SESSION_ID"
        "<188>Jan 15 10:30:01 engine-rtr01 %BGP-4-ADJCHANGE: neighbor 192.168.1.2 Up $TEST_SESSION_ID" 
        "<185>Jan 15 10:30:02 comms-fw01 %SYS-2-MALLOCFAIL: Memory allocation failed $TEST_SESSION_ID"
    )
    
    for message in "${cisco_messages[@]}"; do
        send_syslog_udp "$message"
    done
    
    wait_for_processing 10
    
    # Query results
    cisco_query="SELECT vendor, device_type, facility, severity, category, cruise_segment, host FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' AND vendor = 'cisco' FORMAT JSONEachRow"
    results=$(query_clickhouse "$cisco_query")
    
    if [ -z "$results" ]; then
        echo "❌ No Cisco logs found in ClickHouse"
        return 1
    fi
    
    # Count results
    result_count=$(echo "$results" | wc -l)
    if [ "$result_count" -ge 3 ]; then
        echo "✅ Found $result_count Cisco logs"
    else
        echo "❌ Expected at least 3 Cisco logs, found $result_count"
        return 1
    fi
    
    # Check specific parsing
    if echo "$results" | grep -q '"vendor":"cisco"'; then
        echo "✅ Cisco vendor detected"
    else
        echo "❌ Cisco vendor not detected"
        return 1
    fi
    
    if echo "$results" | grep -q '"device_type":"switch"'; then
        echo "✅ Switch device type detected"
    else
        echo "❌ Switch device type not detected"
    fi
    
    if echo "$results" | grep -q '"cruise_segment":"navigation"'; then
        echo "✅ Navigation cruise segment detected"
    else
        echo "❌ Navigation cruise segment not detected"
    fi
    
    echo ""
}

test_juniper_parsing() {
    echo "🧪 Testing Juniper Junos log parsing..."
    
    juniper_messages=(
        "<187>Jan 15 10:30:03 nav-ex4200 rpd.info: BGP peer 192.168.1.1 changed state $TEST_SESSION_ID"
        "<184>Jan 15 10:30:04 deck-mx960 kernel.warning: Interface xe-0/0/0 link down $TEST_SESSION_ID"
    )
    
    for message in "${juniper_messages[@]}"; do
        send_syslog_udp "$message"
    done
    
    wait_for_processing
    
    juniper_query="SELECT vendor, device_type, facility, severity, cruise_segment FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' AND vendor = 'juniper' FORMAT JSONEachRow"
    results=$(query_clickhouse "$juniper_query")
    
    if [ -n "$results" ]; then
        echo "✅ Juniper logs parsed successfully"
        echo "$results" | head -2
    else
        echo "❌ No Juniper logs found"
        return 1
    fi
    
    echo ""
}

test_fortinet_parsing() {
    echo "🧪 Testing Fortinet FortiOS log parsing..."
    
    fortinet_message='<185>Jan 15 10:30:05 security-fgt100 date=2025-01-15 time=10:30:05 devname="security-fgt100" devid="FGT100F123456789" logid="0000000013" type="traffic" subtype="forward" level="notice" msg="Permitted traffic '"$TEST_SESSION_ID"'"'
    
    send_syslog_udp "$fortinet_message"
    wait_for_processing
    
    fortinet_query="SELECT vendor, device_type, category, event_id, cruise_segment FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' AND vendor = 'fortinet' FORMAT JSONEachRow"
    results=$(query_clickhouse "$fortinet_query")
    
    if [ -n "$results" ]; then
        echo "✅ Fortinet logs parsed successfully"
        echo "$results"
    else
        echo "❌ No Fortinet logs found"
        return 1
    fi
    
    echo ""
}

test_generic_parsing() {
    echo "🧪 Testing generic device classification..."
    
    generic_messages=(
        "<134>Jan 15 10:30:06 guest-ap01 hostapd: Client connected $TEST_SESSION_ID"
        "<132>Jan 15 10:30:07 vsat-modem01 system: Signal strength -85dBm $TEST_SESSION_ID"
        "<138>Jan 15 10:30:08 dining-srv01 application: Service started $TEST_SESSION_ID"
    )
    
    for message in "${generic_messages[@]}"; do
        send_syslog_udp "$message"
    done
    
    wait_for_processing
    
    generic_query="SELECT host, device_type, cruise_segment FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' AND vendor != 'cisco' AND vendor != 'juniper' AND vendor != 'fortinet' FORMAT JSONEachRow"
    results=$(query_clickhouse "$generic_query")
    
    if [ -n "$results" ]; then
        echo "✅ Generic device classification working"
        echo "$results"
    else
        echo "⚠️  No generic logs found (may be parsed as specific vendors)"
    fi
    
    echo ""
}

test_backward_compatibility() {
    echo "🧪 Testing backward compatibility..."
    
    # Send a log that should work with both old and new parsing
    compat_message="<131>Jan 15 10:30:09 api-server01 application: ERROR Database connection failed $TEST_SESSION_ID"
    
    send_syslog_udp "$compat_message"
    wait_for_processing
    
    # Check that basic fields are still populated
    compat_query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' ORDER BY timestamp DESC LIMIT 1 FORMAT JSONEachRow"
    results=$(query_clickhouse "$compat_query")
    
    if [ -n "$results" ]; then
        echo "✅ Backward compatibility maintained"
        echo "$results"
    else
        echo "❌ Backward compatibility test failed"
        return 1
    fi
    
    echo ""
}

test_vector_metrics() {
    echo "🧪 Testing Vector vendor metrics..."
    
    if curl -s -f "$VECTOR_METRICS_URL" > /dev/null; then
        metrics=$(curl -s "$VECTOR_METRICS_URL")
        
        if echo "$metrics" | grep -q "vector_vendor_logs_total"; then
            echo "✅ Vendor metrics are being generated"
            
            # Show some vendor metrics
            echo "📊 Sample vendor metrics:"
            echo "$metrics" | grep "vector_vendor_logs_total" | head -5
        else
            echo "⚠️  Vendor metrics not found (may not be implemented yet)"
        fi
    else
        echo "⚠️  Vector metrics endpoint not accessible"
    fi
    
    echo ""
}

show_summary() {
    echo "📊 Testing Summary"
    echo "=================="
    
    # Count logs by vendor
    summary_query="SELECT vendor, device_type, count() as log_count FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' GROUP BY vendor, device_type ORDER BY log_count DESC FORMAT JSONEachRow"
    summary=$(query_clickhouse "$summary_query")
    
    if [ -n "$summary" ]; then
        echo "📈 Logs processed by vendor/device type:"
        echo "$summary" | jq -r '. | "  \(.vendor)/\(.device_type): \(.log_count) logs"'
        echo ""
        
        # Total count
        total_query="SELECT count() as total FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' FORMAT JSONEachRow"
        total=$(query_clickhouse "$total_query")
        total_count=$(echo "$total" | jq -r '.total')
        echo "🔢 Total test logs processed: $total_count"
        
        # Show cruise segment distribution
        segment_query="SELECT cruise_segment, count() as log_count FROM logs.raw WHERE message LIKE '%$TEST_SESSION_ID%' GROUP BY cruise_segment ORDER BY log_count DESC FORMAT JSONEachRow"
        segments=$(query_clickhouse "$segment_query")
        
        if [ -n "$segments" ]; then
            echo "🚢 Logs by cruise segment:"
            echo "$segments" | jq -r '. | "  \(.cruise_segment): \(.log_count) logs"'
        fi
    else
        echo "❌ No test logs found in summary"
    fi
    
    echo ""
}

cleanup_test_data() {
    echo "🧹 Cleaning up test data..."
    
    cleanup_query="ALTER TABLE logs.raw DELETE WHERE message LIKE '%$TEST_SESSION_ID%'"
    if query_clickhouse "$cleanup_query" > /dev/null 2>&1; then
        echo "✅ Test data cleaned up"
    else
        echo "⚠️  Could not clean up test data (may require OPTIMIZE)"
    fi
    
    echo ""
}

# Main test execution
main() {
    echo "Starting validation at $(date)"
    echo ""
    
    # Pre-flight checks
    if ! command -v nc > /dev/null; then
        echo "❌ netcat (nc) is required for testing"
        exit 1
    fi
    
    if ! command -v curl > /dev/null; then
        echo "❌ curl is required for testing"
        exit 1
    fi
    
    if ! command -v jq > /dev/null; then
        echo "⚠️  jq not found, output formatting will be limited"
    fi
    
    # Run tests
    check_service_health
    test_schema_extensions
    test_cisco_parsing
    test_juniper_parsing  
    test_fortinet_parsing
    test_generic_parsing
    test_backward_compatibility
    test_vector_metrics
    show_summary
    
    # Optional cleanup
    read -p "Clean up test data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_test_data
    fi
    
    echo "✅ Validation completed successfully!"
    echo "🎉 Unified network log normalization is working correctly"
}

# Run main function
main "$@"