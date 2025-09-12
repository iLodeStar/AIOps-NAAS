#!/usr/bin/env python3
"""
Incident Data Field Tracing Tool

This script provides detailed analysis of data field population throughout
the AIOps pipeline to identify where missing incident data should originate.

It addresses the issue where incidents show:
- ship_id: "unknown-ship" 
- service: "unknown_service"
- metric_name: "unknown_metric"
- metric_value: 0

Usage:
    python3 scripts/trace_incident_data_fields.py
    python3 scripts/trace_incident_data_fields.py --deep-analysis
    python3 scripts/trace_incident_data_fields.py --generate-test-data
"""

import json
import requests
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
import sys
import subprocess

def get_clickhouse_connection():
    """Get ClickHouse connection string based on environment"""
    try:
        # Test with admin/admin credentials first
        result = subprocess.run([
            'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client', 
            '--user=admin', '--password=admin', '--query=SELECT 1'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return {'user': 'admin', 'password': 'admin'}
    except:
        pass
    
    # Try default/clickhouse123
    try:
        result = subprocess.run([
            'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client', 
            '--user=default', '--password=clickhouse123', '--query=SELECT 1'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return {'user': 'default', 'password': 'clickhouse123'}
    except:
        pass
        
    return None

def query_clickhouse(query: str, creds: Dict[str, str]) -> List[str]:
    """Execute ClickHouse query and return results"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'aiops-clickhouse', 'clickhouse-client',
            f'--user={creds["user"]}', f'--password={creds["password"]}',
            f'--query={query}'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        else:
            print(f"❌ ClickHouse query failed: {result.stderr}")
            return []
    except Exception as e:
        print(f"❌ ClickHouse query error: {e}")
        return []

def check_service_health():
    """Check health of all pipeline services"""
    print("🔍 SERVICE HEALTH CHECK")
    print("=" * 50)
    
    services = {
        'Vector': 'http://localhost:8686/health',
        'ClickHouse': 'http://localhost:8123/ping', 
        'Benthos': 'http://localhost:4195/ping',
        'Anomaly Detection': 'http://localhost:8081/health',
        'Device Registry': 'http://localhost:8082/health',
        'Incident API': 'http://localhost:8083/health'
    }
    
    health_status = {}
    
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                health_status[service_name] = "✅ Healthy"
            else:
                health_status[service_name] = f"⚠️ Unhealthy (HTTP {response.status_code})"
        except requests.exceptions.ConnectionError:
            health_status[service_name] = "❌ Not responding"
        except Exception as e:
            health_status[service_name] = f"❌ Error: {str(e)}"
    
    for service, status in health_status.items():
        print(f"  {service:<20}: {status}")
    
    return health_status

def analyze_current_incident_quality(creds: Dict[str, str]):
    """Analyze the quality of current incident data"""
    print("\n📊 CURRENT INCIDENT DATA QUALITY ANALYSIS")
    print("=" * 50)
    
    # Get incident count
    incident_count_query = "SELECT count() FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR"
    incident_counts = query_clickhouse(incident_count_query, creds)
    
    if incident_counts and incident_counts[0] != '0':
        print(f"  Total incidents in last 24h: {incident_counts[0]}")
        
        # Analyze field quality
        quality_query = """
        SELECT
            'ship_id' as field_name,
            countIf(ship_id != 'unknown-ship') as complete_count,
            countIf(ship_id = 'unknown-ship') as missing_count,
            round(countIf(ship_id != 'unknown-ship') * 100.0 / count(), 2) as completion_percentage
        FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
        
        UNION ALL
        
        SELECT
            'service' as field_name,
            countIf(service != 'unknown_service') as complete_count,
            countIf(service = 'unknown_service') as missing_count,
            round(countIf(service != 'unknown_service') * 100.0 / count(), 2) as completion_percentage
        FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
        
        UNION ALL
        
        SELECT
            'metric_name' as field_name,
            countIf(metric_name != 'unknown_metric') as complete_count,
            countIf(metric_name = 'unknown_metric') as missing_count,
            round(countIf(metric_name != 'unknown_metric') * 100.0 / count(), 2) as completion_percentage
        FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
        
        UNION ALL
        
        SELECT
            'metric_value' as field_name,
            countIf(metric_value != 0) as complete_count,
            countIf(metric_value = 0) as missing_count,
            round(countIf(metric_value != 0) * 100.0 / count(), 2) as completion_percentage
        FROM logs.incidents WHERE created_at > now() - INTERVAL 24 HOUR
        """
        
        quality_results = query_clickhouse(quality_query, creds)
        if quality_results:
            print("\n  Field Quality Analysis:")
            print("  " + "-" * 70)
            print(f"  {'Field':<15} {'Complete':<10} {'Missing':<10} {'% Complete':<12}")
            print("  " + "-" * 70)
            for row in quality_results:
                if row.strip():
                    parts = row.split('\t')
                    if len(parts) >= 4:
                        print(f"  {parts[0]:<15} {parts[1]:<10} {parts[2]:<10} {parts[3]:<12}%")
        
        # Show sample incident
        sample_query = """
        SELECT 
            incident_id,
            ship_id,
            service,
            metric_name,
            metric_value,
            anomaly_score,
            JSONExtractString(metadata, 'host') as host,
            JSONExtractString(metadata, 'event_source') as event_source,
            created_at
        FROM logs.incidents 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        sample_results = query_clickhouse(sample_query, creds)
        if sample_results:
            print("\n  Sample Most Recent Incident:")
            fields = ['incident_id', 'ship_id', 'service', 'metric_name', 'metric_value', 
                     'anomaly_score', 'host', 'event_source', 'created_at']
            for i, row in enumerate(sample_results):
                if row.strip():
                    parts = row.split('\t')
                    for j, field in enumerate(fields):
                        if j < len(parts):
                            print(f"    {field:<15}: {parts[j]}")
                        break
    else:
        print("  No incidents found in last 24 hours")

def analyze_raw_data_sources(creds: Dict[str, str]):
    """Analyze raw data sources in Vector pipeline"""
    print("\n📥 RAW DATA SOURCES ANALYSIS")
    print("=" * 50)
    
    # Check raw data volume by source
    source_query = """
    SELECT 
        source,
        count() as record_count,
        uniq(host) as unique_hosts,
        uniq(service) as unique_services,
        countIf(host != 'unknown') as valid_hosts,
        countIf(service != 'unknown') as valid_services,
        min(timestamp) as oldest_record,
        max(timestamp) as newest_record
    FROM logs.raw 
    WHERE timestamp > now() - INTERVAL 1 HOUR
    GROUP BY source
    ORDER BY record_count DESC
    """
    
    source_results = query_clickhouse(source_query, creds)
    if source_results:
        print("\n  Data Sources (Last 1 Hour):")
        print("  " + "-" * 100)
        print(f"  {'Source':<15} {'Records':<8} {'Hosts':<6} {'Services':<8} {'Valid Hosts':<12} {'Valid Services':<13}")
        print("  " + "-" * 100)
        for row in source_results:
            if row.strip():
                parts = row.split('\t')
                if len(parts) >= 6:
                    print(f"  {parts[0]:<15} {parts[1]:<8} {parts[2]:<6} {parts[3]:<8} {parts[4]:<12} {parts[5]:<13}")
        
        # Sample data from each source
        print("\n  Sample Data from Each Source:")
        for row in source_results:
            if row.strip():
                source = row.split('\t')[0]
                sample_query = f"""
                SELECT 
                    host, service, left(message, 80) as message_preview
                FROM logs.raw 
                WHERE source = '{source}' AND timestamp > now() - INTERVAL 1 HOUR
                LIMIT 2
                """
                samples = query_clickhouse(sample_query, creds)
                if samples:
                    print(f"\n    {source} samples:")
                    for sample in samples:
                        if sample.strip():
                            parts = sample.split('\t')
                            if len(parts) >= 3:
                                print(f"      Host: {parts[0]}, Service: {parts[1]}")
                                print(f"      Message: {parts[2]}")
                            print()
    else:
        print("  No raw data found in last hour - Vector pipeline may not be working")

def check_vector_metrics():
    """Check Vector component metrics"""
    print("\n📊 VECTOR COMPONENT METRICS")
    print("=" * 50)
    
    try:
        response = requests.get('http://localhost:8686/metrics', timeout=10)
        if response.status_code == 200:
            metrics_text = response.text
            
            # Extract key metrics
            component_metrics = []
            for line in metrics_text.split('\n'):
                if 'vector_component_sent_events_total' in line and not line.startswith('#'):
                    component_metrics.append(line.strip())
                elif 'vector_component_received_events_total' in line and not line.startswith('#'):
                    component_metrics.append(line.strip())
                elif 'vector_component_errors_total' in line and not line.startswith('#'):
                    component_metrics.append(line.strip())
            
            print("  Key Vector Metrics:")
            for metric in component_metrics[:10]:  # Show first 10
                print(f"    {metric}")
                
            if len(component_metrics) > 10:
                print(f"    ... and {len(component_metrics) - 10} more metrics")
        else:
            print(f"  ❌ Could not retrieve Vector metrics (HTTP {response.status_code})")
    except Exception as e:
        print(f"  ❌ Vector metrics error: {e}")

def check_device_registry_mappings():
    """Check device registry for ship_id resolution"""
    print("\n🏷️ DEVICE REGISTRY SHIP_ID MAPPINGS")
    print("=" * 50)
    
    test_hostnames = [
        'dhruv-system-01', 'ship-01', 'vessel-alpha', 'test-host',
        'unknown-host', 'localhost', 'aiops-vector', 'aiops-clickhouse'
    ]
    
    try:
        # First check if device registry is responding
        health_response = requests.get('http://localhost:8082/health', timeout=5)
        if health_response.status_code == 200:
            print("  ✅ Device registry is responding")
            
            print("\n  Testing hostname to ship_id mappings:")
            print("  " + "-" * 60)
            print(f"  {'Hostname':<20} {'Ship ID':<20} {'Status':<15}")
            print("  " + "-" * 60)
            
            for hostname in test_hostnames:
                try:
                    lookup_response = requests.get(f'http://localhost:8082/lookup/{hostname}', timeout=5)
                    if lookup_response.status_code == 200:
                        data = lookup_response.json()
                        if data.get('success') and data.get('mapping', {}).get('ship_id'):
                            ship_id = data['mapping']['ship_id']
                            print(f"  {hostname:<20} {ship_id:<20} {'✅ Mapped':<15}")
                        else:
                            print(f"  {hostname:<20} {'No mapping':<20} {'⚠️ Unmapped':<15}")
                    else:
                        print(f"  {hostname:<20} {'Error':<20} {'❌ Failed lookup':<15}")
                except Exception as e:
                    print(f"  {hostname:<20} {'Error':<20} {'❌ Exception':<15}")
        else:
            print(f"  ❌ Device registry not responding (HTTP {health_response.status_code})")
    except Exception as e:
        print(f"  ❌ Device registry connection error: {e}")
        print("  This explains why ship_id shows as 'unknown-ship'")

def check_anomaly_detection_output():
    """Check anomaly detection service output"""
    print("\n🚨 ANOMALY DETECTION OUTPUT ANALYSIS")
    print("=" * 50)
    
    try:
        response = requests.get('http://localhost:8081/health', timeout=5)
        if response.status_code == 200:
            print("  ✅ Anomaly detection service is responding")
            
            # Try to get metrics if available
            try:
                metrics_response = requests.get('http://localhost:8081/metrics', timeout=5)
                if metrics_response.status_code == 200:
                    print("  ✅ Metrics endpoint available")
                    # Look for anomaly-related metrics
                    metrics = metrics_response.text
                    anomaly_lines = [line for line in metrics.split('\n') if 'anomaly' in line.lower() and not line.startswith('#')]
                    if anomaly_lines:
                        print("  Recent anomaly metrics:")
                        for line in anomaly_lines[:5]:
                            print(f"    {line}")
                else:
                    print("  ⚠️ No metrics endpoint available")
            except:
                print("  ⚠️ Could not retrieve metrics")
                
        else:
            print(f"  ❌ Anomaly detection service not responding (HTTP {response.status_code})")
            print("  This could explain why proper metric names and values are missing")
    except Exception as e:
        print(f"  ❌ Anomaly detection connection error: {e}")

def generate_test_data():
    """Generate test data to trace through the pipeline"""
    print("\n🧪 GENERATING TEST DATA FOR PIPELINE TRACING")
    print("=" * 50)
    
    tracking_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    print(f"  Using tracking ID: {tracking_id}")
    
    # Test 1: Send syslog message with complete fields
    test_syslog_message = f"<14>{datetime.now().strftime('%b %d %H:%M:%S')} test-ship-01 cpu-monitor: CRITICAL tracking_id={tracking_id} metric_name=cpu_usage metric_value=95.5 anomaly_score=0.9 ship_id=test-ship-01 level=ERROR"
    
    print(f"\n  Test 1: Sending syslog message with complete fields...")
    print(f"  Message: {test_syslog_message[:100]}...")
    
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(test_syslog_message.encode(), ('localhost', 1514))
        sock.close()
        print("  ✅ Syslog message sent successfully")
    except Exception as e:
        print(f"  ❌ Failed to send syslog message: {e}")
    
    # Test 2: Send NATS anomaly event (if we can connect)
    print(f"\n  Test 2: Would send NATS anomaly event...")
    test_anomaly_event = {
        "timestamp": datetime.now().isoformat(),
        "ship_id": "test-ship-01",
        "metric_name": "memory_usage",
        "metric_value": 88.2,
        "anomaly_score": 0.85,
        "tracking_id": tracking_id,
        "host": "test-ship-01",
        "service": "memory-monitor",
        "labels": {
            "instance": "test-ship-01",
            "job": "node-exporter"
        }
    }
    print(f"  Event structure: {json.dumps(test_anomaly_event, indent=2)[:200]}...")
    
    return tracking_id

def trace_test_data(tracking_id: str, creds: Dict[str, str]):
    """Trace test data through the pipeline"""
    print(f"\n🔍 TRACING TEST DATA THROUGH PIPELINE")
    print("=" * 50)
    print(f"  Tracking ID: {tracking_id}")
    
    # Wait for processing
    print("  Waiting 15 seconds for pipeline processing...")
    time.sleep(15)
    
    # Check if data reached logs.raw
    raw_query = f"SELECT count() FROM logs.raw WHERE message LIKE '%{tracking_id}%'"
    raw_results = query_clickhouse(raw_query, creds)
    
    if raw_results and raw_results[0] != '0':
        print(f"  ✅ Found {raw_results[0]} records in logs.raw")
        
        # Get details
        detail_query = f"""
        SELECT timestamp, source, host, service, level, left(message, 150) as message
        FROM logs.raw 
        WHERE message LIKE '%{tracking_id}%'
        LIMIT 3
        """
        details = query_clickhouse(detail_query, creds)
        if details:
            print("  Raw data details:")
            for detail in details:
                if detail.strip():
                    parts = detail.split('\t')
                    if len(parts) >= 6:
                        print(f"    Timestamp: {parts[0]}")
                        print(f"    Source: {parts[1]}")
                        print(f"    Host: {parts[2]}")
                        print(f"    Service: {parts[3]}")
                        print(f"    Level: {parts[4]}")
                        print(f"    Message: {parts[5]}")
                        print()
    else:
        print("  ❌ Test data NOT found in logs.raw")
        print("  This indicates Vector is not processing the syslog data")
    
    # Check if data created incidents
    time.sleep(5)  # Wait a bit more for correlation
    incident_query = f"SELECT count() FROM logs.incidents WHERE correlation_id LIKE '%{tracking_id}%' OR JSONHas(metadata, 'tracking_id')"
    incident_results = query_clickhouse(incident_query, creds)
    
    if incident_results and incident_results[0] != '0':
        print(f"  ✅ Found {incident_results[0]} incidents created from test data")
    else:
        print("  ⚠️ No incidents created from test data")
        print("  This could indicate issues in Benthos correlation or anomaly detection")

def provide_recommendations():
    """Provide actionable recommendations"""
    print("\n💡 ACTIONABLE RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = [
        {
            "issue": "ship_id shows as 'unknown-ship'",
            "causes": [
                "Device registry service not running or not accessible",
                "No hostname mappings configured in device registry", 
                "Hostname not properly extracted from log sources"
            ],
            "fixes": [
                "Ensure device registry service is running on port 8082",
                "Add hostname to ship_id mappings using scripts/register_device.py",
                "Verify Vector is extracting hostname from syslog messages",
                "Check that syslog messages include proper hostname field"
            ]
        },
        {
            "issue": "service shows as 'unknown_service'",
            "causes": [
                "Syslog messages not including appname field",
                "Vector not properly parsing service from log sources",
                "Application logs not structured with service identifiers"
            ],
            "fixes": [
                "Configure applications to include service name in syslog appname field",
                "Update Vector configuration to extract service from message content",
                "Use structured logging in applications with service field",
                "Add service mapping rules in Vector transforms"
            ]
        },
        {
            "issue": "metric_name shows as 'unknown_metric'",
            "causes": [
                "Anomaly detection service not providing proper metric names",
                "NATS anomaly events missing metric_name field",
                "Benthos not extracting metric names from source data"
            ],
            "fixes": [
                "Verify anomaly detection service is publishing events to NATS",
                "Check NATS anomaly.detected subject for proper message structure",
                "Update anomaly detection service to include metric_name in events",
                "Add metric name extraction rules in Benthos pipeline"
            ]
        },
        {
            "issue": "metric_value shows as 0",
            "causes": [
                "Anomaly events not including actual metric values",
                "Benthos not parsing numeric values correctly",
                "Data type conversion issues in the pipeline"
            ],
            "fixes": [
                "Ensure anomaly detection includes metric_value in published events", 
                "Add proper number parsing in Benthos configuration",
                "Verify data types in ClickHouse schema match expected values",
                "Add validation for numeric fields in incident API"
            ]
        }
    ]
    
    for rec in recommendations:
        print(f"\n🚨 Issue: {rec['issue']}")
        print("   Likely causes:")
        for cause in rec['causes']:
            print(f"     • {cause}")
        print("   Recommended fixes:")
        for fix in rec['fixes']:
            print(f"     ✅ {fix}")

def main():
    parser = argparse.ArgumentParser(description='Trace incident data field population')
    parser.add_argument('--deep-analysis', action='store_true', help='Perform deep analysis of all components')
    parser.add_argument('--generate-test-data', action='store_true', help='Generate test data to trace through pipeline')
    parser.add_argument('--recommendations-only', action='store_true', help='Show only recommendations')
    
    args = parser.parse_args()
    
    if args.recommendations_only:
        provide_recommendations()
        return
    
    print("🔍 INCIDENT DATA FIELD TRACING ANALYSIS")
    print("=" * 60)
    print("Analyzing data flow to identify sources of missing incident fields")
    print("=" * 60)
    
    # Check services
    health_status = check_service_health()
    
    # Get ClickHouse credentials
    creds = get_clickhouse_connection()
    if not creds:
        print("\n❌ Could not connect to ClickHouse with any known credentials")
        print("   This could explain data flow issues")
        return
    else:
        print(f"\n✅ Connected to ClickHouse with {creds['user']}/{creds['password']}")
    
    # Analyze current data quality
    analyze_current_incident_quality(creds)
    
    if args.deep_analysis:
        # Deep analysis of all components
        analyze_raw_data_sources(creds)
        check_vector_metrics()
        check_device_registry_mappings()
        check_anomaly_detection_output()
    
    # Generate test data if requested
    tracking_id = None
    if args.generate_test_data:
        tracking_id = generate_test_data()
        if tracking_id:
            trace_test_data(tracking_id, creds)
    
    # Always provide recommendations
    provide_recommendations()
    
    print(f"\n🎯 SUMMARY")
    print("=" * 60)
    print("This analysis shows where missing incident data should originate.")
    print("Focus on the service health checks and recommendations above.")
    print("Run with --generate-test-data to test the complete pipeline.")
    print("Run with --deep-analysis for detailed component analysis.")

if __name__ == "__main__":
    main()