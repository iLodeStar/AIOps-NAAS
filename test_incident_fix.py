#!/usr/bin/env python3
"""
Test script for the incident creation fix - Issue #103

This script tests that the anomaly detection -> incident creation pipeline
properly resolves ship_id, service, and other fields from device registry.
"""

import requests
import json
import time
import uuid
from datetime import datetime, timezone

def test_anomaly_to_incident_pipeline():
    """Test the complete pipeline from anomaly detection to incident creation"""
    print("🧪 Testing Anomaly to Incident Pipeline Fix (Issue #103)")
    print("=" * 60)
    
    # Create the exact anomaly event structure from the issue
    test_anomaly_event = {
        "timestamp": "2025-09-11T16:31:55.382021",
        "metric_name": "log_anomaly",
        "metric_value": 1.0,
        "anomaly_score": 0.8,
        "anomaly_type": "log_pattern",
        "detector_name": "log_pattern_detector",
        "threshold": 0.7,
        "metadata": {
            "log_message": "rsyslogd: omfwd: remote server at 127.0.0.1:1516 seems to have closed connection.",
            "tracking_id": None,
            "log_level": "INFO",
            "source_host": "ubuntu",  # This is the key field that should resolve to ship-dhruv
            "service": "rsyslogd",    # This should be preserved in incidents
            "anomaly_severity": "low",
            "original_timestamp": "2025-09-11 16:31:55.000"
        },
        "labels": {}
    }
    
    # Check device registry is working
    print("\n1. Testing device registry lookup...")
    try:
        registry_response = requests.get("http://localhost:8081/lookup/ubuntu", timeout=10)
        if registry_response.status_code == 200:
            registry_data = registry_response.json()
            print(f"✅ Device registry lookup successful:")
            print(f"   hostname: ubuntu -> ship_id: {registry_data['mapping']['ship_id']}")
            expected_ship_id = registry_data['mapping']['ship_id']
        else:
            print(f"❌ Device registry lookup failed: {registry_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Device registry connection failed: {e}")
        return False
    
    # Test Benthos processing
    print("\n2. Testing Benthos anomaly processing...")
    try:
        # Send anomaly event to Benthos (assuming it listens on anomaly.detected subject)
        # For testing, we'll send it via HTTP if Benthos HTTP interface is available
        benthos_response = requests.post(
            "http://localhost:4195/post",  # Benthos HTTP interface
            json=test_anomaly_event,
            timeout=10
        )
        
        if benthos_response.status_code == 200:
            print("✅ Benthos processed anomaly event successfully")
        else:
            print(f"⚠️  Benthos HTTP response: {benthos_response.status_code}")
    except Exception as e:
        print(f"⚠️  Benthos HTTP test failed (expected if HTTP disabled): {e}")
    
    # Wait a moment for incident creation
    print("\n3. Waiting for incident creation...")
    time.sleep(3)
    
    # Check incident API for recent incidents
    print("\n4. Checking incident API for created incidents...")
    try:
        incidents_response = requests.get("http://localhost:8081/incidents?limit=5", timeout=10)
        if incidents_response.status_code == 200:
            incidents = incidents_response.json()
            print(f"✅ Retrieved {len(incidents)} recent incidents")
            
            # Look for incidents with our expected ship_id
            matching_incidents = [
                inc for inc in incidents 
                if inc.get('ship_id') == expected_ship_id and inc.get('service') == 'rsyslogd'
            ]
            
            if matching_incidents:
                incident = matching_incidents[0]
                print(f"✅ Found matching incident:")
                print(f"   incident_id: {incident['incident_id']}")
                print(f"   ship_id: {incident['ship_id']} (expected: {expected_ship_id})")
                print(f"   service: {incident['service']} (expected: rsyslogd)")
                print(f"   incident_severity: {incident['incident_severity']}")
                print(f"   metric_name: {incident['metric_name']}")
                
                # Validate fields are not empty/unknown
                validation_results = {
                    "ship_id_correct": incident['ship_id'] == expected_ship_id,
                    "service_correct": incident['service'] == 'rsyslogd',
                    "ship_id_not_unknown": incident['ship_id'] != 'unknown-ship',
                    "service_not_unknown": incident['service'] != 'unknown_service',
                    "severity_not_empty": incident['incident_severity'] != '',
                    "metric_name_correct": incident['metric_name'] == 'log_anomaly'
                }
                
                print(f"\n5. Validation Results:")
                all_passed = True
                for check, passed in validation_results.items():
                    status = "✅" if passed else "❌"
                    print(f"   {status} {check}: {passed}")
                    if not passed:
                        all_passed = False
                
                return all_passed
            else:
                print(f"❌ No incidents found with expected ship_id '{expected_ship_id}' and service 'rsyslogd'")
                if incidents:
                    print("   Available incidents:")
                    for inc in incidents[:3]:
                        print(f"   - ship_id: {inc.get('ship_id')}, service: {inc.get('service')}")
                return False
        else:
            print(f"❌ Incident API failed: {incidents_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Incident API connection failed: {e}")
        return False

def test_device_registry_standalone():
    """Test device registry service independently"""
    print("\n" + "=" * 60)
    print("🔍 Testing Device Registry Service")
    print("=" * 60)
    
    try:
        # Test health endpoint
        health_response = requests.get("http://localhost:8081/health", timeout=5)
        print(f"Device registry health: {health_response.status_code}")
        
        # Test lookup for known hostname
        lookup_response = requests.get("http://localhost:8081/lookup/ubuntu", timeout=5)
        if lookup_response.status_code == 200:
            data = lookup_response.json()
            print(f"✅ Lookup successful: ubuntu -> {data['mapping']['ship_id']}")
            return True
        else:
            print(f"❌ Lookup failed: {lookup_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Device registry test failed: {e}")
        return False

def test_incident_api_standalone():
    """Test incident API service independently"""
    print("\n" + "=" * 60)
    print("🔍 Testing Incident API Service")  
    print("=" * 60)
    
    try:
        # Test health endpoint
        health_response = requests.get("http://localhost:8081/health", timeout=5)
        print(f"Incident API health: {health_response.status_code}")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"Health status: {health_data}")
        
        # Test incidents endpoint
        incidents_response = requests.get("http://localhost:8081/incidents?limit=3", timeout=5)
        if incidents_response.status_code == 200:
            incidents = incidents_response.json()
            print(f"✅ Retrieved {len(incidents)} incidents")
            if incidents:
                print("Recent incidents:")
                for inc in incidents:
                    print(f"  - ID: {inc['incident_id'][:8]}... ship_id: {inc['ship_id']} service: {inc['service']}")
            return True
        else:
            print(f"❌ Incidents endpoint failed: {incidents_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Incident API test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Incident Pipeline Fix Validation")
    print("=" * 60)
    
    # Run standalone tests first
    registry_ok = test_device_registry_standalone()
    incident_api_ok = test_incident_api_standalone()
    
    if not (registry_ok and incident_api_ok):
        print("\n❌ Prerequisites failed - ensure services are running")
        exit(1)
    
    # Run full pipeline test
    success = test_anomaly_to_incident_pipeline()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Incident pipeline fix is working!")
    else:
        print("❌ TESTS FAILED - Fix needs more work")
    print("=" * 60)