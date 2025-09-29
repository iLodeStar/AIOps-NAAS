#!/bin/bash

# Quick NATS Topic Configuration Validation
# This script validates that NATS topics are correctly configured across all services

echo "🔍 Validating NATS Topic Configuration..."

# Define expected pipeline flow
declare -A expected_flow
expected_flow["Vector"]="logs.anomalous"
expected_flow["Anomaly Detection"]="anomaly.detected"  
expected_flow["Benthos Enrichment"]="anomaly.detected.enriched"
expected_flow["Enhanced Anomaly Detection"]="anomaly.detected.enriched.final"
expected_flow["Benthos Correlation"]="incidents.created"

echo ""
echo "📋 Expected Sequential Anomaly Pipeline Flow:"
echo "  Vector → logs.anomalous"
echo "  Anomaly Detection Service → anomaly.detected" 
echo "  Benthos Anomaly Enrichment → anomaly.detected.enriched"
echo "  Enhanced Anomaly Detection → anomaly.detected.enriched.final"
echo "  Benthos Correlation → incidents.created"
echo "  Incident API (consumes incidents.created)"
echo ""
echo "📋 Existing Telemetry Pipeline (Preserved):"
echo "  Raw Telemetry → Benthos Data Enrichment → enriched.for_anomaly_detection"
echo "  Enhanced Anomaly Detection → anomaly.detected.enriched.final"
echo ""

# Check Vector configuration
echo "🔍 Checking Vector Configuration..."
if grep -q "subject.*logs\.anomalous" vector/vector.toml; then
    echo "  ✅ Vector publishes to logs.anomalous"
else
    echo "  ❌ Vector does not publish to logs.anomalous"
fi

# Check Anomaly Detection Service 
echo "🔍 Checking Anomaly Detection Service..."
if grep -q "logs\.anomalous" services/anomaly-detection/anomaly_service.py && grep -q "anomaly\.detected" services/anomaly-detection/anomaly_service.py; then
    echo "  ✅ Anomaly Detection: subscribes to logs.anomalous, publishes to anomaly.detected"
else
    echo "  ❌ Anomaly Detection: incorrect topic configuration"
fi

# Check Benthos Enrichment
echo "🔍 Checking Benthos Data Enrichment Configuration..."
if grep -q "subject.*metrics\.system" benthos/data-enrichment.yaml && grep -q "subject.*enriched\.for_anomaly_detection" benthos/data-enrichment.yaml; then
    echo "  ✅ Benthos Data Enrichment: subscribes to raw telemetry, publishes to enriched.for_anomaly_detection"
else
    echo "  ❌ Benthos Data Enrichment: incorrect topic configuration"
fi

# Check Benthos Anomaly Enrichment
echo "🔍 Checking Benthos Anomaly Enrichment Configuration..."
if grep -q "subject.*anomaly\.detected" benthos/anomaly-enrichment.yaml && grep -q "subject.*anomaly\.detected\.enriched" benthos/anomaly-enrichment.yaml; then
    echo "  ✅ Benthos Anomaly Enrichment: subscribes to anomaly.detected, publishes to anomaly.detected.enriched"
else
    echo "  ❌ Benthos Anomaly Enrichment: incorrect topic configuration"
fi

# Check Enhanced Anomaly Detection
echo "🔍 Checking Enhanced Anomaly Detection Service..."
if grep -q "anomaly\.detected\.enriched" services/enhanced-anomaly-detection/anomaly_service.py && grep -q "anomaly\.detected\.enriched\.final" services/enhanced-anomaly-detection/anomaly_service.py; then
    echo "  ✅ Enhanced Anomaly Detection: subscribes to anomaly.detected.enriched, publishes to anomaly.detected.enriched.final"
else
    echo "  ❌ Enhanced Anomaly Detection: incorrect topic configuration"
fi

# Check Benthos Correlation
echo "🔍 Checking Benthos Correlation Configuration..."
if grep -q "subject.*anomaly\.detected\.enriched\.final" benthos/benthos.yaml && grep -q "subject.*incidents\.created" benthos/benthos.yaml; then
    echo "  ✅ Benthos Correlation: subscribes to anomaly.detected.enriched.final, publishes to incidents.created"
else
    echo "  ❌ Benthos Correlation: incorrect topic configuration"
fi

# Check Incident API
echo "🔍 Checking Incident API Service..."
if grep -q "incidents\.created" services/incident-api/incident_api.py; then
    echo "  ✅ Incident API: subscribes to incidents.created"
else
    echo "  ❌ Incident API: does not subscribe to incidents.created"
fi

echo ""
echo "🔍 Checking for potential topic conflicts..."

# Check that no service subscribes to multiple input topics that would break sequential processing
if grep -A 10 -B 10 "broker:" benthos/benthos.yaml | grep -c "subject:"; then
    echo "  ⚠️  Warning: Benthos Correlation may have multiple input topics (check manually)"
else
    echo "  ✅ Benthos Correlation has single input topic"
fi

if grep -A 10 -B 10 "broker:" benthos/data-enrichment.yaml | grep -c "subject:"; then
    echo "  ⚠️  Warning: Benthos Enrichment may have multiple input topics (check manually)"
else
    echo "  ✅ Benthos Enrichment has single input topic"
fi

echo ""
echo "✅ NATS Topic Validation Complete"
echo ""
echo "💡 To manually verify topic flow:"
echo "   1. Start all services: make up-all"
echo "   2. Run end-to-end test: ./scripts/verify_modular_pipeline.sh"
echo "   3. Monitor stats: python3 scripts/collect_pipeline_stats.py --watch"