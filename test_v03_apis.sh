#!/bin/bash
# AIOps NAAS v0.3 - API Testing Script
# Tests v0.3 services without requiring full Docker environment

set -e

echo "🚢 AIOps NAAS v0.3 - API Testing Script"
echo "========================================="

# Function to test if a service is running
check_service() {
    local service_name="$1"
    local port="$2"
    local endpoint="$3"
    
    echo -n "🔍 Checking $service_name (port $port)... "
    
    if curl -sf "http://localhost:$port$endpoint" >/dev/null 2>&1; then
        echo "✅ Running"
        return 0
    else
        echo "❌ Not running"
        return 1
    fi
}

# Function to demonstrate API calls
demo_api() {
    local service_name="$1"
    local port="$2"
    
    echo ""
    echo "🔧 Testing $service_name API:"
    echo "----------------------------"
    
    case $service_name in
        "Link Health Service")
            echo "📊 Getting current prediction:"
            curl -s "http://localhost:$port/prediction" | jq '.' || echo "Service not running - would return link quality prediction"
            
            echo ""
            echo "📋 Checking service health:"
            curl -s "http://localhost:$port/health" | jq '.' || echo "Service not running - would return health status"
            
            echo ""
            echo "🎯 Simulating modem data:"
            curl -s -X POST "http://localhost:$port/simulate/modem" \
                -H "Content-Type: application/json" \
                -d '{"snr_db": 8.0, "ber": 0.001, "signal_strength_dbm": -80}' | jq '.' || echo "Service not running - would update modem simulation data"
            ;;
            
        "Remediation Service")
            echo "🛠️  Listing available actions:"
            curl -s "http://localhost:$port/actions" | jq '.' || echo "Service not running - would list remediation actions"
            
            echo ""
            echo "🔄 Testing dry-run execution:"
            curl -s -X POST "http://localhost:$port/execute/bandwidth_reduction?dry_run=true" | jq '.' || echo "Service not running - would execute dry-run"
            
            echo ""
            echo "👤 Checking pending approvals:"
            curl -s "http://localhost:$port/approvals" | jq '.' || echo "Service not running - would show pending approvals"
            ;;
            
        "Open Policy Agent")
            echo "🔒 Testing policy evaluation:"
            curl -s -X POST "http://localhost:$port/v1/data/remediation/allow" \
                -H "Content-Type: application/json" \
                -d '{
                    "input": {
                        "action": {"action_type": "qos_traffic_shaping", "risk_level": "MEDIUM"},
                        "context": {"recent_actions_count": 2}
                    }
                }' | jq '.' || echo "Service not running - would evaluate policy"
            ;;
    esac
}

echo ""
echo "🏥 Service Health Check"
echo "======================="

# Check if Docker Compose services are running
LINK_HEALTH_RUNNING=false
REMEDIATION_RUNNING=false
OPA_RUNNING=false

if check_service "Link Health Service" 8082 "/health"; then
    LINK_HEALTH_RUNNING=true
fi

if check_service "Remediation Service" 8083 "/health"; then
    REMEDIATION_RUNNING=true
fi

if check_service "Open Policy Agent" 8181 "/health"; then
    OPA_RUNNING=true
fi

# Demonstrate APIs
if [ "$LINK_HEALTH_RUNNING" = true ]; then
    demo_api "Link Health Service" 8082
else
    echo ""
    echo "📊 Link Health Service Demo (Offline):"
    echo "-------------------------------------"
    echo "🔧 Would provide:"
    echo "  • Real-time satellite link quality predictions"
    echo "  • Risk assessment: LOW/MEDIUM/HIGH/CRITICAL" 
    echo "  • Contributing factors: SNR, BER, weather, ship movement"
    echo "  • 15-minute lead time degradation alerts"
    echo ""
    echo "Example prediction response:"
    cat <<EOF | jq '.'
{
    "timestamp": "2024-08-24T09:45:58.334706",
    "predicted_quality_score": 0.351,
    "degradation_risk_level": "HIGH",
    "contributing_factors": ["Low SNR", "Heavy precipitation"],
    "recommended_actions": ["Switch to backup satellite", "Reduce bandwidth usage"],
    "confidence": 0.85,
    "prediction_horizon_minutes": 15
}
EOF
fi

if [ "$REMEDIATION_RUNNING" = true ]; then
    demo_api "Remediation Service" 8083
else
    echo ""
    echo "🛠️  Remediation Service Demo (Offline):"
    echo "-------------------------------------"
    echo "🔧 Would provide:"
    echo "  • 6 remediation actions: Failover, QoS, Bandwidth, Antenna, Power, Error Correction"
    echo "  • Approval workflows for high-risk actions"
    echo "  • Dry-run and rollback capabilities"
    echo "  • Policy-based decision making"
    echo ""
    echo "Example available actions:"
    cat <<EOF | jq '.'
{
    "satellite_failover": {
        "name": "Satellite Failover",
        "risk_level": "HIGH",
        "requires_approval": true,
        "supports_dry_run": true,
        "supports_rollback": true
    },
    "qos_shaping": {
        "name": "QoS Traffic Shaping", 
        "risk_level": "MEDIUM",
        "requires_approval": false,
        "supports_dry_run": true,
        "supports_rollback": true
    }
}
EOF
fi

if [ "$OPA_RUNNING" = true ]; then
    demo_api "Open Policy Agent" 8181
else
    echo ""
    echo "🔒 Open Policy Agent Demo (Offline):"
    echo "-----------------------------------"
    echo "🔧 Would provide:"
    echo "  • Policy enforcement for remediation actions"
    echo "  • Rate limiting by action type"
    echo "  • Risk assessment and approval determination"
    echo "  • Audit trail for all decisions"
    echo ""
    echo "Example policy decision:"
    cat <<EOF | jq '.'
{
    "result": {
        "allowed": true,
        "reason": "Action approved by policy",
        "requires_approval": false,
        "risk_assessment": {
            "risk_level": "MEDIUM",
            "estimated_impact": "low"
        }
    }
}
EOF
fi

echo ""
echo "🚀 Starting Services"
echo "==================="
echo ""
echo "To start all v0.3 services:"
echo "  docker compose up -d"
echo ""
echo "To test the integration end-to-end:"
echo "  python3 test_v03_integration.py"
echo ""
echo "Service Endpoints:"
echo "  • Link Health Service:    http://localhost:8082"
echo "  • Remediation Service:    http://localhost:8083  "
echo "  • Open Policy Agent:      http://localhost:8181"
echo "  • Existing Grafana:       http://localhost:3000"
echo "  • Existing VictoriaMetrics: http://localhost:8428"
echo ""
echo "✅ v0.3 Testing Complete!"
echo "🎯 Features: Predictive Satellite Link Health + Guarded Auto-Remediation"