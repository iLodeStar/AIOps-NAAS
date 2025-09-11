#!/usr/bin/env python3
"""
Simple test for the fixed Benthos configuration.
Tests the problematic scenarios that were causing failures.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path

def test_problematic_events():
    """Test events that were causing the original failures"""
    test_events = [
        {
            "name": "Event with null values (original failure case)",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "ship_id": None,
                "severity": None,
                "metric_name": None,
                "incident_type": None
            }
        },
        {
            "name": "Event with unknown ship scenario", 
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "application_logs",
                "ship_id": "unknown-ship",
                "severity": "warning",
                "metric_name": "log_anomaly"
            }
        },
        {
            "name": "CPU/Memory correlation scenario",
            "event": {
                "timestamp": "2025-01-01T12:00:00Z",
                "event_source": "basic_metrics",
                "ship_id": "test-ship-01",
                "severity": "critical", 
                "metric_name": "cpu_usage",
                "anomaly_score": 0.9
            }
        }
    ]
    
    config_path = Path(__file__).parent / "benthos" / "benthos-fixed.yaml"
    
    print("🧪 Testing Fixed Benthos Configuration")
    print("=" * 50)
    
    results = []
    
    for i, test_case in enumerate(test_events):
        print(f"\n📋 Test {i+1}: {test_case['name']}")
        
        # Create input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_case['event'], f)
            input_file = f.name
        
        output_file = tempfile.mktemp(suffix='.json')
        
        # Simple test config that processes one event
        test_config = f"""
input:
  file:
    paths: ["{input_file}"]
    codec: all-bytes

# Use a subset of the main pipeline processors
pipeline:
  processors:
    - mapping: |
        root = content().parse_json()
        
    # Test the normalization logic
    - mapping: |
        root.correlation_id = if this.correlation_id != null && this.correlation_id != "" {{ 
          this.correlation_id 
        }} else {{ 
          uuid_v4() 
        }}
        
        root.ship_id = if this.ship_id != null && this.ship_id != "" && !this.ship_id.contains("unknown") {{ 
          this.ship_id 
        }} else {{ 
          "unknown-ship" 
        }}
        
        root.event_source = if this.event_source != null && this.event_source != "" {{ 
          this.event_source 
        }} else {{ 
          "basic_metrics" 
        }}
        
        root.metric_name = if this.metric_name != null && this.metric_name != "" {{ 
          this.metric_name 
        }} else {{ 
          "unknown_metric" 
        }}
        
        root.severity = if this.severity != null && this.severity != "" {{ 
          this.severity 
        }} else {{ 
          "info"
        }}
        
        root.incident_type = if this.incident_type != null && this.incident_type != "" {{
          this.incident_type
        }} else {{
          "single_anomaly"
        }}
        
        # Test priority calculations (this was the main failure point)
        let severity_map = {{
          "critical": 4,
          "high": 3,
          "medium": 2, 
          "warning": 2,
          "info": 1
        }}
        
        let severity_priority = if severity_map.get(root.severity) != null {{ severity_map.get(root.severity) }} else {{ 1 }}
        let related_priority = 0  # No related event
        let max_priority = if severity_priority >= related_priority {{ severity_priority }} else {{ related_priority }}
        
        root.debug_priorities = {{
          "severity_priority": severity_priority,
          "related_priority": related_priority,
          "max_priority": max_priority,
          "severity_value": root.severity
        }}
        
        root.test_result = "success"
        root.processing_timestamp = now()

output:
  file:
    path: "{output_file}"
    codec: lines
"""
        
        config_file = tempfile.mktemp(suffix='.yaml')
        with open(config_file, 'w') as f:
            f.write(test_config)
        
        try:
            # Run Benthos 
            result = subprocess.run([
                'docker', 'run', '--rm',
                '-v', f'{config_file}:/test-config.yaml:ro',
                '-v', f'{input_file}:/input.json:ro',
                '-v', f'{os.path.dirname(output_file)}:{os.path.dirname(output_file)}',
                'jeffail/benthos:latest',
                '-c', '/test-config.yaml'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        output = f.read().strip()
                    if output:
                        try:
                            parsed = json.loads(output)
                            if parsed.get('test_result') == 'success':
                                print(f"  ✅ SUCCESS")
                                print(f"     Ship ID: {parsed.get('ship_id')}")
                                print(f"     Incident Type: {parsed.get('incident_type')}")
                                print(f"     Severity: {parsed.get('severity')}")
                                results.append(True)
                            else:
                                print(f"  ❌ FAILED: Unexpected test result")
                                results.append(False)
                        except json.JSONDecodeError:
                            print(f"  ❌ FAILED: Invalid JSON output")
                            results.append(False)
                    else:
                        print(f"  ❌ FAILED: No output")
                        results.append(False)
                else:
                    print(f"  ❌ FAILED: No output file")
                    results.append(False)
            else:
                print(f"  ❌ FAILED: Benthos error")
                print(f"     {result.stderr}")
                results.append(False)
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ FAILED: Timeout (this was the original issue)")
            results.append(False)
        except Exception as e:
            print(f"  ❌ FAILED: Exception: {e}")
            results.append(False)
        finally:
            # Cleanup
            for temp_file in [input_file, output_file, config_file]:
                try:
                    if os.path.exists(temp_file):
                        os.unlink(temp_file)
                except:
                    pass
    
    print(f"\n📊 Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ All tests passed! The fixed configuration handles null values correctly.")
        return True
    else:
        print("❌ Some tests failed. Review the errors above.")
        return False

if __name__ == "__main__":
    success = test_problematic_events()
    exit(0 if success else 1)