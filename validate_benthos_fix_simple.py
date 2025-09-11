#!/usr/bin/env python3
"""
Simple test to validate Benthos configuration syntax after null handling fixes.
"""

import subprocess
import sys
from pathlib import Path

def validate_benthos_config():
    """Validate the Benthos configuration syntax"""
    config_path = Path(__file__).parent / "benthos" / "benthos.yaml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        return False
    
    try:
        result = subprocess.run([
            'docker', 'run', '--rm',
            '-v', f'{config_path.absolute()}:/config.yaml:ro',
            'jeffail/benthos:latest', 
            '-c', '/config.yaml',
            '--lint'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Configuration syntax validation passed")
            print("✅ Configuration linting passed")
            return True
        else:
            print("❌ Configuration validation/linting failed:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Configuration validation timed out")
        return False
    except Exception as e:
        print(f"❌ Configuration validation error: {e}")
        return False

def analyze_configuration():
    """Analyze the configuration for our specific fixes"""
    config_path = Path(__file__).parent / "benthos" / "benthos.yaml"
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            
        fixes_found = []
        
        # Check for improved cache key generation
        if 'if json("ship_id") != null && json("ship_id") != ""' in content:
            fixes_found.append("✅ Enhanced null checking for ship_id in cache keys")
        
        # Check for improved severity handling
        if 'if this.severity != null && this.severity != ""' in content:
            fixes_found.append("✅ Enhanced null checking for severity fields")
            
        # Check for improved incident_type handling  
        if 'if json("incident_type") != null && json("incident_type") != ""' in content:
            fixes_found.append("✅ Enhanced null checking for incident_type in suppression cache")
            
        # Check for improved event_source handling
        if 'if json("event_source") != null && json("event_source") != ""' in content:
            fixes_found.append("✅ Enhanced null checking for event_source in cache keys")
            
        # Check for improved metric_name handling
        if 'if json("metric_name") != null && json("metric_name") != ""' in content:
            fixes_found.append("✅ Enhanced null checking for metric_name in cache keys")
        
        if fixes_found:
            print("\n🔧 Null Handling Fixes Applied:")
            for fix in fixes_found:
                print(f"  {fix}")
            return True
        else:
            print("\n❌ Expected null handling fixes not found in configuration")
            return False
            
    except Exception as e:
        print(f"❌ Error analyzing configuration: {e}")
        return False

def main():
    print("🚀 Benthos Issue #95 Fix Validation")
    print("=" * 50)
    
    # Validate configuration syntax
    config_valid = validate_benthos_config()
    
    # Analyze configuration for fixes
    fixes_applied = analyze_configuration()
    
    print("\n📊 Validation Results:")
    print(f"  Configuration Valid: {'✅ Yes' if config_valid else '❌ No'}")
    print(f"  Fixes Applied: {'✅ Yes' if fixes_applied else '❌ No'}")
    
    if config_valid and fixes_applied:
        print("\n🎉 Success! The configuration is valid and null handling fixes are in place.")
        print("\nThe following issues should now be resolved:")
        print("  • Key does not exist errors in cache operations")  
        print("  • Null comparison errors in severity priority calculations")
        print("  • Null field handling in cache key generation")
        return True
    else:
        print("\n⚠️ Issues found. Review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)