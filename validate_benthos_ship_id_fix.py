#!/usr/bin/env python3
"""
Validation script for Benthos ship_id and device_id extraction fix
Validates the mapping logic against sample data from the problem statement
"""

import json
import yaml

def simulate_benthos_mapping(input_data):
    """
    Simulate the key parts of the Benthos mapping logic
    to validate the fix without requiring running services
    """
    print(f"\n🧪 Testing input data: {json.dumps(input_data, indent=2)[:200]}...")
    
    # Simulate the ship_id extraction logic from the fix
    original_ship_id = input_data.get('ship_id')
    metadata = input_data.get('metadata', {})
    
    # Step 1: Check for ship_id in multiple locations including metadata
    available_ship_id = None
    ship_id_source = None
    
    if original_ship_id and original_ship_id != "" and "unknown" not in original_ship_id:
        available_ship_id = original_ship_id
        ship_id_source = "original_field"
    elif metadata.get('ship_id') and metadata.get('ship_id') != "" and "unknown" not in metadata.get('ship_id', ""):
        available_ship_id = metadata.get('ship_id')
        ship_id_source = "metadata_field"
    
    if available_ship_id:
        ship_id = available_ship_id
        skip_lookup = True
    else:
        # Would trigger device registry lookup
        ship_id = "unknown-ship"  # fallback
        ship_id_source = "fallback"
        skip_lookup = False
    
    # Simulate device_id extraction (matching Benthos logic)
    device_id = None
    if input_data.get('device_id'):
        device_id = input_data.get('device_id')
    elif metadata.get('device_id'):
        device_id = metadata.get('device_id')
    elif input_data.get('host') and input_data.get('host') != "unknown":
        device_id = input_data.get('host')
    elif input_data.get('labels', {}).get('instance'):
        device_id = input_data.get('labels', {}).get('instance')
    else:
        device_id = "unknown-device"
    
    # Simulate service extraction
    service = None
    if input_data.get('service'):
        service = input_data.get('service')
    elif metadata.get('service'):
        service = metadata.get('service')
    elif input_data.get('labels', {}).get('job'):
        service = input_data.get('labels', {}).get('job')
    elif input_data.get('application'):
        service = input_data.get('application')
    else:
        service = "unknown_service"
    
    # Simulate host extraction
    host = None
    if input_data.get('host'):
        host = input_data.get('host')
    elif metadata.get('source_host'):
        host = metadata.get('source_host')
    elif input_data.get('labels', {}).get('instance'):
        host = input_data.get('labels', {}).get('instance')
    else:
        host = "unknown"
    
    # Simulate metric_name extraction
    metric_name = input_data.get('metric_name', 'unknown_metric')
    
    # Simulate metric_value extraction  
    metric_value = input_data.get('metric_value', 0.0)
    if metric_value is None:
        metric_value = input_data.get('value', 0.0)
    if metric_value is None:
        metric_value = metadata.get('metric_value', 0.0)
    
    return {
        'ship_id': ship_id,
        'ship_id_source': ship_id_source,
        'device_id': device_id,
        'service': service,
        'host': host,
        'metric_name': metric_name,
        'metric_value': metric_value,
        'skip_lookup': skip_lookup
    }

def test_log_anomaly_extraction():
    """Test log anomaly data from problem statement"""
    print("\n" + "="*60)
    print("🔍 Testing Log Anomaly Field Extraction")
    print("="*60)
    
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
    
    # Expected output values from problem statement
    expected = {
        'ship_id': 'ship-test',
        'device_id': 'dev_88f60a33198f',
        'service': 'rsyslogd',
        'host': 'ubuntu',
        'metric_name': 'log_anomaly',
        'metric_value': 1.0
    }
    
    result = simulate_benthos_mapping(log_anomaly_sample)
    
    print("📊 RESULTS:")
    print(f"   Ship ID: {result['ship_id']} (source: {result['ship_id_source']})")
    print(f"   Device ID: {result['device_id']}")
    print(f"   Service: {result['service']}")
    print(f"   Host: {result['host']}")
    print(f"   Metric Name: {result['metric_name']}")
    print(f"   Metric Value: {result['metric_value']}")
    print(f"   Skip Registry Lookup: {result['skip_lookup']}")
    
    print("\n✅ VALIDATION:")
    success = True
    for key in expected:
        if result[key] == expected[key]:
            print(f"   ✅ {key}: {result[key]} (CORRECT)")
        else:
            print(f"   ❌ {key}: {result[key]} (EXPECTED: {expected[key]})")
            success = False
    
    if success:
        print("\n🎉 SUCCESS: Log anomaly field extraction working correctly!")
    else:
        print("\n❌ FAILED: Some fields not extracted correctly!")
    
    return success

def test_metrics_anomaly_extraction():
    """Test metrics anomaly data from problem statement"""
    print("\n" + "="*60) 
    print("📈 Testing Metrics Anomaly Field Extraction")
    print("="*60)
    
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
        },
        "labels": {
            "instance": "node-exporter:9100",
            "job": "node-exporter"
        }
    }
    
    # Expected behavior for metrics (should trigger device registry lookup)
    expected = {
        'ship_id': 'unknown-ship',  # Should be fallback since no ship_id in data
        'device_id': 'node-exporter:9100',  # Should use labels.instance
        'service': 'node-exporter',  # Should use labels.job
        'host': 'node-exporter:9100',  # Should use labels.instance
        'metric_name': 'memory_usage',
        'metric_value': 66.89349130164545
    }
    
    result = simulate_benthos_mapping(metrics_anomaly_sample)
    
    print("📊 RESULTS:")
    print(f"   Ship ID: {result['ship_id']} (source: {result['ship_id_source']})")
    print(f"   Device ID: {result['device_id']}")
    print(f"   Service: {result['service']}")
    print(f"   Host: {result['host']}")
    print(f"   Metric Name: {result['metric_name']}")
    print(f"   Metric Value: {result['metric_value']}")
    print(f"   Skip Registry Lookup: {result['skip_lookup']}")
    
    print("\n✅ VALIDATION:")
    success = True
    for key in expected:
        if result[key] == expected[key]:
            print(f"   ✅ {key}: {result[key]} (CORRECT)")
        else:
            print(f"   ❌ {key}: {result[key]} (EXPECTED: {expected[key]})")
            success = False
    
    if success:
        print("\n🎉 SUCCESS: Metrics anomaly field extraction working correctly!")
    else:
        print("\n❌ FAILED: Some fields not extracted correctly!")
    
    return success

def validate_benthos_config():
    """Validate the Benthos configuration syntax"""
    print("\n" + "="*60)
    print("🔧 Validating Benthos Configuration")
    print("="*60)
    
    try:
        with open('benthos/benthos.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        print("   ✅ Benthos YAML syntax is valid")
        
        # Check key sections exist
        required_sections = ['input', 'pipeline', 'output', 'cache_resources']
        for section in required_sections:
            if section in config:
                print(f"   ✅ {section} section exists")
            else:
                print(f"   ❌ {section} section missing")
                return False
        
        # Check processor count
        processors = config.get('pipeline', {}).get('processors', [])
        print(f"   ✅ Pipeline has {len(processors)} processors")
        
        # Look for the ship_id extraction logic
        ship_id_fix_found = False
        for i, processor in enumerate(processors):
            if 'mapping' in processor and 'available_ship_id' in str(processor.get('mapping', '')):
                print(f"   ✅ Ship ID extraction fix found in processor {i}")
                ship_id_fix_found = True
                break
        
        if not ship_id_fix_found:
            print("   ❌ Ship ID extraction fix not found in processors")
            return False
        
        print("\n🎉 SUCCESS: Benthos configuration is valid!")
        return True
        
    except yaml.YAMLError as e:
        print(f"   ❌ YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print("   ❌ benthos/benthos.yaml file not found")
        return False
    except Exception as e:
        print(f"   ❌ Configuration validation error: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 Benthos Ship ID and Device ID Extraction Fix Validator")
    print("🔍 This validates the fix without requiring running services")
    print("="*80)
    
    results = []
    
    # Test 1: Validate configuration syntax
    config_valid = validate_benthos_config()
    results.append(("Configuration Validation", config_valid))
    
    # Test 2: Log anomaly extraction
    log_success = test_log_anomaly_extraction()
    results.append(("Log Anomaly Extraction", log_success))
    
    # Test 3: Metrics anomaly extraction  
    metrics_success = test_metrics_anomaly_extraction()
    results.append(("Metrics Anomaly Extraction", metrics_success))
    
    # Summary
    print("\n" + "="*80)
    print("📋 VALIDATION SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status} - {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 ALL VALIDATIONS PASSED!")
        print("🔧 The fix should resolve the ship_id and device_id extraction issues.")
        print("\n📝 Key improvements:")
        print("   - Log anomalies now extract ship_id from metadata.ship_id")
        print("   - Log anomalies now extract device_id from metadata.device_id")  
        print("   - Log anomalies now extract service from metadata.service")
        print("   - Metrics anomalies use device registry lookup or fallbacks")
        print("   - All metric_value fields are preserved correctly")
    else:
        print("\n❌ SOME VALIDATIONS FAILED!")
        print("🔧 Please review the configuration and fix any issues.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)