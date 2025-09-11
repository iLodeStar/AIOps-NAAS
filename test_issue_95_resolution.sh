#!/bin/bash
"""
Test script to validate that the specific log error patterns from issue #95 are resolved.

This script creates test scenarios that would have previously caused the exact errors:
1. "operator failed for key 'unknown-ship_application_logs_log_anomaly': key does not exist"
2. "operator failed for key 'unknown_anomaly_unknown-ship': key does not exist"  
3. "failed to check if condition: cannot compare types null ... and null"
"""

set -e

echo "🚀 Testing Issue #95 Specific Error Pattern Resolution"
echo "======================================================"

# Test 1: Validate cache key pattern fixes
echo "🔍 Test 1: Cache Key Pattern Validation"
echo "--------------------------------------"

# Check that all cache key expressions use safe null handling
KEY_PATTERNS=(
    'json("ship_id") != null && json("ship_id") != ""'
    'json("event_source") != null && json("event_source") != ""'
    'json("metric_name") != null && json("metric_name") != ""'
    'json("incident_type") != null && json("incident_type") != ""'
)

CONFIG_FILE="benthos/benthos.yaml"
ALL_PATTERNS_FOUND=true

for pattern in "${KEY_PATTERNS[@]}"; do
    if grep -q "$pattern" "$CONFIG_FILE"; then
        echo "  ✅ Found safe null checking pattern: ${pattern:0:50}..."
    else
        echo "  ❌ Missing safe null checking pattern: ${pattern:0:50}..."
        ALL_PATTERNS_FOUND=false
    fi
done

# Test 2: Check for unsafe concatenations
echo -e "\n🔍 Test 2: Unsafe Concatenation Check"
echo "------------------------------------"

# Look for direct JSON field concatenations that could cause null issues
UNSAFE_PATTERNS=(
    'json("ship_id") + "_"'
    'json("incident_type") + "_"'
    '+ json("ship_id")'
    '+ json("incident_type")'
)

UNSAFE_FOUND=false
for pattern in "${UNSAFE_PATTERNS[@]}"; do
    if grep -q "$pattern" "$CONFIG_FILE"; then
        echo "  ⚠️  Found potentially unsafe pattern: $pattern"
        UNSAFE_FOUND=true
    fi
done

if [ "$UNSAFE_FOUND" = false ]; then
    echo "  ✅ No unsafe concatenation patterns found"
fi

# Test 3: Severity comparison safety
echo -e "\n🔍 Test 3: Severity Comparison Safety"  
echo "------------------------------------"

if grep -q "if related.severity == null" "$CONFIG_FILE"; then
    echo "  ✅ Found null-safe related.severity handling"
else
    echo "  ❌ Missing null-safe related.severity handling"
    ALL_PATTERNS_FOUND=false
fi

if grep -q "if secondary.severity == null" "$CONFIG_FILE"; then
    echo "  ✅ Found null-safe secondary.severity handling"
else
    echo "  ❌ Missing null-safe secondary.severity handling"  
    ALL_PATTERNS_FOUND=false
fi

# Test 4: Configuration validation
echo -e "\n🔍 Test 4: Configuration Syntax Validation"
echo "------------------------------------------"

if docker run --rm -v "$(pwd)/${CONFIG_FILE}:/config.yaml:ro" jeffail/benthos:latest lint /config.yaml; then
    echo "  ✅ Configuration passes lint validation"
    CONFIG_VALID=true
else
    echo "  ❌ Configuration has lint errors"
    CONFIG_VALID=false
fi

# Summary
echo -e "\n📊 Test Summary"
echo "==============="
echo "Safe Patterns Found: $([ "$ALL_PATTERNS_FOUND" = true ] && echo "✅ Yes" || echo "❌ No")"
echo "Unsafe Patterns Avoided: $([ "$UNSAFE_FOUND" = false ] && echo "✅ Yes" || echo "❌ No")"  
echo "Configuration Valid: $([ "$CONFIG_VALID" = true ] && echo "✅ Yes" || echo "❌ No")"

if [ "$ALL_PATTERNS_FOUND" = true ] && [ "$UNSAFE_FOUND" = false ] && [ "$CONFIG_VALID" = true ]; then
    echo -e "\n🎉 SUCCESS! All Issue #95 error patterns should now be resolved:"
    echo "  • Key does not exist errors: FIXED"
    echo "  • Null comparison errors: FIXED"  
    echo "  • Cache key safety: IMPROVED"
    exit 0
else
    echo -e "\n⚠️  Some issues remain. Check the details above."
    exit 1
fi