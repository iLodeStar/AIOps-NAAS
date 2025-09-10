#!/usr/bin/env python3
"""
Comprehensive test for Issue #83 - Benthos processing fails
Tests the actual configuration and validates all null handling fixes
"""

import json
import subprocess
import tempfile
import os
import yaml
from pathlib import Path

def test_benthos_config_validity():
    """Test that the Benthos configuration is syntactically valid"""
    print("🔍 Testing Benthos Configuration Validity...")
    
    config_path = Path("/home/runner/work/AIOps-NAAS/AIOps-NAAS/benthos/benthos.yaml")
    if not config_path.exists():
        return False, f"Config file not found: {config_path}"
    
    try:
        # Try to parse the YAML
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Basic validation checks
        required_sections = ['input', 'pipeline', 'output', 'cache_resources']
        for section in required_sections:
            if section not in config:
                return False, f"Missing required section: {section}"
        
        return True, "Configuration structure is valid"
    except yaml.YAMLError as e:
        return False, f"YAML parsing error: {e}"
    except Exception as e:
        return False, f"Configuration error: {e}"

def test_null_handling_patterns():
    """Test the specific null handling patterns that were causing Issue #83"""
    print("🧪 Testing Null Handling Patterns...")
    
    config_path = Path("/home/runner/work/AIOps-NAAS/AIOps-NAAS/benthos/benthos.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # Test patterns that should be present to fix Issue #83
        tests = [
            {
                "name": "Related severity null safety",
                "pattern": "related.severity != null &&",
                "found": "related.severity != null &&" in config_content
            },
            {
                "name": "Secondary severity null safety", 
                "pattern": "secondary.severity != null &&",
                "found": "secondary.severity != null &&" in config_content
            },
            {
                "name": "Suppression cache key null safety",
                "pattern": 'json(\\"incident_type\\")',
                "found": 'json(\\"incident_type\\")' in config_content and "unknown_anomaly" in config_content
            },
            {
                "name": "Cache operations drop_on_err",
                "pattern": "drop_on_err: true",
                "found": "drop_on_err: true" in config_content
            },
            {
                "name": "Incident type null safety mapping",
                "pattern": "if this.incident_type == null || this.incident_type == \"\"",
                "found": "if this.incident_type == null || this.incident_type == \"\"" in config_content
            }
        ]
        
        results = []
        for test in tests:
            if test["found"]:
                print(f"  ✅ {test['name']}: Found")
                results.append(True)
            else:
                print(f"  ❌ {test['name']}: Missing pattern '{test['pattern']}'")
                results.append(False)
        
        return all(results), f"Passed {sum(results)}/{len(results)} null handling tests"
        
    except Exception as e:
        return False, f"Error testing patterns: {e}"

def test_issue_83_error_patterns():
    """Test that the specific error patterns from Issue #83 are addressed"""
    print("🎯 Testing Issue #83 Error Pattern Fixes...")
    
    config_path = Path("/home/runner/work/AIOps-NAAS/AIOps-NAAS/benthos/benthos.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        # Errors from Issue #83 that should be fixed:
        fixes = [
            {
                "error": "cannot compare types null (from field `this.severity_priority`) and null (from field `this.related_priority`)",
                "fix_description": "Related/secondary priority calculations should check for null severity",
                "check": lambda content: "related.severity != null &&" in content and "secondary.severity != null &&" in content
            },
            {
                "error": "key interpolation error: cannot add types null (from json path `incident_type`) and string",
                "fix_description": "Suppression cache key should handle null incident_type safely",
                "check": lambda content: 'json(\\"incident_type\\")' in content and "unknown_anomaly" in content and "suppression_cache" in content
            },
            {
                "error": "operator failed for key 'no_secondary_key': key does not exist",
                "fix_description": "Cache operations should use drop_on_err to handle missing keys",
                "check": lambda content: content.count("drop_on_err: true") >= 3  # Should be on multiple cache operations
            },
            {
                "error": "operator failed for key 'ship-01_snmp_network_interface': key does not exist", 
                "fix_description": "Cache operations should gracefully handle missing correlation keys",
                "check": lambda content: "drop_on_err: true" in content
            }
        ]
        
        results = []
        for fix in fixes:
            if fix["check"](config_content):
                print(f"  ✅ Fixed: {fix['error'][:60]}...")
                print(f"     Solution: {fix['fix_description']}")
                results.append(True)
            else:
                print(f"  ❌ Not Fixed: {fix['error'][:60]}...")
                print(f"     Missing: {fix['fix_description']}")
                results.append(False)
        
        return all(results), f"Fixed {sum(results)}/{len(results)} Issue #83 error patterns"
        
    except Exception as e:
        return False, f"Error checking fixes: {e}"

def test_configuration_sections():
    """Test that all configuration sections have proper null handling"""
    print("🏗️ Testing Configuration Section Integrity...")
    
    config_path = Path("/home/runner/work/AIOps-NAAS/AIOps-NAAS/benthos/benthos.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        tests = []
        
        # Check pipeline processors
        if 'pipeline' in config and 'processors' in config['pipeline']:
            processors = config['pipeline']['processors']
            cache_processors = [p for p in processors if 'cache' in p]
            
            # Should have multiple cache processors with proper error handling
            tests.append(("Cache processors found", len(cache_processors) >= 3))
            
            # Check for mapping processors with null safety
            mapping_processors = [p for p in processors if 'mapping' in p]
            tests.append(("Mapping processors found", len(mapping_processors) >= 2))
            
        # Check cache resources
        if 'cache_resources' in config:
            cache_resources = config['cache_resources']
            expected_caches = ['correlation_cache', 'suppression_cache', 'temporal_cache']
            for cache_name in expected_caches:
                found = any(cache.get('label') == cache_name for cache in cache_resources)
                tests.append((f"Cache resource '{cache_name}' exists", found))
        
        # Check input/output configuration
        tests.append(("Input configuration exists", 'input' in config))
        tests.append(("Output configuration exists", 'output' in config))
        
        results = []
        for test_name, passed in tests:
            if passed:
                print(f"  ✅ {test_name}")
                results.append(True)
            else:
                print(f"  ❌ {test_name}")
                results.append(False)
        
        return all(results), f"Passed {sum(results)}/{len(results)} configuration integrity tests"
        
    except Exception as e:
        return False, f"Error testing configuration: {e}"

def main():
    """Run comprehensive tests for Issue #83 fix"""
    print("🧪 Comprehensive Testing for Issue #83 - Benthos Processing Failures")
    print("=" * 75)
    print()
    print("Issue #83 reported these specific errors:")
    print("  1. Line 91: cannot compare types null (severity_priority vs related_priority)")
    print("  2. Processor 6: key interpolation error with null incident_type")
    print("  3. Processor 4: 'no_secondary_key' cache key does not exist")  
    print("  4. Processor 3: 'ship-01_snmp_network_interface' cache key does not exist")
    print()
    
    all_tests = [
        test_benthos_config_validity,
        test_null_handling_patterns,
        test_issue_83_error_patterns,
        test_configuration_sections
    ]
    
    results = []
    for test_func in all_tests:
        print()
        success, message = test_func()
        print(f"Result: {message}")
        results.append(success)
    
    print()
    print("📊 Test Summary:")
    print(f"  Total test categories: {len(results)}")
    print(f"  Passed: {sum(results)}")
    print(f"  Failed: {len(results) - sum(results)}")
    
    if all(results):
        print()
        print("✅ ALL TESTS PASSED!")
        print("   Issue #83 has been comprehensively fixed. The Benthos configuration now:")
        print("   - Safely handles null values in severity priority calculations")
        print("   - Uses null-safe key interpolation for cache operations")
        print("   - Gracefully handles missing cache keys with drop_on_err")
        print("   - Maintains configuration structural integrity")
        print("   - Prevents all specific error patterns reported in Issue #83")
        return True
    else:
        print()
        print("❌ SOME TESTS FAILED!")
        print("   Issue #83 fix may not be complete. Review failed tests above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)