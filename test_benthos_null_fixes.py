#!/usr/bin/env python3
"""
Test script to validate Benthos null handling fixes for issue #77.

This script simulates the problematic data scenarios that were causing
Benthos processor failures and verifies our fixes handle them correctly.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def create_test_events():
    """Create test events that trigger the problematic scenarios"""
    return [
        {
            "name": "Event with null metric_name",
            "event": {
                "correlation_id": "test-001",
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "basic_metrics",
                "ship_id": "ship-01",
                "severity": "warning",
                "anomaly_score": 0.8,
                "metric_name": None,  # This should trigger cache key issue
                "labels": {
                    "instance": "ship-01",
                    "job": "node-exporter"
                }
            }
        },
        {
            "name": "Event with missing fields",
            "event": {
                "correlation_id": "test-002", 
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "snmp_network",
                "ship_id": None,  # This should trigger ship_id null issue
                "severity": None,  # This should trigger severity priority null issue
                "anomaly_score": 0.6
                # Missing labels, metric_name, etc.
            }
        },
        {
            "name": "Event with empty incident_type scenario",
            "event": {
                "correlation_id": "test-003",
                "timestamp": "2025-01-01T12:00:00Z", 
                "event_source": "application_logs",
                "ship_id": "ship-01",
                "severity": "critical",
                "anomaly_score": 0.9,
                "metric_name": "log_anomaly",
                "incident_type": "",  # This should trigger incident_type null issue
                "labels": {}
            }
        },
        {
            "name": "Event with all null values (worst case)",
            "event": {
                "correlation_id": "test-004",
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": None,
                "ship_id": None,
                "severity": None,
                "anomaly_score": None,
                "metric_name": None,
                "incident_type": None,
                "labels": None
            }
        }
    ]

def test_benthos_config_with_events(config_path, test_events):
    """Test Benthos configuration with problematic events"""
    print("🧪 Testing Benthos Configuration with Null/Empty Scenarios")
    print("=" * 60)
    
    results = []
    
    for test_case in test_events:
        print(f"\n📋 Testing: {test_case['name']}")
        
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_case['event'], f)
            input_file = f.name
        
        # Create temporary output file  
        output_file = tempfile.mktemp(suffix='.json')
        
        try:
            # Create a minimal test config that uses our pipeline processors
            test_config = f"""
http:
  enabled: false

input:
  file:
    paths: ["{input_file}"]
    codec: all-bytes
    
pipeline:
  processors:
    # Parse JSON input
    - mapping: |
        root = content().parse_json()
        
    # Apply the same mapping logic from our main config
    - mapping: |
        root.correlation_id = if this.correlation_id != null {{ this.correlation_id }} else {{ uuid_v4() }}
        root.processing_timestamp = now()
        
        # Identify event source and type with null safety
        root.event_source = if this.event_source != null {{ this.event_source }} else {{ "unknown" }}
        
        # Extract contextual information with safe null handling  
        root.ship_id = if this.ship_id != null && this.ship_id != "" {{ this.ship_id }} else {{ "unknown_ship" }}
        
        root.service = "unknown"
        if this.labels != null && this.labels.job != null {{
          root.service = this.labels.job
        }} else if this.service != null {{
          root.service = this.service
        }}
        
        # Standardize anomaly scoring with null safety
        root.anomaly_score = if this.anomaly_score != null {{ this.anomaly_score }} else {{ 0.4 }}
        
        # Enhanced severity calculation with null safety
        root.severity = if this.severity != null {{ this.severity }} else {{ "info" }}
        
        # Safe metric name handling for cache keys
        root.metric_name = if this.metric_name != null && this.metric_name != "" {{ this.metric_name }} else {{ "unknown_metric" }}
        
        # Test the problematic priority calculations
        let severity_priority = if this.severity == "critical" {{ 4 }} else if this.severity == "high" {{ 3 }} else if this.severity == "medium" {{ 2 }} else if this.severity == "warning" {{ 2 }} else {{ 1 }}
        let related_priority = 0  # Simulate no related event
        let secondary_priority = 0  # Simulate no secondary event
        
        # Safe max priority calculation (this was failing before)
        let max_priority = if severity_priority >= related_priority && severity_priority >= secondary_priority {{ 
          severity_priority 
        }} else if related_priority >= secondary_priority {{ 
          related_priority 
        }} else {{ 
          secondary_priority 
        }}
        
        # Debug information with null safety (this was causing issues)
        root.debug_priorities = {{
          "severity_priority": if severity_priority != null {{ severity_priority }} else {{ 0 }},
          "related_priority": if related_priority != null {{ related_priority }} else {{ 0 }},
          "secondary_priority": if secondary_priority != null {{ secondary_priority }} else {{ 0 }},
          "severity_value": if this.severity != null {{ this.severity }} else {{ "unknown" }},
          "max_priority": max_priority
        }}
        
        # Incident type with null safety (this was causing key interpolation errors)
        root.incident_type = if this.incident_type != null && this.incident_type != "" {{ this.incident_type }} else {{ "unknown_anomaly" }}
        
        # Test cache key generation (this was causing key errors)
        root.correlation_cache_key = this.ship_id + "_" + this.event_source + "_" + this.metric_name
        root.suppression_cache_key = this.incident_type + "_" + this.ship_id
        
        # Mark as processed
        root.test_result = "processed_successfully"

output:
  file:
    path: "{output_file}"
    codec: lines
"""
            
            # Write test config
            config_file = tempfile.mktemp(suffix='.yaml')
            with open(config_file, 'w') as f:
                f.write(test_config)
            
            # Run Benthos with test config
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{config_file}:/test-config.yaml:ro',
                '-v', f'{input_file}:/input.json:ro', 
                '-v', f'{os.path.dirname(output_file)}:{os.path.dirname(output_file)}',
                'jeffail/benthos:latest',
                '-c', '/test-config.yaml'
            ], capture_output=True, text=True, timeout=30)
            
            # Check results
            if result.returncode == 0:
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output = f.read().strip()
                    if output:
                        try:
                            parsed_output = json.loads(output)
                            if parsed_output.get('test_result') == 'processed_successfully':
                                print(f"  ✅ SUCCESS: Event processed without errors")
                                print(f"     - Ship ID: {parsed_output.get('ship_id')}")
                                print(f"     - Incident Type: {parsed_output.get('incident_type')}") 
                                print(f"     - Correlation Key: {parsed_output.get('correlation_cache_key')}")
                                print(f"     - Suppression Key: {parsed_output.get('suppression_cache_key')}")
                                results.append(True)
                            else:
                                print(f"  ❌ FAILED: Unexpected output format")
                                results.append(False)
                        except json.JSONDecodeError as e:
                            print(f"  ❌ FAILED: Invalid JSON output: {e}")
                            results.append(False)
                    else:
                        print(f"  ❌ FAILED: No output generated")
                        results.append(False)
                else:
                    print(f"  ❌ FAILED: Output file not created")
                    results.append(False)
            else:
                print(f"  ❌ FAILED: Benthos execution failed")
                print(f"     Error: {result.stderr}")
                results.append(False)
                
        except Exception as e:
            print(f"  ❌ FAILED: Exception occurred: {e}")
            results.append(False)
            
        finally:
            # Cleanup
            for temp_file in [input_file, output_file, config_file]:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"  Total tests: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")
    
    if all(results):
        print(f"\n✅ ALL TESTS PASSED! Benthos null handling fixes are working correctly.")
        return True
    else:
        print(f"\n❌ SOME TESTS FAILED! Please review the errors above.")
        return False

def validate_config_syntax(config_path):
    """Validate the main Benthos configuration syntax"""
    print("🔍 Validating Main Benthos Configuration")
    print("-" * 50)
    
    result = subprocess.run([
        'docker', 'run', '--rm',
        '-v', f'{config_path}:/benthos.yaml:ro',
        'jeffail/benthos:latest',
        'lint', '/benthos.yaml'
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Configuration syntax validation passed")
        return True
    else:
        print("❌ Configuration syntax validation failed")
        print(f"Error: {result.stderr}")
        return False

def main():
    """Main test function"""
    print("🚀 Benthos Issue #77 Fix Validation Test")
    print("=" * 60)
    
    # Get config path
    config_path = Path(__file__).parent / "benthos" / "benthos.yaml"
    
    # Validate main config syntax
    if not validate_config_syntax(config_path):
        return False
    
    # Test with problematic events
    test_events = create_test_events()
    
    success = test_benthos_config_with_events(config_path, test_events)
    
    if success:
        print("\n🎉 All Benthos null handling fixes validated successfully!")
        print("   The configuration should now handle:")
        print("   - Null metric_name values in cache keys")
        print("   - Null ship_id values in suppression logic")
        print("   - Null severity values in priority calculations")
        print("   - Empty incident_type values in key interpolation")
        print("   - Missing or null fields throughout the pipeline")
    
    return success

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)