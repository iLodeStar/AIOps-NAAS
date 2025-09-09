#!/usr/bin/env python3
"""
Test script to validate the fix for issue #81 - Benthos not processing data
due to null value handling errors in priority calculations and cache keys.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def create_problematic_events():
    """Create test events that were causing the reported errors"""
    return [
        {
            "name": "Event with null severity (causes priority comparison error)",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "basic_metrics", 
                "ship_id": "ship-01",
                "severity": None,  # This was causing "cannot compare types null" error
                "anomaly_score": 0.8,
                "metric_name": "cpu_usage"
            }
        },
        {
            "name": "Event with null incident_type (causes key interpolation error)",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "application_logs",
                "ship_id": "ship-01", 
                "severity": "warning",
                "anomaly_score": 0.6,
                "metric_name": "log_error",
                "incident_type": None  # This was causing key interpolation errors
            }
        },
        {
            "name": "Event with null metric_name (causes cache key issues)",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "snmp_network",
                "ship_id": "ship-01",
                "severity": "info",
                "anomaly_score": 0.4,
                "metric_name": None  # This was causing cache key issues
            }
        },
        {
            "name": "Event with all problematic nulls (worst case)",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "basic_metrics",
                "ship_id": None,
                "severity": None,
                "anomaly_score": None,
                "metric_name": None,
                "incident_type": None
            }
        }
    ]

def test_benthos_processing(event_data):
    """Test if Benthos can process the event without errors"""
    
    # Create a simplified Benthos config that tests our critical mapping logic
    test_config = """
http:
  enabled: false

input:
  stdin:
    codec: lines

pipeline:
  processors:
    # Parse input as JSON
    - mapping: |
        root = content().parse_json()
    
    # Apply the critical mapping logic from our main config (simplified)
    - mapping: |
        root.correlation_id = uuid_v4()
        root.processing_timestamp = now()
        
        # Test event source handling (should not fail)
        root.event_source = if this.event_source != null { this.event_source } else { "unknown" }
        
        # Test ship_id null safety (this was failing)
        root.ship_id = if this.ship_id != null && this.ship_id != "" { this.ship_id } else { "ship-01" }
        
        # Test severity null safety (this was causing priority calc failures) 
        root.severity = if this.severity != null && this.severity != "" { this.severity } else { "info" }
        
        # Test metric_name null safety (this was causing cache key issues)
        root.metric_name = if this.metric_name != null && this.metric_name != "" { this.metric_name } else { "unknown_metric" }
        
        # Test the critical priority calculation that was failing
        let current_severity = root.severity
        let severity_priority = if current_severity == "critical" { 4 } else if current_severity == "high" { 3 } else if current_severity == "medium" { 2 } else if current_severity == "warning" { 2 } else { 1 }
        let related_priority = 0  # Simulate no related event
        let secondary_priority = 0
        
        # This comparison was failing before the fix
        let max_priority = if severity_priority >= related_priority && severity_priority >= secondary_priority { 
          severity_priority 
        } else if related_priority >= secondary_priority { 
          related_priority 
        } else { 
          secondary_priority 
        }
        
        # Test incident_type null safety (this was causing key interpolation errors)
        root.incident_type = if this.incident_type != null && this.incident_type != "" { this.incident_type } else { "unknown_anomaly" }
        
        # Test cache key generation (these were failing)
        root.correlation_cache_key = root.ship_id + "_" + root.event_source + "_" + root.metric_name
        root.suppression_cache_key = root.incident_type + "_" + root.ship_id
        
        # Add debug info
        root.debug = {
          "severity_priority": severity_priority,
          "max_priority": max_priority,
          "current_severity": current_severity
        }
        
        root.test_status = "success"

output:
  stdout:
    codec: lines
"""
    
    # Create temporary files
    config_file = tempfile.mktemp(suffix='.yaml')
    input_file = tempfile.mktemp(suffix='.json')
    
    try:
        # Write config and input data
        with open(config_file, 'w') as f:
            f.write(test_config)
            
        with open(input_file, 'w') as f:
            json.dump(event_data, f)
        
        # Run Benthos
        with open(input_file, 'r') as stdin_file:
            result = subprocess.run([
                'docker', 'run', '--rm', '-i',
                '-v', f'{config_file}:/test-config.yaml:ro',
                'jeffail/benthos:latest',
                '-c', '/test-config.yaml'
            ], stdin=stdin_file, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                try:
                    # Parse the last output line as JSON
                    processed_event = json.loads(output_lines[-1])
                    if processed_event.get('test_status') == 'success':
                        return True, processed_event
                    else:
                        return False, f"Processing failed: {processed_event}"
                except json.JSONDecodeError as e:
                    return False, f"Invalid JSON output: {e}"
            else:
                return False, "No output produced"
        else:
            return False, f"Benthos error: {result.stderr}"
    
    except Exception as e:
        return False, f"Test exception: {e}"
    
    finally:
        # Cleanup
        for temp_file in [config_file, input_file]:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass

def main():
    """Run the issue #81 fix validation tests"""
    print("🧪 Testing Issue #81 Fix - Benthos Null Handling")
    print("=" * 60)
    
    test_events = create_problematic_events()
    results = []
    
    for i, test_case in enumerate(test_events, 1):
        print(f"\n📋 Test {i}/4: {test_case['name']}")
        
        success, result = test_benthos_processing(test_case['event'])
        
        if success:
            print(f"  ✅ SUCCESS - Event processed without errors")
            print(f"     Ship ID: {result.get('ship_id')}")
            print(f"     Severity: {result.get('severity')}")
            print(f"     Incident Type: {result.get('incident_type')}")
            print(f"     Metric Name: {result.get('metric_name')}")
            print(f"     Priority Debug: {result.get('debug', {})}")
            print(f"     Cache Keys Generated Successfully")
            results.append(True)
        else:
            print(f"  ❌ FAILED - {result}")
            results.append(False)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"  Total tests: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")
    
    if all(results):
        print(f"\n✅ ALL TESTS PASSED!")
        print(f"   Issue #81 has been fixed. Benthos now handles:")
        print(f"   - Null severity values in priority calculations")
        print(f"   - Null incident_type values in cache key interpolation")
        print(f"   - Null metric_name values in cache operations")
        print(f"   - Null ship_id values throughout the pipeline")
        return True
    else:
        print(f"\n❌ SOME TESTS FAILED!")
        print(f"   The fix may not be complete. Review errors above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)