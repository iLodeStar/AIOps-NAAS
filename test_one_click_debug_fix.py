#!/usr/bin/env python3
"""
Test script to validate the one-click incident debugging tool fixes
This test ensures the port inconsistency is resolved and script functions correctly
"""

import sys
import os
import subprocess
import tempfile
import re
from pathlib import Path

def test_script_help():
    """Test that the script can show help without errors"""
    print("🧪 Testing script help functionality...")
    
    result = subprocess.run([
        sys.executable, 
        'scripts/one_click_incident_debugging.py', 
        '--help'
    ], capture_output=True, text=True, cwd='/home/runner/work/AIOps-NAAS/AIOps-NAAS')
    
    assert result.returncode == 0, f"Script help failed: {result.stderr}"
    assert "--deep-analysis" in result.stdout, "Help should mention --deep-analysis"
    assert "--generate-issue-report" in result.stdout, "Help should mention --generate-issue-report"
    print("  ✅ Script help works correctly")

def test_port_consistency():
    """Test that all device registry ports are consistent (8081)"""
    print("🧪 Testing port consistency...")
    
    script_path = Path('/home/runner/work/AIOps-NAAS/AIOps-NAAS/scripts/one_click_incident_debugging.py')
    script_content = script_path.read_text()
    
    # Check that there are no references to the old incorrect port 8091
    port_8091_matches = re.findall(r'localhost:8091', script_content)
    assert len(port_8091_matches) == 0, f"Found {len(port_8091_matches)} references to incorrect port 8091"
    
    # Check that device registry references use correct port 8081
    device_registry_matches = re.findall(r'localhost:8081[^0-9]', script_content)
    assert len(device_registry_matches) > 0, "Should have references to device registry port 8081"
    
    print(f"  ✅ Found {len(device_registry_matches)} correct device registry port references")
    print("  ✅ No incorrect port 8091 references found")

def test_report_generation():
    """Test that the script can generate a report without errors"""
    print("🧪 Testing report generation (services down scenario)...")
    
    # Run the script in report generation mode
    result = subprocess.run([
        sys.executable, 
        'scripts/one_click_incident_debugging.py', 
        '--generate-issue-report'
    ], capture_output=True, text=True, cwd='/home/runner/work/AIOps-NAAS/AIOps-NAAS')
    
    # Script should complete successfully even if services are down
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    
    # Check output contains expected sections
    output = result.stdout
    assert "ONE-CLICK INCIDENT DEBUGGING SESSION" in output, "Missing session header"
    assert "SERVICE HEALTH CHECKS" in output, "Missing health checks section"
    assert "GENERATE TRACKABLE TEST DATA" in output, "Missing test data section"
    assert "GitHub issue report saved:" in output, "Missing report save confirmation"
    
    print("  ✅ Script generates reports without errors")
    print("  ✅ All expected output sections present")

def test_report_file_consistency():
    """Test that generated report files have consistent port numbers"""
    print("🧪 Testing generated report file port consistency...")
    
    # Find the latest generated report
    report_files = list(Path('/home/runner/work/AIOps-NAAS/AIOps-NAAS').glob('INCIDENT_DATA_ISSUE_REPORT_*.md'))
    if not report_files:
        print("  ⚠️  No report files found to test")
        return
    
    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
    report_content = latest_report.read_text()
    
    # Check for port consistency in the generated report
    port_8091_in_report = re.findall(r'localhost:8091', report_content)
    assert len(port_8091_in_report) == 0, f"Found {len(port_8091_in_report)} incorrect port 8091 references in report"
    
    port_8081_in_report = re.findall(r'localhost:8081', report_content)
    assert len(port_8081_in_report) > 0, "Should have device registry port 8081 references in report"
    
    print(f"  ✅ Report file has {len(port_8081_in_report)} correct port references")
    print("  ✅ No incorrect port references in generated report")

def test_expected_structure():
    """Test that the script has the expected functions and classes"""
    print("🧪 Testing script structure...")
    
    script_path = Path('/home/runner/work/AIOps-NAAS/AIOps-NAAS/scripts/one_click_incident_debugging.py')
    script_content = script_path.read_text()
    
    # Check for expected classes and methods
    expected_elements = [
        'class OneClickIncidentDebugger',
        'def _perform_health_checks',
        'def _generate_test_data',
        'def _inject_test_data',
        'def _track_data_through_services',
        'def _identify_data_mismatches',
        'def _generate_github_issue'
    ]
    
    for element in expected_elements:
        assert element in script_content, f"Missing expected element: {element}"
    
    print("  ✅ All expected classes and methods present")

def main():
    """Run all tests"""
    print("🚀 Running One-Click Debug Script Fix Tests")
    print("=" * 50)
    
    os.chdir('/home/runner/work/AIOps-NAAS/AIOps-NAAS')
    
    try:
        test_script_help()
        test_port_consistency()
        test_expected_structure()
        test_report_generation()
        test_report_file_consistency()
        
        print("\n✅ ALL TESTS PASSED!")
        print("The one-click debug script port inconsistency has been successfully fixed.")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n💥 UNEXPECTED ERROR: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())