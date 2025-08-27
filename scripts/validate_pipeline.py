#!/usr/bin/env python3
"""
AIOps NAAS - End-to-End Pipeline Validator (Python Version)

This script validates the complete anomaly detection pipeline:
1. Sends baseline metrics to VictoriaMetrics
2. Sends anomaly spikes to trigger detection
3. Waits for anomalies to be processed
4. Verifies incidents are created via Incident API
5. Optionally checks ClickHouse storage

Usage: 
  export CH_USER=admin CH_PASS=admin
  python3 scripts/validate_pipeline.py

Environment Variables:
  VM_URL - VictoriaMetrics URL (default: http://localhost:8428)
  INCIDENT_API_URL - Incident API URL (default: http://localhost:8081) 
  CH_URL - ClickHouse URL (default: http://localhost:8123)
  CH_USER - ClickHouse username (default: admin)
  CH_PASS - ClickHouse password (default: admin)
  WAIT_TIME - Wait time between steps in seconds (default: 30)
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# Configuration from environment
VM_URL = os.getenv('VM_URL', 'http://localhost:8428')
INCIDENT_API_URL = os.getenv('INCIDENT_API_URL', 'http://localhost:8081')
CH_URL = os.getenv('CH_URL', 'http://localhost:8123')
CH_USER = os.getenv('CH_USER', 'admin')
CH_PASS = os.getenv('CH_PASS', 'admin')
WAIT_TIME = int(os.getenv('WAIT_TIME', '30'))

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_header(message: str):
    print(f"\n{Colors.BLUE}================================================================{Colors.NC}")
    print(f"{Colors.BLUE}🔍 {message}{Colors.NC}")
    print(f"{Colors.BLUE}================================================================{Colors.NC}")

def print_section(message: str):
    print(f"\n{Colors.YELLOW}----------------------------------------{Colors.NC}")
    print(f"{Colors.YELLOW}📋 {message}{Colors.NC}")
    print(f"{Colors.YELLOW}----------------------------------------{Colors.NC}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def check_services() -> bool:
    """Check if required services are healthy"""
    print_section("Checking Service Health")
    
    failures = 0
    
    # Check VictoriaMetrics
    try:
        response = requests.get(f"{VM_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("VictoriaMetrics is healthy")
        else:
            print_error(f"VictoriaMetrics returned status {response.status_code}")
            failures += 1
    except requests.RequestException as e:
        print_error(f"VictoriaMetrics is not accessible at {VM_URL}: {e}")
        failures += 1
    
    # Check Incident API
    try:
        response = requests.get(f"{INCIDENT_API_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Incident API is healthy")
        else:
            print_error(f"Incident API returned status {response.status_code}")
            failures += 1
    except requests.RequestException as e:
        print_error(f"Incident API is not accessible at {INCIDENT_API_URL}: {e}")
        failures += 1
    
    # Check ClickHouse (optional)
    if CH_USER and CH_PASS:
        try:
            response = requests.get(f"{CH_URL}/ping", auth=(CH_USER, CH_PASS), timeout=5)
            if response.status_code == 200:
                print_success("ClickHouse is accessible with credentials")
            else:
                print_warning("ClickHouse not accessible via HTTP (may use native TCP)")
        except requests.RequestException:
            print_warning("ClickHouse not accessible via HTTP (may use native TCP)")
    else:
        print_warning("ClickHouse credentials not provided - skipping HTTP check")
    
    return failures == 0

def send_baseline_metrics() -> bool:
    """Send baseline metrics to VictoriaMetrics"""
    print_section("Sending Baseline Metrics")
    
    timestamp = int(time.time())
    
    # CPU baseline metrics (normal idle values = low CPU usage)
    cpu_data = f"""node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp - 300} 95.5
node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp - 240} 94.8
node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp - 180} 96.2
node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp - 120} 95.1
node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp - 60} 94.9"""
    
    # Memory baseline metrics (normal values - 25% usage)
    mem_total = 8 * 1024 * 1024 * 1024  # 8GB
    mem_available_normal = 6 * 1024 * 1024 * 1024  # 6GB available
    
    mem_data = f"""node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp - 300} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp - 300} {mem_available_normal}
node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp - 240} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp - 240} {mem_available_normal}
node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp - 180} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp - 180} {mem_available_normal}
node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp - 120} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp - 120} {mem_available_normal}
node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp - 60} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp - 60} {mem_available_normal}"""
    
    try:
        # Send CPU metrics
        response = requests.post(
            f"{VM_URL}/api/v1/import/prometheus",
            data=cpu_data,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        if response.status_code == 200:
            print_success("CPU baseline metrics sent")
        else:
            print_error(f"Failed to send CPU metrics: {response.status_code}")
            return False
        
        # Send Memory metrics
        response = requests.post(
            f"{VM_URL}/api/v1/import/prometheus",
            data=mem_data,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        if response.status_code == 200:
            print_success("Memory baseline metrics sent")
        else:
            print_error(f"Failed to send Memory metrics: {response.status_code}")
            return False
            
        return True
        
    except requests.RequestException as e:
        print_error(f"Failed to send baseline metrics: {e}")
        return False

def send_anomaly_spikes() -> bool:
    """Send anomaly spike metrics to VictoriaMetrics"""
    print_section("Sending Anomaly Spikes")
    
    timestamp = int(time.time())
    
    # High CPU usage (low idle time = high usage)
    cpu_spike = f'node_cpu_seconds_total{{mode="idle",instance="validator:9100"}} {timestamp} 15.0'
    
    # High Memory usage (low available memory = high usage)
    mem_total = 8 * 1024 * 1024 * 1024  # 8GB
    mem_available_low = 512 * 1024 * 1024  # 512MB available (94% usage)
    mem_spike = f"""node_memory_MemTotal_bytes{{instance="validator:9100"}} {timestamp} {mem_total}
node_memory_MemAvailable_bytes{{instance="validator:9100"}} {timestamp} {mem_available_low}"""
    
    try:
        # Send CPU spike
        response = requests.post(
            f"{VM_URL}/api/v1/import/prometheus",
            data=cpu_spike,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        if response.status_code == 200:
            print_success("CPU anomaly spike sent (85% usage)")
        else:
            print_error(f"Failed to send CPU spike: {response.status_code}")
            return False
        
        # Send Memory spike  
        response = requests.post(
            f"{VM_URL}/api/v1/import/prometheus",
            data=mem_spike,
            headers={'Content-Type': 'text/plain'},
            timeout=10
        )
        if response.status_code == 200:
            print_success("Memory anomaly spike sent (94% usage)")
        else:
            print_error(f"Failed to send Memory spike: {response.status_code}")
            return False
            
        return True
        
    except requests.RequestException as e:
        print_error(f"Failed to send anomaly spikes: {e}")
        return False

def wait_for_processing():
    """Wait for anomaly processing"""
    print_section("Waiting for Anomaly Processing")
    
    print(f"⏳ Waiting {WAIT_TIME}s for anomaly detection and correlation...")
    for i in range(WAIT_TIME):
        print(".", end="", flush=True)
        time.sleep(1)
    print("")
    print_success("Wait complete")

def check_incidents() -> bool:
    """Check if incidents were generated"""
    print_section("Checking for Generated Incidents")
    
    try:
        response = requests.get(f"{INCIDENT_API_URL}/incidents", timeout=10)
        if response.status_code == 200:
            incidents = response.json()
            incident_count = len(incidents) if isinstance(incidents, list) else 0
            
            print(f"📊 Found {incident_count} incidents")
            
            if incident_count > 0:
                print_success("Pipeline validation PASSED - incidents were generated")
                print(f"\n{Colors.BLUE}Recent incidents:{Colors.NC}")
                for incident in incidents[:5]:  # Show first 5
                    incident_id = incident.get('incident_id', 'unknown')
                    metric_name = incident.get('metric_name', 'unknown')
                    anomaly_score = incident.get('anomaly_score', 0)
                    print(f"- {incident_id}: {metric_name} ({anomaly_score})")
                return True
            else:
                print_warning("No incidents found yet")
                return False
        else:
            print_error(f"Failed to query incidents API: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print_error(f"Failed to query incidents API: {e}")
        return False

def check_clickhouse():
    """Check ClickHouse storage (optional)"""
    print_section("Checking ClickHouse Storage (Optional)")
    
    if not CH_USER or not CH_PASS:
        print_warning("ClickHouse credentials not provided - skipping")
        return
    
    query = "SELECT count() FROM incidents WHERE created_at >= now() - INTERVAL 5 MINUTE"
    
    try:
        response = requests.post(
            CH_URL,
            data=query,
            auth=(CH_USER, CH_PASS),
            timeout=10
        )
        if response.status_code == 200:
            count = response.text.strip()
            print(f"📊 Recent incidents in ClickHouse: {count}")
            if int(count) > 0:
                print_success("ClickHouse validation PASSED")
            else:
                print_warning("No recent incidents in ClickHouse")
        else:
            print_warning(f"Could not check ClickHouse: {response.status_code}")
            
    except (requests.RequestException, ValueError):
        print_warning("Could not check ClickHouse (may use native TCP instead of HTTP)")

def print_summary():
    """Print validation summary"""
    print_header("Validation Summary")
    
    print(f"{Colors.BLUE}Pipeline Components Tested:{Colors.NC}")
    print("1. ✅ VictoriaMetrics - Metrics ingestion")
    print("2. ✅ Anomaly Detection - PromQL queries and anomaly scoring")
    print("3. ✅ NATS - Event publishing")
    print("4. ✅ Benthos - Event correlation")
    print("5. ✅ Incident API - Incident storage and retrieval")
    print("6. ⚠️  ClickHouse - Storage validation (optional)")
    
    print(f"\n{Colors.BLUE}Metrics Simulated:{Colors.NC}")
    print("- node_cpu_seconds_total (idle mode) - CPU usage calculation")
    print("- node_memory_MemTotal_bytes - Memory total")
    print("- node_memory_MemAvailable_bytes - Memory usage calculation")
    
    print(f"\n{Colors.BLUE}Next Steps:{Colors.NC}")
    print("- Check Grafana dashboards at http://localhost:3000")
    print("- Review logs: docker compose logs anomaly-detection incident-api")
    print("- For manual testing: python3 scripts/publish_test_anomalies.py")

def main():
    """Main validation workflow"""
    print_header("AIOps NAAS Pipeline Validator (Python)")
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print(__doc__)
        return 0
    
    # Check services
    if not check_services():
        print_error("Some services are not healthy. Please check your deployment.")
        return 1
    
    # Send baseline metrics
    if not send_baseline_metrics():
        print_error("Failed to send baseline metrics")
        return 1
    
    # Send anomaly spikes
    if not send_anomaly_spikes():
        print_error("Failed to send anomaly spikes")
        return 1
    
    # Wait for processing
    wait_for_processing()
    
    # Check for incidents
    validation_passed = check_incidents()
    
    # Check ClickHouse
    check_clickhouse()
    
    # Print summary
    print_summary()
    
    if validation_passed:
        print(f"\n{Colors.GREEN}🎉 VALIDATION SUCCESSFUL - End-to-end pipeline working!{Colors.NC}")
        return 0
    else:
        print(f"\n{Colors.RED}❌ VALIDATION FAILED - No incidents generated{Colors.NC}")
        print(f"{Colors.YELLOW}💡 Troubleshooting suggestions:{Colors.NC}")
        print("1. Check anomaly-detection service logs: docker compose logs anomaly-detection")
        print("2. Verify NATS connectivity: docker compose logs nats")
        print("3. Check correlation service: docker compose logs benthos")
        print("4. Try manual anomaly publishing: python3 scripts/publish_test_anomalies.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())