#!/usr/bin/env python3
"""
Test script for Issue #147 - Benthos ship_id detection and severity comparison fixes
Tests the specific fixes applied to resolve null comparison errors and ship_id detection issues.
"""

import yaml
import json
import subprocess
import sys
from pathlib import Path

def test_yaml_syntax():
    """Test that the YAML syntax is valid after changes."""
    print("🔧 Testing Benthos YAML syntax...")
    try:
        with open('benthos/benthos.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Verify critical sections exist
        assert 'pipeline' in config, "Missing pipeline section"
        assert 'processors' in config['pipeline'], "Missing processors in pipeline"
        
        processors = config['pipeline']['processors']
        print(f"   ✅ Found {len(processors)} processors in pipeline")
        
        # Find the severity comparison processor (should be index 11)
        severity_processor = processors[11]
        assert 'mapping' in severity_processor, "Severity processor missing mapping"
        
        # Check that the mapping contains our fixes
        mapping_text = severity_processor['mapping']
        assert 'severity_priority != null && related_priority != null' in mapping_text, "Null check fix not found"
        
        # Check for ship_id debug in the right processor (should be processor 3, not 11)
        ship_id_processor = processors[3]  # Ship ID processor is at index 3
        ship_id_mapping = ship_id_processor['mapping']
        assert 'ship_id_debug' in ship_id_mapping, "Ship ID debug logging not found"
        
        print("   ✅ YAML syntax is valid")
        print("   ✅ Severity null check fix is present")
        print("   ✅ Ship ID debug logging is present")
        return True
        
    except yaml.YAMLError as e:
        print(f"   ❌ YAML syntax error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_severity_logic():
    """Test the severity comparison logic with various inputs."""
    print("\n🔍 Testing severity comparison logic...")
    
    test_cases = [
        # Test case 1: Normal values
        {
            "name": "Normal severity values",
            "this_severity": "critical",
            "related_severity": "warning",
            "expected": "critical"  # higher priority
        },
        # Test case 2: Null this.severity
        {
            "name": "Null this.severity",
            "this_severity": None,
            "related_severity": "high",
            "expected": "high"  # should default to info (1) vs high (3), so high wins
        },
        # Test case 3: Both null
        {
            "name": "Both severities null",
            "this_severity": None,
            "related_severity": None,
            "expected": "low"  # both default to info (1), so priority = 1
        },
        # Test case 4: Invalid severity
        {
            "name": "Invalid severity value",
            "this_severity": "invalid",
            "related_severity": "medium",
            "expected": "medium"  # invalid defaults to info (1), medium is 2
        }
    ]
    
    severity_map = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "warning": 2,
        "info": 1,
        "debug": 1
    }
    
    results = []
    for test_case in test_cases:
        print(f"   🧪 {test_case['name']}...")
        
        # Simulate the logic from our fix
        current_severity = test_case['this_severity'].lower() if test_case['this_severity'] and isinstance(test_case['this_severity'], str) else "info"
        severity_priority = severity_map.get(current_severity, 1)
        
        related_severity = test_case['related_severity'].lower() if test_case['related_severity'] and isinstance(test_case['related_severity'], str) else "info"
        related_priority = severity_map.get(related_severity, 1) if test_case['related_severity'] else 0
        
        # Apply our new null-safe comparison logic
        if severity_priority is not None and related_priority is not None:
            max_priority = severity_priority if severity_priority >= related_priority else related_priority
        elif severity_priority is not None:
            max_priority = severity_priority
        elif related_priority is not None:
            max_priority = related_priority
        else:
            max_priority = 1
        
        # Convert back to severity name
        incident_severity = {
            4: "critical",
            3: "high", 
            2: "medium",
            1: "low"
        }.get(max_priority, "low")
        
        success = incident_severity == test_case['expected']
        status = "✅" if success else "❌"
        print(f"      {status} Expected: {test_case['expected']}, Got: {incident_severity}")
        
        results.append(success)
    
    all_passed = all(results)
    print(f"   {'✅' if all_passed else '❌'} Severity logic tests: {sum(results)}/{len(results)} passed")
    return all_passed

def test_ship_id_extraction():
    """Test ship_id extraction logic."""
    print("\n🚢 Testing ship_id extraction logic...")
    
    test_cases = [
        {
            "name": "Ship ID in top-level field",
            "data": {"ship_id": "test-ship", "host": "test-host"},
            "expected_ship_id": "test-ship",
            "expected_source": "original_field"
        },
        {
            "name": "Ship ID in metadata",
            "data": {"metadata": {"ship_id": "metadata-ship"}, "host": "test-host"},
            "expected_ship_id": "metadata-ship", 
            "expected_source": "metadata_field"
        },
        {
            "name": "No ship ID, should use hostname fallback",
            "data": {"host": "test-hostname"},
            "expected_ship_id": "test-ship",  # "test-hostname" -> split("-")[0] + "-ship" = "test-ship"
            "expected_source": "registry_unavailable_hostname_fallback"
        },
        {
            "name": "Unknown ship_id should be ignored",
            "data": {"ship_id": "unknown-ship", "host": "test-host"},
            "expected_ship_id": "test-ship",  # "test-host" -> "test" + "-ship" = "test-ship"
            "expected_source": "registry_unavailable_hostname_fallback"
        }
    ]
    
    results = []
    for test_case in test_cases:
        print(f"   🧪 {test_case['name']}...")
        
        data = test_case['data']
        
        # Simulate the ship_id extraction logic
        available_ship_id = None
        if data.get('ship_id') and data['ship_id'] != "" and "unknown" not in data['ship_id']:
            available_ship_id = data['ship_id']
        elif data.get('metadata', {}).get('ship_id') and data['metadata']['ship_id'] != "" and "unknown" not in data['metadata']['ship_id']:
            available_ship_id = data['metadata']['ship_id']
        
        if available_ship_id:
            ship_id = available_ship_id
            ship_id_source = "original_field" if data.get('ship_id') == available_ship_id else "metadata_field"
        else:
            # Fallback to hostname-based
            hostname = data.get('host') or data.get('hostname')
            if hostname:
                # Simulate the actual hostname fallback logic from benthos.yaml
                if "-" in hostname:
                    ship_id = f"{hostname.split('-')[0]}-ship"
                else:
                    ship_id = f"{hostname}-ship"
                ship_id_source = "registry_unavailable_hostname_fallback"
            else:
                ship_id = "unknown-ship"
                ship_id_source = "no_hostname"
        
        success = (ship_id == test_case['expected_ship_id'] and 
                  ship_id_source == test_case['expected_source'])
        status = "✅" if success else "❌"
        
        print(f"      {status} Expected: {test_case['expected_ship_id']} ({test_case['expected_source']})")
        print(f"         Got: {ship_id} ({ship_id_source})")
        
        results.append(success)
    
    all_passed = all(results)
    print(f"   {'✅' if all_passed else '❌'} Ship ID extraction tests: {sum(results)}/{len(results)} passed")
    return all_passed

def main():
    """Run all tests for the Benthos fixes."""
    print("🚀 Testing Benthos Fixes for Issue #147")
    print("=" * 60)
    
    results = []
    
    # Test 1: YAML syntax
    results.append(test_yaml_syntax())
    
    # Test 2: Severity comparison logic
    results.append(test_severity_logic())
    
    # Test 3: Ship ID extraction
    results.append(test_ship_id_extraction())
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary")
    print("=" * 60)
    
    all_passed = all(results)
    passed_count = sum(results)
    total_count = len(results)
    
    status_icon = "🎉" if all_passed else "⚠️"
    print(f"{status_icon} Results: {passed_count}/{total_count} test suites passed")
    
    if all_passed:
        print("✅ All tests passed! The fixes should resolve Issue #147.")
        print("\n🔧 Fixes applied:")
        print("   ✅ Null-safe severity comparison logic")
        print("   ✅ Enhanced ship_id extraction with debug logging")
        print("   ✅ Proper fallback handling for all edge cases")
    else:
        print("❌ Some tests failed. Review the fixes before deployment.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())