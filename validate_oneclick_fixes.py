#!/usr/bin/env python3
"""
Validation script for one-click debugging fixes
Tests the configuration and API endpoint fixes without requiring running services
"""

import yaml
import json
from pathlib import Path

def validate_docker_compose_fixes():
    """Validate docker-compose.yml fixes"""
    print("🔍 Validating docker-compose.yml fixes...")
    
    compose_file = Path("docker-compose.yml")
    if not compose_file.exists():
        print("   ❌ docker-compose.yml not found")
        return False
    
    with open(compose_file, 'r') as f:
        compose_data = yaml.safe_load(f)
    
    # Check incident-api health check port
    incident_api = compose_data.get('services', {}).get('incident-api', {})
    health_check = incident_api.get('healthcheck', {})
    test_command = health_check.get('test', [])
    
    if any('http://localhost:9081/health' in cmd for cmd in test_command):
        print("   ✅ Incident API health check uses correct internal port 9081")
    else:
        print("   ❌ Incident API health check port not fixed")
        print(f"      Found: {test_command}")
        return False
    
    # Verify port mapping is still correct
    ports = incident_api.get('ports', [])
    if '9081:9081' in ports:
        print("   ✅ Incident API external port mapping (9081:9081) maintained")
    elif '9081:8081' in ports:
        print("   ✅ Incident API external port mapping (9081:8081) maintained")
    else:
        print(f"   ⚠️  Unexpected port mapping: {ports}")
    
    return True

def validate_debugging_script_fixes():
    """Validate one-click debugging script fixes"""
    print("\n🔍 Validating one-click debugging script fixes...")
    
    script_file = Path("scripts/one_click_incident_debugging.py")
    if not script_file.exists():
        print("   ❌ One-click debugging script not found")
        return False
    
    with open(script_file, 'r') as f:
        content = f.read()
    
    # Check device registration endpoint
    if '/devices/register' in content and "'http://localhost:8081/devices/register'" in content:
        print("   ✅ Device registration endpoint updated to /devices/register")
    else:
        print("   ❌ Device registration endpoint not updated")
        return False
    
    # Check ip_address field in payload
    if "'ip_address': '192.168.1.100'" in content:
        print("   ✅ Device registration payload includes required ip_address field")
    else:
        print("   ❌ Device registration payload missing ip_address field")
        return False
    
    # Check anomaly detection service in health checks
    if "'Anomaly Detection', 'http://localhost:8080/health'" in content:
        print("   ✅ Anomaly Detection service added to health checks")
    else:
        print("   ❌ Anomaly Detection service not added to health checks")
        return False
    
    # Check reproduction steps updated
    if '/devices/register' in content and '"ip_address":"192.168.1.100"' in content:
        print("   ✅ Reproduction steps updated with correct endpoint and payload")
    else:
        print("   ❌ Reproduction steps not fully updated")
        return False
    
    return True

def validate_endpoint_consistency():
    """Validate endpoint consistency across services"""
    print("\n🔍 Validating endpoint consistency...")
    
    # Check incident-api service port
    incident_api_file = Path("services/incident-api/incident_api.py")
    if incident_api_file.exists():
        with open(incident_api_file, 'r') as f:
            content = f.read()
        
        if 'port=9081' in content:
            print("   ✅ Incident API runs on port 9081 internally")
        else:
            print("   ❌ Incident API port configuration not found or incorrect")
            return False
    
    # Check device registry service port  
    device_reg_file = Path("services/device-registry/app.py")
    if device_reg_file.exists():
        with open(device_reg_file, 'r') as f:
            content = f.read()
        
        if 'port=8080' in content:
            print("   ✅ Device Registry runs on port 8080 internally")
        else:
            print("   ❌ Device Registry port configuration not found or incorrect")
            return False
    
    return True

def main():
    """Run all validations"""
    print("🚀 VALIDATING ONE-CLICK DEBUGGING FIXES")
    print("=" * 50)
    
    all_passed = True
    
    all_passed &= validate_docker_compose_fixes()
    all_passed &= validate_debugging_script_fixes() 
    all_passed &= validate_endpoint_consistency()
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL VALIDATIONS PASSED")
        print("   The one-click debugging fixes are correctly implemented")
        print("   Key fixes:")
        print("   - Incident API health check port corrected (9081)")
        print("   - Device registration endpoint updated (/devices/register)")
        print("   - Required ip_address field added to device payloads")
        print("   - Anomaly Detection service added to health checks")
        print("   - Reproduction steps updated with correct API calls")
    else:
        print("❌ SOME VALIDATIONS FAILED")
        print("   Please review the issues above")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())