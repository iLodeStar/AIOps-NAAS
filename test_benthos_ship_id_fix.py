#!/usr/bin/env python3
"""
Test script for Benthos ship_id and device_id extraction fix
Tests the field mapping logic with sample data from the problem statement
"""

import json
import requests
import time
import subprocess
import os

# Sample data from the problem statement
log_anomaly_sample = {
    "timestamp": "2025-09-16T15:36:31.884894",
    "metric_name": "log_anomaly",
    "metric_value": 1.0,
    "anomaly_score": 0.85,
    "anomaly_type": "log_pattern",
    "detector_name": "log_pattern_detector",
    "threshold": 0.7,
    "metadata": {
        "log_message": "omfwd: remote server at 127.0.0.1:1516 seems to have closed connection...",
        "tracking_id": None,
        "log_level": "INFO",
        "source_host": "ubuntu",
        "service": "rsyslogd",
        "anomaly_severity": "high",
        "original_timestamp": "2025-09-16 15:36:31.000",
        "ship_id": "ship-test",
        "device_id": "dev_88f60a33198f"
    },
    "labels": {}
}

# Metrics anomaly sample for comparison
metrics_anomaly_sample = {
    "timestamp": "2025-09-16T15:36:12.456174",
    "metric_name": "memory_usage",
    "metric_value": 66.89349130164545,
    "anomaly_score": 0.7419725012189122,
    "anomaly_type": "statistical_with_baseline",
    "detector_name": "enhanced_detector",
    "threshold": 0.6,
    "metadata": {
        "query": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
        "vm_timestamp": 1758036969,
        # ... other metadata fields
    },
    "labels": {
        "instance": "node-exporter:9100",
        "job": "node-exporter"
    }
}

def test_benthos_processing():
    """Test that Benthos correctly processes the sample data"""
    print("🧪 Testing Benthos ship_id and device_id extraction fix...")
    
    try:
        # Check if Benthos is running
        benthos_response = requests.get("http://localhost:4195/ping", timeout=5)
        if benthos_response.status_code != 200:
            print("❌ Benthos is not responding. Please start services first.")
            return False
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to Benthos. Please start services first.")
        return False
    
    # Check if NATS is available for publishing test data
    try:
        nats_test = subprocess.run([
            "docker", "exec", "aiops-nats", "nats", "pub", "test.connection", "ping"
        ], capture_output=True, text=True, timeout=10)
        if nats_test.returncode != 0:
            print("❌ Cannot connect to NATS. Please start services first.")
            return False
    except subprocess.TimeoutExpired:
        print("❌ NATS connection test timed out.")
        return False
    
    print("✅ Services are running. Testing field extraction...")
    
    # Test 1: Log anomaly with metadata.ship_id and metadata.device_id
    print("\n📝 Test 1: Log anomaly with metadata fields")
    test_log_anomaly(log_anomaly_sample)
    
    # Test 2: Metrics anomaly with labels
    print("\n📊 Test 2: Metrics anomaly with labels")
    test_metrics_anomaly(metrics_anomaly_sample)
    
    return True

def test_log_anomaly(sample_data):
    """Test log anomaly processing"""
    print(f"   Input ship_id: {sample_data['metadata']['ship_id']}")
    print(f"   Input device_id: {sample_data['metadata']['device_id']}")
    print(f"   Input service: {sample_data['metadata']['service']}")
    print(f"   Input metric_value: {sample_data['metric_value']}")
    
    # Publish to anomaly.detected topic
    try:
        publish_cmd = [
            "docker", "exec", "aiops-nats", "nats", "pub", "anomaly.detected", 
            json.dumps(sample_data)
        ]
        result = subprocess.run(publish_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"❌ Failed to publish test data: {result.stderr}")
            return
        
        print("   ✅ Published log anomaly to anomaly.detected")
        
        # Wait for processing
        time.sleep(2)
        
        # Check incidents.created topic for results
        subscribe_cmd = [
            "docker", "exec", "aiops-nats", "nats", "sub", "incidents.created", 
            "--count=1", "--timeout=5s"
        ]
        result = subprocess.run(subscribe_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout:
            # Parse the incident data
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{'):
                    try:
                        incident_data = json.loads(line)
                        print(f"   ✅ Output ship_id: {incident_data.get('ship_id', 'NOT_FOUND')}")
                        print(f"   ✅ Output device_id: {incident_data.get('device_id', 'NOT_FOUND')}")
                        print(f"   ✅ Output service: {incident_data.get('service', 'NOT_FOUND')}")
                        print(f"   ✅ Output metric_value: {incident_data.get('metric_value', 'NOT_FOUND')}")
                        
                        # Check if the fix worked
                        expected_ship = "ship-test"
                        expected_device = "dev_88f60a33198f"
                        expected_service = "rsyslogd"
                        expected_value = 1.0
                        
                        if (incident_data.get('ship_id') == expected_ship and
                            incident_data.get('device_id') == expected_device and
                            incident_data.get('service') == expected_service and
                            incident_data.get('metric_value') == expected_value):
                            print("   🎉 SUCCESS: All fields extracted correctly!")
                        else:
                            print("   ❌ FAIL: Some fields not extracted correctly")
                            print(f"      Expected ship_id: {expected_ship}, got: {incident_data.get('ship_id')}")
                            print(f"      Expected device_id: {expected_device}, got: {incident_data.get('device_id')}")
                            print(f"      Expected service: {expected_service}, got: {incident_data.get('service')}")
                            print(f"      Expected metric_value: {expected_value}, got: {incident_data.get('metric_value')}")
                        break
                    except json.JSONDecodeError:
                        continue
        else:
            print("   ❌ No incident created or timeout reached")
            
    except subprocess.TimeoutExpired:
        print("   ❌ Test timed out")
    except Exception as e:
        print(f"   ❌ Test failed: {str(e)}")

def test_metrics_anomaly(sample_data):
    """Test metrics anomaly processing (should use device registry lookup)"""
    print(f"   Input labels.instance: {sample_data['labels'].get('instance', 'NOT_FOUND')}")
    print(f"   Input labels.job: {sample_data['labels'].get('job', 'NOT_FOUND')}")
    print(f"   Input metric_value: {sample_data['metric_value']}")
    
    # Publish to anomaly.detected topic
    try:
        publish_cmd = [
            "docker", "exec", "aiops-nats", "nats", "pub", "anomaly.detected", 
            json.dumps(sample_data)
        ]
        result = subprocess.run(publish_cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print(f"❌ Failed to publish test data: {result.stderr}")
            return
        
        print("   ✅ Published metrics anomaly to anomaly.detected")
        
        # Wait for processing
        time.sleep(2)
        
        # Check incidents.created topic for results
        subscribe_cmd = [
            "docker", "exec", "aiops-nats", "nats", "sub", "incidents.created", 
            "--count=1", "--timeout=5s"
        ]
        result = subprocess.run(subscribe_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout:
            # Parse the incident data
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{'):
                    try:
                        incident_data = json.loads(line)
                        print(f"   ✅ Output ship_id: {incident_data.get('ship_id', 'NOT_FOUND')}")
                        print(f"   ✅ Output device_id: {incident_data.get('device_id', 'NOT_FOUND')}")
                        print(f"   ✅ Output service: {incident_data.get('service', 'NOT_FOUND')}")
                        print(f"   ✅ Output metric_value: {incident_data.get('metric_value', 'NOT_FOUND')}")
                        
                        # For metrics, we expect device registry lookup or fallback
                        if incident_data.get('metric_value') == sample_data['metric_value']:
                            print("   🎉 SUCCESS: Metric value preserved correctly!")
                        else:
                            print("   ❌ FAIL: Metric value not preserved")
                        break
                    except json.JSONDecodeError:
                        continue
        else:
            print("   ❌ No incident created or timeout reached")
            
    except subprocess.TimeoutExpired:
        print("   ❌ Test timed out")
    except Exception as e:
        print(f"   ❌ Test failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Benthos Ship ID and Device ID Extraction Fix Tester")
    print("=" * 60)
    
    if not test_benthos_processing():
        print("\n❌ Tests could not run. Please ensure Docker services are started.")
        exit(1)
    
    print("\n📋 Test Summary:")
    print("   - Log anomalies should extract ship_id and device_id from metadata")
    print("   - Metrics anomalies should use device registry lookup or fallbacks")
    print("   - All metric_value fields should be preserved correctly")
    print("\n🔧 If tests fail, check the Benthos configuration in benthos/benthos.yaml")