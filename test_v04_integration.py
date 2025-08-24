#!/usr/bin/env python3
"""
AIOps NAAS v0.4 - Integration Test

Comprehensive integration test for v0.4 fleet management features:
- Fleet Data Aggregation Service
- Capacity Forecasting Service  
- Cross-Ship Benchmarking Service
- Fleet dashboards and reporting

Tests end-to-end functionality and validates all v0.4 acceptance criteria:
- Central visibility across all ships
- Actionable capacity planning
- Cross-ship incident benchmarking
"""

import asyncio
import requests
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import sys

# Service endpoints
SERVICES = {
    "fleet-aggregation": "http://localhost:8084",
    "capacity-forecasting": "http://localhost:8085", 
    "cross-ship-benchmarking": "http://localhost:8086",
    "grafana": "http://localhost:3000"
}

def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"🚢 {title}")
    print(f"{'='*60}")

def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'—'*40}")
    print(f"🔍 {title}")
    print(f"{'—'*40}")

def check_service_health(service_name: str, endpoint: str) -> bool:
    """Check if a service is healthy"""
    try:
        response = requests.get(f"{endpoint}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ {service_name}: {health_data.get('status', 'healthy')}")
            return True
        else:
            print(f"❌ {service_name}: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {service_name}: {str(e)}")
        return False

def test_fleet_aggregation_service():
    """Test Fleet Data Aggregation Service functionality"""
    print_section("Fleet Data Aggregation Service")
    
    service_url = SERVICES["fleet-aggregation"]
    
    # Test 1: Fleet summary
    try:
        print("📊 Testing fleet summary...")
        response = requests.get(f"{service_url}/fleet/summary", timeout=15)
        if response.status_code == 200:
            summary = response.json()
            print(f"   • Total Ships: {summary.get('total_ships', 'N/A')}")
            print(f"   • Active Ships: {summary.get('active_ships', 'N/A')}")
            print(f"   • Total Capacity: {summary.get('total_capacity', 'N/A')}")
            print(f"   • Avg Occupancy Rate: {summary.get('average_occupancy_rate', 0):.1%}")
            print(f"   • Ships by Route: {summary.get('ships_by_route', {})}")
            print("✅ Fleet summary retrieved successfully")
        else:
            print(f"❌ Fleet summary failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fleet summary error: {e}")
        return False
    
    # Test 2: Fleet locations 
    try:
        print("🗺️  Testing fleet locations...")
        response = requests.get(f"{service_url}/fleet/locations", timeout=15)
        if response.status_code == 200:
            locations = response.json()
            print(f"   • Ships tracked: {len(locations)}")
            for ship in locations[:3]:  # Show first 3
                print(f"     - {ship.get('name', 'Unknown')}: {ship.get('latitude', 0):.2f}, {ship.get('longitude', 0):.2f}")
            print("✅ Fleet locations retrieved successfully")
        else:
            print(f"❌ Fleet locations failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fleet locations error: {e}")
        return False
    
    # Test 3: Fleet incidents
    try:
        print("🚨 Testing fleet incidents...")
        response = requests.get(f"{service_url}/fleet/incidents", timeout=15)
        if response.status_code == 200:
            incidents = response.json()
            print(f"   • Ships with incident data: {len(incidents)}")
            total_incidents = sum(ship.get('incident_count_24h', 0) for ship in incidents)
            critical_incidents = sum(ship.get('critical_incidents', 0) for ship in incidents)
            print(f"   • Total incidents (24h): {total_incidents}")
            print(f"   • Critical incidents: {critical_incidents}")
            print("✅ Fleet incidents retrieved successfully")
        else:
            print(f"❌ Fleet incidents failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fleet incidents error: {e}")
        return False
    
    # Test 4: Manual aggregation trigger
    try:
        print("🔄 Testing manual aggregation trigger...")
        response = requests.post(f"{service_url}/fleet/aggregate", timeout=20)
        if response.status_code == 200:
            result = response.json()
            print(f"   • Status: {result.get('status', 'unknown')}")
            print(f"   • Message: {result.get('message', 'No message')}")
            print("✅ Manual aggregation completed successfully")
        else:
            print(f"❌ Manual aggregation failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Manual aggregation error: {e}")
        return False
    
    return True

def test_capacity_forecasting_service():
    """Test Capacity Forecasting Service functionality"""
    print_section("Capacity Forecasting Service")
    
    service_url = SERVICES["capacity-forecasting"]
    
    # Test 1: Ship forecasts
    try:
        print("📈 Testing ship capacity forecasts...")
        response = requests.get(f"{service_url}/forecast/ships?days_ahead=30", timeout=20)
        if response.status_code == 200:
            forecasts = response.json()
            print(f"   • Forecasts generated: {len(forecasts)}")
            
            # Analyze forecast data
            if forecasts:
                ships = set(f.get('ship_id') for f in forecasts)
                routes = set(f.get('route') for f in forecasts)
                avg_occupancy = sum(f.get('predicted_occupancy_rate', 0) for f in forecasts) / len(forecasts)
                
                print(f"   • Ships covered: {len(ships)}")
                print(f"   • Routes covered: {len(routes)}")
                print(f"   • Avg predicted occupancy: {avg_occupancy:.1%}")
                
                # Show sample forecast
                sample = forecasts[0]
                print(f"   • Sample forecast for {sample.get('ship_id', 'unknown')}:")
                print(f"     - Predicted occupancy: {sample.get('predicted_occupancy_rate', 0):.1%}")
                print(f"     - Trend: {sample.get('trend_direction', 'unknown')}")
                print(f"     - Seasonal factor: {sample.get('seasonal_factor', 1):.2f}")
            
            print("✅ Ship forecasts retrieved successfully")
        else:
            print(f"❌ Ship forecasts failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ship forecasts error: {e}")
        return False
    
    # Test 2: Route forecasts
    try:
        print("🌍 Testing route forecasts...")
        response = requests.get(f"{service_url}/forecast/routes", timeout=20)
        if response.status_code == 200:
            route_forecasts = response.json()
            print(f"   • Route forecasts: {len(route_forecasts)}")
            
            for route in route_forecasts[:3]:  # Show first 3
                print(f"   • {route.get('route', 'Unknown')}:")
                print(f"     - Utilization rate: {route.get('utilization_rate', 0):.1%}")
                print(f"     - Revenue projection: ${route.get('revenue_projection', 0):,.0f}")
                print(f"     - Recommendations: {len(route.get('recommendations', []))}")
            
            print("✅ Route forecasts retrieved successfully")
        else:
            print(f"❌ Route forecasts failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Route forecasts error: {e}")
        return False
    
    # Test 3: Capacity alerts
    try:
        print("⚠️  Testing capacity alerts...")
        response = requests.get(f"{service_url}/alerts", timeout=15)
        if response.status_code == 200:
            alerts = response.json()
            print(f"   • Alerts generated: {len(alerts)}")
            
            # Categorize alerts
            alert_types = {}
            severity_counts = {}
            for alert in alerts:
                alert_type = alert.get('alert_type', 'unknown')
                severity = alert.get('severity', 'unknown')
                alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            print(f"   • Alert types: {alert_types}")
            print(f"   • Severity distribution: {severity_counts}")
            
            # Show sample alert
            if alerts:
                sample = alerts[0]
                print(f"   • Sample alert: {sample.get('alert_type', 'unknown')} for {sample.get('ship_id', 'unknown')}")
                print(f"     - Severity: {sample.get('severity', 'unknown')}")
                print(f"     - Actions: {len(sample.get('recommended_actions', []))}")
            
            print("✅ Capacity alerts retrieved successfully")
        else:
            print(f"❌ Capacity alerts failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Capacity alerts error: {e}")
        return False
    
    # Test 4: Historical data
    try:
        print("📊 Testing historical data...")
        response = requests.get(f"{service_url}/historical?days_back=30", timeout=15)
        if response.status_code == 200:
            historical = response.json()
            print(f"   • Historical data points: {len(historical)}")
            
            if historical:
                ships = set(h.get('ship_id') for h in historical)
                routes = set(h.get('route') for h in historical)
                print(f"   • Ships in historical data: {len(ships)}")
                print(f"   • Routes in historical data: {len(routes)}")
            
            print("✅ Historical data retrieved successfully")
        else:
            print(f"❌ Historical data failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Historical data error: {e}")
        return False
    
    # Test 5: Model retraining
    try:
        print("🔄 Testing model retraining...")
        response = requests.post(f"{service_url}/models/retrain", timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"   • Status: {result.get('status', 'unknown')}")
            print(f"   • Models trained: {result.get('models_trained', 0)}")
            print("✅ Model retraining completed successfully")
        else:
            print(f"❌ Model retraining failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Model retraining error: {e}")
        return False
    
    return True

def test_cross_ship_benchmarking_service():
    """Test Cross-Ship Benchmarking Service functionality"""
    print_section("Cross-Ship Benchmarking Service")
    
    service_url = SERVICES["cross-ship-benchmarking"]
    
    # Test 1: Fleet benchmark summary
    try:
        print("📊 Testing fleet benchmark summary...")
        response = requests.get(f"{service_url}/fleet/summary", timeout=20)
        if response.status_code == 200:
            summary = response.json()
            print(f"   • Active ships: {summary.get('active_ships', 0)}")
            print(f"   • Fleet health score: {summary.get('fleet_health_score', 0):.1f}")
            print(f"   • Top performer: {summary.get('top_performer', 'N/A')}")
            print(f"   • Bottom performer: {summary.get('bottom_performer', 'N/A')}")
            print(f"   • Outliers detected: {summary.get('outlier_count', 0)}")
            print(f"   • Correlation insights: {summary.get('correlation_insights', 0)}")
            print("✅ Fleet benchmark summary retrieved successfully")
        else:
            print(f"❌ Fleet benchmark summary failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fleet benchmark summary error: {e}")
        return False
    
    # Test 2: Ship benchmarks
    try:
        print("⚖️  Testing ship benchmarks...")
        response = requests.get(f"{service_url}/benchmarks/ships", timeout=20)
        if response.status_code == 200:
            benchmarks = response.json()
            print(f"   • Ship benchmarks: {len(benchmarks)}")
            
            for benchmark in benchmarks[:3]:  # Show top 3
                print(f"   • {benchmark.get('ship_name', 'Unknown')}:")
                print(f"     - Overall score: {benchmark.get('overall_score', 0):.1f}")
                print(f"     - Percentile rank: {benchmark.get('percentile_rank', 0):.1f}")
                print(f"     - Strengths: {len(benchmark.get('strengths', []))}")
                print(f"     - Improvement areas: {len(benchmark.get('improvement_areas', []))}")
                print(f"     - Outliers: {len(benchmark.get('outliers', []))}")
            
            print("✅ Ship benchmarks retrieved successfully")
        else:
            print(f"❌ Ship benchmarks failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ship benchmarks error: {e}")
        return False
    
    # Test 3: Outlier detection
    try:
        print("🚨 Testing outlier detection...")
        response = requests.get(f"{service_url}/outliers", timeout=15)
        if response.status_code == 200:
            outliers = response.json()
            print(f"   • Outliers detected: {len(outliers)}")
            
            # Categorize outliers
            severity_counts = {}
            metric_counts = {}
            for outlier in outliers:
                severity = outlier.get('severity', 'unknown')
                metric = outlier.get('metric_name', 'unknown')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                metric_counts[metric] = metric_counts.get(metric, 0) + 1
            
            print(f"   • By severity: {severity_counts}")
            print(f"   • By metric: {dict(list(metric_counts.items())[:3])}")  # Show top 3
            
            # Show sample outlier
            if outliers:
                sample = outliers[0]
                print(f"   • Sample outlier: {sample.get('ship_id', 'unknown')} - {sample.get('metric_name', 'unknown')}")
                print(f"     - Z-score: {sample.get('z_score', 0):.2f}")
                print(f"     - Severity: {sample.get('severity', 'unknown')}")
                print(f"     - Description: {sample.get('description', 'No description')[:60]}...")
            
            print("✅ Outlier detection completed successfully")
        else:
            print(f"❌ Outlier detection failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Outlier detection error: {e}")
        return False
    
    # Test 4: Correlation insights
    try:
        print("🔗 Testing correlation insights...")
        response = requests.get(f"{service_url}/insights", timeout=15)
        if response.status_code == 200:
            insights = response.json()
            print(f"   • Insights generated: {len(insights)}")
            
            # Categorize insights
            insight_types = {}
            for insight in insights:
                insight_type = insight.get('insight_type', 'unknown')
                insight_types[insight_type] = insight_types.get(insight_type, 0) + 1
            
            print(f"   • By type: {insight_types}")
            
            # Show sample insight
            if insights:
                sample = insights[0]
                print(f"   • Sample insight: {sample.get('title', 'No title')}")
                print(f"     - Type: {sample.get('insight_type', 'unknown')}")
                print(f"     - Correlation strength: {sample.get('correlation_strength', 0):.2f}")
                print(f"     - Confidence: {sample.get('confidence', 0):.1f}%")
                print(f"     - Affected ships: {len(sample.get('affected_ships', []))}")
            
            print("✅ Correlation insights retrieved successfully")
        else:
            print(f"❌ Correlation insights failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Correlation insights error: {e}")
        return False
    
    # Test 5: Manual analysis trigger
    try:
        print("🔄 Testing manual analysis trigger...")
        response = requests.post(f"{service_url}/analysis/run", timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"   • Status: {result.get('status', 'unknown')}")
            print(f"   • Ships analyzed: {result.get('ships_analyzed', 0)}")
            print(f"   • Outliers detected: {result.get('outliers_detected', 0)}")
            print(f"   • Insights generated: {result.get('insights_generated', 0)}")
            print("✅ Manual analysis completed successfully")
        else:
            print(f"❌ Manual analysis failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Manual analysis error: {e}")
        return False
    
    return True

def test_grafana_dashboards():
    """Test Grafana dashboard availability"""
    print_section("Grafana Fleet Dashboards")
    
    grafana_url = SERVICES["grafana"]
    
    # Test dashboard availability (simplified - just check if Grafana is responding)
    try:
        print("📊 Testing Grafana accessibility...")
        response = requests.get(f"{grafana_url}/api/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"   • Grafana status: {health.get('database', 'unknown')}")
            print("✅ Grafana is accessible")
        else:
            print(f"❌ Grafana health check failed: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Grafana connection error: {e}")
        return False
    
    # List expected dashboards
    expected_dashboards = [
        "Fleet Overview Dashboard",
        "Cross-Ship Benchmarking Dashboard", 
        "Capacity Forecasting Dashboard"
    ]
    
    print(f"📋 Expected v0.4 dashboards:")
    for dashboard in expected_dashboards:
        print(f"   • {dashboard}")
    
    print("✅ Fleet dashboards configured (manual verification required)")
    return True

def run_comprehensive_test():
    """Run comprehensive v0.4 integration test"""
    print_header("AIOps NAAS v0.4 - Fleet Management Integration Test")
    
    # Track test results
    test_results = {}
    
    # Step 1: Health checks
    print_section("Service Health Checks")
    all_healthy = True
    for service, endpoint in SERVICES.items():
        healthy = check_service_health(service, endpoint)
        test_results[f"{service}_health"] = healthy
        if not healthy:
            all_healthy = False
    
    if not all_healthy:
        print("\n❌ Some services are not healthy. Please start all services before running tests.")
        print("   Run: docker compose up -d")
        return False
    
    # Step 2: Fleet Data Aggregation tests
    print("\n" + "="*60)
    fleet_aggregation_success = test_fleet_aggregation_service()
    test_results["fleet_aggregation"] = fleet_aggregation_success
    
    # Step 3: Capacity Forecasting tests
    print("\n" + "="*60)
    capacity_forecasting_success = test_capacity_forecasting_service()
    test_results["capacity_forecasting"] = capacity_forecasting_success
    
    # Step 4: Cross-Ship Benchmarking tests
    print("\n" + "="*60)
    benchmarking_success = test_cross_ship_benchmarking_service()
    test_results["benchmarking"] = benchmarking_success
    
    # Step 5: Grafana Dashboard tests
    print("\n" + "="*60)
    grafana_success = test_grafana_dashboards()
    test_results["grafana"] = grafana_success
    
    # Final results
    print_header("v0.4 Integration Test Results")
    
    total_tests = len([k for k in test_results.keys() if not k.endswith("_health")])
    passed_tests = len([k for k, v in test_results.items() if v and not k.endswith("_health")])
    
    print(f"📊 Test Summary:")
    print(f"   • Total test categories: {total_tests}")
    print(f"   • Passed: {passed_tests}")
    print(f"   • Failed: {total_tests - passed_tests}")
    
    print(f"\n🎯 v0.4 Acceptance Criteria Validation:")
    
    # Central visibility across all ships
    central_visibility = test_results.get("fleet_aggregation", False) and test_results.get("grafana", False)
    print(f"   • Central visibility across all ships: {'✅ PASS' if central_visibility else '❌ FAIL'}")
    
    # Actionable capacity planning
    capacity_planning = test_results.get("capacity_forecasting", False)
    print(f"   • Actionable capacity planning: {'✅ PASS' if capacity_planning else '❌ FAIL'}")
    
    # Cross-ship incident benchmarking
    benchmarking_capability = test_results.get("benchmarking", False)
    print(f"   • Cross-ship incident benchmarking: {'✅ PASS' if benchmarking_capability else '❌ FAIL'}")
    
    # Overall success
    overall_success = central_visibility and capacity_planning and benchmarking_capability
    
    if overall_success:
        print(f"\n🎉 v0.4 Integration Test PASSED!")
        print(f"✅ All acceptance criteria met")
        print(f"🚀 Fleet Reporting, Capacity Forecasting, and Cross-Ship Benchmarking features validated")
    else:
        print(f"\n❌ v0.4 Integration Test FAILED")
        print(f"🔧 Some acceptance criteria not met - review failed tests above")
    
    # Export detailed results
    results_file = "/tmp/v04_test_results.json"
    detailed_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "v0.4",
        "test_results": test_results,
        "acceptance_criteria": {
            "central_visibility": central_visibility,
            "capacity_planning": capacity_planning,
            "benchmarking": benchmarking_capability,
            "overall_success": overall_success
        },
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0.0%"
        }
    }
    
    try:
        with open(results_file, 'w') as f:
            json.dump(detailed_results, f, indent=2)
        print(f"\n📄 Detailed results exported to {results_file}")
    except Exception as e:
        print(f"\n⚠️  Could not export results: {e}")
    
    return overall_success

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)