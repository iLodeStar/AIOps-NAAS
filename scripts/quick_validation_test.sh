#!/bin/bash
#
# Quick Validation Test Script - Demonstrates Working Message Tracking
# This script validates the fixes for Vector UDP syslog reception
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE} Vector UDP Syslog Validation Test${NC}"
echo -e "${BLUE}=============================================${NC}"

# Generate tracking ID
TRACKING_ID="TEST-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo -e "${GREEN}Tracking ID: $TRACKING_ID${NC}"

echo -e "\n${BLUE}Step 1: Checking Vector Configuration${NC}"
echo "Verifying Vector is configured for UDP syslog..."

# Check if Vector configuration uses UDP
if docker exec aiops-vector cat /etc/vector/vector.toml | grep -A 2 "\[sources.syslog\]" | grep "mode.*=.*\"udp\"" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Vector is configured for UDP mode${NC}"
else
    echo -e "${RED}❌ Vector is NOT configured for UDP mode${NC}"
    echo "Current Vector syslog configuration:"
    docker exec aiops-vector cat /etc/vector/vector.toml | grep -A 3 "\[sources.syslog\]" || echo "Could not read Vector config"
    exit 1
fi

echo -e "\n${BLUE}Step 2: Checking Services Health${NC}"

# Check Vector health
if curl -sf http://localhost:8686/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Vector is healthy${NC}"
else
    echo -e "${RED}❌ Vector is not responding${NC}"
    exit 1
fi

# Check ClickHouse health  
if curl -sf http://localhost:8123/ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ ClickHouse is healthy${NC}"
else
    echo -e "${RED}❌ ClickHouse is not responding${NC}"
    exit 1
fi

echo -e "\n${BLUE}Step 3: Sending Test Message via UDP${NC}"
echo "Command: echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) test: VALIDATION $TRACKING_ID message\" | nc -u localhost 1514"

# Send test message via UDP
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test: VALIDATION $TRACKING_ID message" | nc -u localhost 1514

if [[ $? -eq 0 ]]; then
    echo -e "${GREEN}✅ Message sent successfully via UDP${NC}"
else
    echo -e "${RED}❌ Failed to send message${NC}"
    exit 1
fi

echo -e "\n${BLUE}Step 4: Waiting for Vector Processing${NC}"
echo "Waiting 10 seconds for message processing..."
sleep 10

echo -e "\n${BLUE}Step 5: Checking Vector Metrics${NC}"
echo "Checking if Vector received and processed the message..."

# Check Vector metrics
EVENTS_IN=$(curl -s http://localhost:8686/metrics | grep 'vector_events_in_total{component_id="syslog"' | tail -1 | awk '{print $2}')
EVENTS_OUT=$(curl -s http://localhost:8686/metrics | grep 'vector_events_out_total{component_id="syslog_for_logs"' | tail -1 | awk '{print $2}')

echo "Vector Input Events (syslog): ${EVENTS_IN:-0}"
echo "Vector Output Events (syslog_for_logs): ${EVENTS_OUT:-0}"

if [[ -n "$EVENTS_IN" ]] && [[ "$EVENTS_IN" -gt 0 ]]; then
    echo -e "${GREEN}✅ Vector is receiving messages${NC}"
else
    echo -e "${RED}❌ Vector is not receiving messages${NC}"
fi

echo -e "\n${BLUE}Step 6: Searching ClickHouse for Message${NC}"
echo "Looking for tracking ID in ClickHouse logs.raw table..."

# Search ClickHouse for the message
CLICKHOUSE_RESULT=$(docker exec aiops-clickhouse clickhouse-client --query "SELECT count(*) FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null)

if [[ "$CLICKHOUSE_RESULT" =~ ^[0-9]+$ ]] && [[ "$CLICKHOUSE_RESULT" -gt 0 ]]; then
    echo -e "${GREEN}✅ Found $CLICKHOUSE_RESULT message(s) in ClickHouse${NC}"
    
    # Show the actual message
    echo -e "\n${BLUE}Message Details:${NC}"
    docker exec aiops-clickhouse clickhouse-client --query "SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' LIMIT 1 FORMAT Vertical" 2>/dev/null || echo "Could not retrieve message details"
else
    echo -e "${RED}❌ Message not found in ClickHouse${NC}"
    echo "ClickHouse query result: $CLICKHOUSE_RESULT"
fi

echo -e "\n${BLUE}Step 7: Validation Summary${NC}"
echo -e "${GREEN}===============================================${NC}"

if [[ "$CLICKHOUSE_RESULT" =~ ^[0-9]+$ ]] && [[ "$CLICKHOUSE_RESULT" -gt 0 ]]; then
    echo -e "${GREEN}🎉 END-TO-END VALIDATION SUCCESSFUL!${NC}"
    echo -e "${GREEN}✅ Vector UDP Configuration: Working${NC}"  
    echo -e "${GREEN}✅ Message Processing: Working${NC}"
    echo -e "${GREEN}✅ ClickHouse Storage: Working${NC}"
    echo -e "${GREEN}✅ Message Tracking: Working${NC}"
    echo -e "\n${BLUE}Your message successfully traveled:${NC}"
    echo -e "   Syslog → Vector (UDP:1514) → ClickHouse (logs.raw)"
    echo -e "\n${BLUE}Tracking ID: $TRACKING_ID${NC}"
else
    echo -e "${RED}❌ END-TO-END VALIDATION FAILED${NC}"
    echo -e "${RED}Issue: Message not found in final storage${NC}"
    exit 1
fi

echo -e "${GREEN}===============================================${NC}"