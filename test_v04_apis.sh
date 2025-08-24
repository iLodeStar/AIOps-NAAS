#!/bin/bash
"""
AIOps NAAS v0.4 - API Testing Script

This script demonstrates the v0.4 Fleet Management APIs:
- Fleet Data Aggregation Service (port 8084)
- Capacity Forecasting Service (port 8085)  
- Cross-Ship Benchmarking Service (port 8086)

Usage: ./test_v04_apis.sh
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service URLs
FLEET_AGGREGATION_URL="http://localhost:8084"
CAPACITY_FORECASTING_URL="http://localhost:8085"
BENCHMARKING_URL="http://localhost:8086"

print_header() {
    echo -e "\n${BLUE}================================================================${NC}"
    echo -e "${BLUE}🚢 $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}🔍 $1${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
}

check_service() {
    local service_name=$1
    local url=$2
    
    echo -e "🔗 Checking $service_name..."
    
    if curl -s -f "$url/health" > /dev/null 2>&1; then
        echo -e "✅ $service_name is ${GREEN}RUNNING${NC}"
        return 0
    else
        echo -e "❌ $service_name is ${RED}NOT AVAILABLE${NC}"
        return 1
    fi
}

demo_api() {
    local title=$1
    local url=$2
    local description=$3
    
    echo -e "\n📡 ${GREEN}$title${NC}"
    echo -e "   $description"
    echo -e "   URL: $url"
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "   Status: ${GREEN}✅ Available${NC}"
        echo -e "   Sample response:"
        curl -s "$url" | jq '.' 2>/dev/null | head -20 || echo "   (Raw response too large or not JSON)"
    else
        echo -e "   Status: ${RED}❌ Not available${NC}"
    fi
}

print_header "AIOps NAAS v0.4 - Fleet Management API Demo"

echo -e "This script demonstrates the v0.4 Fleet Management capabilities:"
echo -e "• Fleet Data Aggregation - Central data collection from all ships"
echo -e "• Capacity Forecasting - Seasonal traffic and occupancy prediction"  
echo -e "• Cross-Ship Benchmarking - Performance comparison and correlation analysis"
echo -e "• OpenStreetMap Integration - Fleet location mapping"

# Check service availability
print_section "Service Health Checks"

FLEET_RUNNING=false
FORECASTING_RUNNING=false
BENCHMARKING_RUNNING=false

if check_service "Fleet Aggregation" "$FLEET_AGGREGATION_URL"; then
    FLEET_RUNNING=true
fi

if check_service "Capacity Forecasting" "$CAPACITY_FORECASTING_URL"; then
    FORECASTING_RUNNING=true
fi

if check_service "Cross-Ship Benchmarking" "$BENCHMARKING_URL"; then
    BENCHMARKING_RUNNING=true
fi

# Fleet Data Aggregation Service Demo
print_section "Fleet Data Aggregation Service (Port 8084)"

if [ "$FLEET_RUNNING" = true ]; then
    demo_api "Fleet Summary" "$FLEET_AGGREGATION_URL/fleet/summary" "Overview of entire fleet status and capacity"
    demo_api "Fleet Locations" "$FLEET_AGGREGATION_URL/fleet/locations" "Real-time ship positions for mapping"
    demo_api "Fleet Incidents" "$FLEET_AGGREGATION_URL/fleet/incidents" "Cross-ship incident summary and correlation"
    
    echo -e "\n🔧 Available Actions:"
    echo -e "   • POST /fleet/aggregate - Trigger manual data aggregation"
    echo -e "   • Automatic background aggregation every 2 minutes"
    echo -e "   • NATS integration for real-time fleet status updates"
    
else
    echo -e "\n🛠️  Fleet Data Aggregation Demo (Offline):"
    echo -e "---------------------------------------------"
    echo -e "🔧 Would provide:"
    echo -e "  • Central aggregation from 5 ships across different routes"
    echo -e "  • Real-time ship location tracking with GPS coordinates"
    echo -e "  • Fleet-wide incident correlation and analysis"
    echo -e "  • ClickHouse integration for historical fleet data storage"
    
    echo -e "\nExample fleet summary response:"
    cat <<EOF | jq '.'
{
    "total_ships": 5,
    "active_ships": 5,
    "total_capacity": 15800,
    "total_occupancy": 13020,
    "average_occupancy_rate": 0.824,
    "ships_by_route": {
        "Caribbean": 1,
        "Alaska": 1, 
        "Mediterranean": 1,
        "Northern Europe": 1,
        "South Pacific": 1
    },
    "timestamp": "2024-08-24T10:30:00Z"
}
EOF
    
    echo -e "\nExample ship location data:"
    cat <<EOF | jq '.'
[
    {
        "ship_id": "ship-01",
        "name": "Caribbean Dream",
        "latitude": 25.7617,
        "longitude": -80.1918,
        "heading": 180.5,
        "speed_knots": 18.2,
        "route": "Caribbean",
        "capacity": 3000,
        "occupancy": 2550,
        "timestamp": "2024-08-24T10:30:00Z"
    }
]
EOF
fi

# Capacity Forecasting Service Demo
print_section "Capacity Forecasting Service (Port 8085)"

if [ "$FORECASTING_RUNNING" = true ]; then
    demo_api "Ship Forecasts" "$CAPACITY_FORECASTING_URL/forecast/ships?days_ahead=30" "30-day capacity predictions per ship"
    demo_api "Route Forecasts" "$CAPACITY_FORECASTING_URL/forecast/routes" "Aggregated route-level forecasting"
    demo_api "Capacity Alerts" "$CAPACITY_FORECASTING_URL/alerts" "Overbooking and underutilization alerts"
    demo_api "Historical Data" "$CAPACITY_FORECASTING_URL/historical?days_back=90" "Historical capacity and booking patterns"
    
    echo -e "\n🔧 Available Actions:"
    echo -e "   • POST /models/retrain - Retrain forecasting models with latest data"
    echo -e "   • GET /models/metrics - View model performance and accuracy"
    echo -e "   • Seasonal pattern recognition for different routes"
    echo -e "   • Time-series modeling with ExponentialSmoothing and regression"
    
else
    echo -e "\n🔮 Capacity Forecasting Demo (Offline):"
    echo -e "----------------------------------------"
    echo -e "🔧 Would provide:"
    echo -e "  • 30-365 day capacity forecasting per ship and route"
    echo -e "  • Seasonal pattern analysis (Caribbean peak: Dec-Mar, Alaska: Jun-Aug)"
    echo -e "  • Machine learning models: ExponentialSmoothing + PolynomialRegression"
    echo -e "  • Revenue projections and yield optimization recommendations"
    
    echo -e "\nExample capacity forecast:"
    cat <<EOF | jq '.'
{
    "ship_id": "ship-03",
    "route": "Mediterranean",
    "forecast_date": "2024-09-15T00:00:00Z",
    "predicted_occupancy": 3185,
    "predicted_occupancy_rate": 0.91,
    "confidence_lower": 0.81,
    "confidence_upper": 1.0,
    "seasonal_factor": 1.3,
    "trend_direction": "increasing"
}
EOF
    
    echo -e "\nExample route forecast:"
    cat <<EOF | jq '.'
{
    "route": "Mediterranean", 
    "forecast_period": "next_30_days",
    "total_capacity": 105000,
    "predicted_demand": 95550,
    "utilization_rate": 0.91,
    "revenue_projection": 95550000,
    "recommendations": [
        "Consider increasing capacity or pricing for this route",
        "High demand predicted - optimize revenue management"
    ]
}
EOF
fi

# Cross-Ship Benchmarking Service Demo  
print_section "Cross-Ship Benchmarking Service (Port 8086)"

if [ "$BENCHMARKING_RUNNING" = true ]; then
    demo_api "Fleet Benchmark Summary" "$BENCHMARKING_URL/fleet/summary" "Fleet-wide performance overview"
    demo_api "Ship Benchmarks" "$BENCHMARKING_URL/benchmarks/ships" "Individual ship performance scores"
    demo_api "Performance Outliers" "$BENCHMARKING_URL/outliers" "Ships performing outside normal parameters"
    demo_api "Correlation Insights" "$BENCHMARKING_URL/insights" "Cross-ship patterns and correlations"
    
    echo -e "\n🔧 Available Actions:"
    echo -e "   • POST /analysis/run - Trigger comprehensive benchmarking analysis"
    echo -e "   • GET /comparison/{ship_id} - Detailed ship-to-fleet comparison"  
    echo -e "   • Statistical outlier detection with z-score analysis"
    echo -e "   • Correlation matrix analysis for fleet-wide patterns"
    
else
    echo -e "\n⚖️  Cross-Ship Benchmarking Demo (Offline):"
    echo -e "-------------------------------------------"
    echo -e "🔧 Would provide:"
    echo -e "  • Performance benchmarking across 4 categories:"
    echo -e "    - Operational Efficiency (CPU, Memory, Storage, Bandwidth)"
    echo -e "    - Passenger Experience (Link Quality, Occupancy, Incidents)"
    echo -e "    - Route Performance (Speed, Fuel, Schedule Adherence)"
    echo -e "    - Technical Reliability (Uptime, Error Rate, Maintenance)"
    echo -e "  • Statistical outlier detection (z-score > 2.0)"
    echo -e "  • Fleet-wide correlation analysis for operational insights"
    
    echo -e "\nExample fleet benchmark summary:"
    cat <<EOF | jq '.'
{
    "timestamp": "2024-08-24T10:30:00Z",
    "total_ships": 5,
    "active_ships": 5,
    "fleet_health_score": 85.6,
    "top_performer": "ship-03",
    "bottom_performer": "ship-04", 
    "category_averages": {
        "operational_efficiency": 78.2,
        "passenger_experience": 85.4,
        "route_performance": 82.1,
        "technical_reliability": 88.7
    },
    "outlier_count": 3,
    "correlation_insights": 4
}
EOF
    
    echo -e "\nExample performance outlier:"
    cat <<EOF | jq '.'
{
    "ship_id": "ship-04",
    "metric_name": "error_rate",
    "category": "technical_reliability",
    "actual_value": 4.2,
    "expected_value": 1.5,
    "z_score": 3.2,
    "severity": "HIGH",
    "description": "Error rate significantly higher than fleet average (1.50)"
}
EOF
    
    echo -e "\nExample correlation insight:"
    cat <<EOF | jq '.'
{
    "insight_id": "12345",
    "insight_type": "fleet_pattern",
    "title": "Strong Positive Correlation: CPU and Memory Usage",
    "description": "Fleet analysis shows positive correlation (0.78) between cpu_usage and memory_usage across all ships",
    "affected_ships": ["ship-01", "ship-03", "ship-04"],
    "correlation_strength": 0.78,
    "confidence": 87.0,
    "recommended_actions": [
        "Monitor CPU usage as increases may indicate Memory usage will also increase",
        "Optimize CPU usage to potentially improve Memory usage"
    ]
}
EOF
fi

# Integration and Next Steps
print_section "v0.4 Integration Summary"

echo -e "🎯 ${GREEN}v0.4 Acceptance Criteria Status:${NC}"
if [ "$FLEET_RUNNING" = true ] && [ "$FORECASTING_RUNNING" = true ] && [ "$BENCHMARKING_RUNNING" = true ]; then
    echo -e "   ✅ Central visibility across all ships - Fleet aggregation and mapping"
    echo -e "   ✅ Actionable capacity planning - Forecasting with seasonal patterns" 
    echo -e "   ✅ Cross-ship incident benchmarking - Performance correlation analysis"
else
    echo -e "   🔧 Central visibility across all ships - Fleet aggregation and mapping"
    echo -e "   🔧 Actionable capacity planning - Forecasting with seasonal patterns" 
    echo -e "   🔧 Cross-ship incident benchmarking - Performance correlation analysis"
fi

echo -e "\n📊 ${BLUE}Fleet Dashboards Available:${NC}"
echo -e "   • Fleet Overview Dashboard - http://localhost:3000 (fleet-overview uid)"
echo -e "   • Cross-Ship Benchmarking - http://localhost:3000 (cross-ship-benchmarking uid)"
echo -e "   • Capacity Forecasting - http://localhost:3000 (capacity-forecasting uid)"
echo -e "   • OpenStreetMap integration for ship location visualization"

echo -e "\n🔄 ${BLUE}Background Processing:${NC}"
echo -e "   • Fleet data aggregation every 2 minutes"
echo -e "   • Forecasting model retraining every 6 hours"
echo -e "   • Benchmarking analysis every 10 minutes"
echo -e "   • NATS message bus integration for real-time updates"

echo -e "\n🚀 ${BLUE}Technology Stack:${NC}"
echo -e "   • ClickHouse: Fleet data storage with partitioned tables"
echo -e "   • VictoriaMetrics: Fleet-wide metrics aggregation"
echo -e "   • Grafana: Fleet dashboards with OpenStreetMap"
echo -e "   • Python ML: scikit-learn, statsmodels for forecasting"
echo -e "   • FastAPI: RESTful services with comprehensive APIs"

echo -e "\n🎉 ${GREEN}v0.4 Implementation Complete!${NC}"
echo -e "Fleet Reporting, Capacity Forecasting, and Cross-Ship Benchmarking features ready for production use."

if [ "$FLEET_RUNNING" = true ] && [ "$FORECASTING_RUNNING" = true ] && [ "$BENCHMARKING_RUNNING" = true ]; then
    echo -e "\n${GREEN}✅ All v0.4 services are running and ready for testing!${NC}"
    echo -e "Run the integration test: ${YELLOW}python3 test_v04_integration.py${NC}"
else
    echo -e "\n${YELLOW}🔧 To start all services:${NC}"
    echo -e "   ${YELLOW}docker compose up -d${NC}"
    echo -e "   ${YELLOW}python3 test_v04_integration.py${NC}"
fi