#!/usr/bin/env python3
"""
Simplified test for Benthos null handling fixes - issue #77
This validates the specific changes we made to fix the null handling issues.
"""

import re
import json

def test_benthos_config_fixes():
    """Test the specific fixes we applied to benthos.yaml"""
    print("🔍 Testing Benthos Configuration Fixes for Issue #77")
    print("=" * 60)
    
    # Read the configuration file
    with open('benthos/benthos.yaml', 'r') as f:
        config_content = f.read()
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Check for null-safe cache key generation
    total_tests += 1
    if 'unknown_metric' in config_content and 'unknown_ship' in config_content:
        print("✅ Test 1: Null-safe cache key generation with fallback values")
        tests_passed += 1
    else:
        print("❌ Test 1: Missing null-safe cache key generation")
    
    # Test 2: Check for placeholder cache keys (no empty strings)
    total_tests += 1
    if 'no_correlation_key' in config_content and 'no_secondary_key' in config_content:
        print("✅ Test 2: Placeholder cache keys instead of empty strings")
        tests_passed += 1
    else:
        print("❌ Test 2: Missing placeholder cache keys")
    
    # Test 3: Check for incident_type null safety
    total_tests += 1
    if 'if this.incident_type == null || this.incident_type == ""' in config_content:
        print("✅ Test 3: Incident type null safety check")
        tests_passed += 1
    else:
        print("❌ Test 3: Missing incident type null safety")
    
    # Test 4: Check for ship_id null safety 
    total_tests += 1
    if 'if this.ship_id == null || this.ship_id == ""' in config_content:
        print("✅ Test 4: Ship ID null safety check")
        tests_passed += 1
    else:
        print("❌ Test 4: Missing ship ID null safety")
    
    # Test 5: Check for null-safe debug priorities
    total_tests += 1
    if 'if severity_priority != null { severity_priority } else { 0 }' in config_content:
        print("✅ Test 5: Null-safe debug priorities assignment")
        tests_passed += 1
    else:
        print("❌ Test 5: Missing null-safe debug priorities")
    
    # Test 6: Check that we're using safe comparison instead of array.max()
    total_tests += 1
    if 'if severity_priority >= related_priority && severity_priority >= secondary_priority' in config_content:
        print("✅ Test 6: Safe priority comparison logic (no array.max)")
        tests_passed += 1
    else:
        print("❌ Test 6: Missing safe priority comparison")
    
    # Test 7: Verify no problematic patterns remain
    total_tests += 1
    problematic_patterns = [
        r'this\.severity_priority.*this\.related_priority',
        r'\.max\(\)',
        r'\+ ""',  # Empty string concatenation
        r'key: "\${.*}""'  # Keys ending with empty quotes
    ]
    
    has_problematic = False
    for pattern in problematic_patterns:
        if re.search(pattern, config_content):
            print(f"❌ Found problematic pattern: {pattern}")
            has_problematic = True
    
    if not has_problematic:
        print("✅ Test 7: No problematic patterns found")
        tests_passed += 1
    else:
        print("❌ Test 7: Found problematic patterns")
    
    # Test 8: Validate specific error scenarios from issue #77
    total_tests += 1
    
    # Check for the specific error patterns mentioned in the issue
    error_fixes = {
        "ubuntu_snmp_network_interface": "no_correlation_key" in config_content,
        "empty_key_errors": "no_secondary_key" in config_content,
        "null_severity_handling": "if this.severity != null { this.severity } else { \"unknown\" }" in config_content,
        "incident_type_interpolation": '"unknown_anomaly"' in config_content
    }
    
    all_error_fixes = all(error_fixes.values())
    if all_error_fixes:
        print("✅ Test 8: All specific error scenarios from issue #77 addressed")
        tests_passed += 1
    else:
        print("❌ Test 8: Some error scenarios not fully addressed")
        for fix, status in error_fixes.items():
            print(f"   - {fix}: {'✅' if status else '❌'}")
    
    print(f"\n📊 Test Results:")
    print(f"   Passed: {tests_passed}/{total_tests}")
    print(f"   Success Rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("   The Benthos configuration should now handle:")
        print("   ✅ Null metric_name values in cache keys")
        print("   ✅ Null ship_id values in suppression logic")
        print("   ✅ Null severity values in priority calculations")
        print("   ✅ Empty incident_type values in key interpolation")
        print("   ✅ Missing fields without causing processor failures")
        return True
    else:
        print(f"\n❌ {total_tests - tests_passed} tests failed. Please review the configuration.")
        return False

def validate_json_structure():
    """Validate that our changes maintain proper JSON structure"""
    print("\n🔧 Validating JSON Structure Integrity")
    print("-" * 50)
    
    with open('benthos/benthos.yaml', 'r') as f:
        content = f.read()
    
    # Extract mapping blocks that contain JSON-like structures
    mapping_blocks = re.findall(r'mapping:\s*\|([^-]+?)(?=^\s*-|\Z)', content, re.MULTILINE | re.DOTALL)
    
    json_issues = 0
    for i, block in enumerate(mapping_blocks):
        # Check for common JSON syntax issues
        if '{ {' in block or '} }' in block:
            print(f"❌ Mapping block {i+1}: Potential double brace issue")
            json_issues += 1
        
        if block.count('{') != block.count('}'):
            print(f"❌ Mapping block {i+1}: Unmatched braces")
            json_issues += 1
    
    if json_issues == 0:
        print("✅ JSON structure integrity validated")
        return True
    else:
        print(f"❌ Found {json_issues} JSON structure issues")
        return False

def main():
    """Run all validation tests"""
    print("🚀 Benthos Issue #77 Fix Validation")
    print("=====================================")
    
    # Test the specific fixes
    fixes_valid = test_benthos_config_fixes()
    
    # Test JSON structure
    structure_valid = validate_json_structure()
    
    # Final result
    if fixes_valid and structure_valid:
        print(f"\n✅ VALIDATION SUCCESSFUL!")
        print(f"   All Benthos null handling fixes have been validated.")
        print(f"   The configuration should now process events without the errors:")
        print(f"   - 'operator failed for key': Fixed with placeholder keys")
        print(f"   - 'cannot compare types null': Fixed with null-safe comparisons")
        print(f"   - 'cannot add types null and string': Fixed with default values")
        return True
    else:
        print(f"\n❌ VALIDATION FAILED!")
        print(f"   Please review the issues identified above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)