#!/bin/bash

# Quick startup and validation script for AIOps NAAS
# This script starts services and validates the Vector-to-ClickHouse data flow

set -e

echo "🚀 STARTING AIOPS NAAS SERVICES"
echo "==============================="

cd "$(dirname "$0")/.."

echo ""
echo "1️⃣  Starting Docker Compose services..."
docker compose up -d

echo ""
echo "2️⃣  Waiting for services to become healthy..."
echo "This may take up to 60 seconds..."

# Wait for services with timeout
timeout=60
elapsed=0

while [ $elapsed -lt $timeout ]; do
    if curl -s http://localhost:8686/health >/dev/null 2>&1 && \
       curl -s http://localhost:8123/ping >/dev/null 2>&1 && \
       curl -s http://localhost:8222/healthz >/dev/null 2>&1; then
        echo "  ✅ Core services are healthy!"
        break
    fi
    
    echo -n "."
    sleep 5
    elapsed=$((elapsed + 5))
done

if [ $elapsed -ge $timeout ]; then
    echo ""
    echo "  ⚠️  Services may still be starting. Continuing with validation..."
fi

echo ""
echo "3️⃣  Service Status Check:"
echo "Vector:     $(curl -s http://localhost:8686/health 2>/dev/null || echo 'Not ready')"
echo "ClickHouse: $(curl -s http://localhost:8123/ping 2>/dev/null || echo 'Not ready')"  
echo "NATS:       $(curl -s http://localhost:8222/healthz 2>/dev/null | jq -r .status 2>/dev/null || echo 'Not ready')"
echo "Benthos:    $(curl -s http://localhost:4195/ping 2>/dev/null || echo 'Not ready')"

echo ""
echo "4️⃣  Testing End-to-End Message Flow..."

# Generate unique tracking ID
TRACKING_ID="STARTUP-$(date +%Y%m%d-%H%M%S)-$(uuidgen | cut -d'-' -f1)"
echo "Using Tracking ID: $TRACKING_ID"

# Send test message via UDP
echo "Sending UDP test message..."
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: STARTUP_TEST $TRACKING_ID UDP message" | nc -u localhost 1514

# Send test message via TCP  
echo "Sending TCP test message..."
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: STARTUP_TEST $TRACKING_ID TCP message" | nc localhost 1515

# Wait for processing
echo "Waiting 15 seconds for message processing..."
sleep 15

echo ""
echo "5️⃣  Validation Results:"

# Check Vector logs
if docker logs aiops-vector --since=60s 2>&1 | grep -q "$TRACKING_ID"; then
    echo "  ✅ Messages found in Vector logs"
else
    echo "  ❌ Messages NOT found in Vector logs"
fi

# Check ClickHouse
CLICKHOUSE_COUNT=$(docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT count() FROM logs.raw WHERE message LIKE '%$TRACKING_ID%'" 2>/dev/null || echo "0")

if [ "$CLICKHOUSE_COUNT" -gt "0" ]; then
    echo "  ✅ Messages found in ClickHouse ($CLICKHOUSE_COUNT records)"
    echo "  📊 Record details:"
    docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 \
        --query="SELECT timestamp, level, message, source, host, service FROM logs.raw WHERE message LIKE '%$TRACKING_ID%' ORDER BY timestamp DESC" 2>/dev/null | sed 's/^/      /'
else
    echo "  ❌ Messages NOT found in ClickHouse"
    echo "  🔍 Run ./scripts/diagnose_clickhouse_issue.sh for detailed diagnostics"
fi

# Check Vector metrics
VECTOR_EVENTS=$(curl -s http://localhost:8686/metrics 2>/dev/null | grep 'vector_component_sent_events_total.*clickhouse' | grep -oE '[0-9]+$' | tail -1 || echo "0")
if [ "$VECTOR_EVENTS" -gt "0" ]; then
    echo "  ✅ Vector processed $VECTOR_EVENTS events to ClickHouse"
else
    echo "  ⚠️  Vector metrics show 0 events sent to ClickHouse"
fi

echo ""
echo "6️⃣  Quick Commands for Manual Testing:"
echo "Generate tracking ID:"
echo "  TRACKING_ID=\"E2E-\$(date +%Y%m%d-%H%M%S)-\$(uuidgen | cut -d'-' -f1)\""
echo ""
echo "Send UDP message:"
echo "  echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) test-service: \$TRACKING_ID\" | nc -u localhost 1514"
echo ""
echo "Send TCP message:"  
echo "  echo \"<14>\$(date '+%b %d %H:%M:%S') \$(hostname) test-service: \$TRACKING_ID\" | nc localhost 1515"
echo ""
echo "Query ClickHouse:"
echo "  docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 \\"
echo "    --query=\"SELECT * FROM logs.raw WHERE message LIKE '%\$TRACKING_ID%'\""

echo ""
echo "🏁 STARTUP COMPLETE"
echo "==================="

if [ "$CLICKHOUSE_COUNT" -gt "0" ]; then
    echo "✅ SUCCESS: End-to-end message flow is working!"
    echo "🌐 Access points:"
    echo "   - Grafana: http://localhost:3000 (admin/admin)"
    echo "   - Vector API: http://localhost:8686/metrics"
    echo "   - NATS Monitor: http://localhost:8222"
    echo "   - Benthos API: http://localhost:4195/stats"
else
    echo "⚠️  ISSUE: Messages not reaching ClickHouse"
    echo "🔧 Next steps:"
    echo "   1. Check service logs: docker compose logs vector clickhouse"
    echo "   2. Run diagnostics: ./scripts/diagnose_clickhouse_issue.sh"
    echo "   3. Review fix guide: cat COMPLETE_CLICKHOUSE_INTEGRATION_FIX.md"
fi