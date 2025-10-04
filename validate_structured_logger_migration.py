#!/usr/bin/env python3
"""
Validation script for StructuredLogger migration
Verifies that all target services use StructuredLogger from aiops_core
"""

import sys
import os
from pathlib import Path

# Services that should be using StructuredLogger
TARGET_SERVICES = [
    'anomaly-detection',
    'incident-api', 
    'enrichment-service',
    'correlation-service',
    'llm-enricher'
]

def check_service_logging(service_name):
    """Check if a service uses StructuredLogger"""
    service_path = Path(f'services/{service_name}')
    
    if not service_path.exists():
        print(f"  ⚠️  Service directory not found: {service_path}")
        return False
    
    # Find Python files in the service
    py_files = list(service_path.glob('*.py'))
    
    has_structured_logger = False
    has_old_logger = False
    files_checked = []
    
    for py_file in py_files:
        if py_file.name.startswith('test_'):
            continue  # Skip test files
            
        content = py_file.read_text()
        files_checked.append(py_file.name)
        
        if 'StructuredLogger' in content:
            has_structured_logger = True
        
        # Check for old-style logger initialization
        if 'logging.getLogger(__name__)' in content:
            # Check if it's a fallback pattern (acceptable)
            if 'except ImportError' in content or 'V3_AVAILABLE' in content:
                # This is a fallback pattern, which is acceptable
                pass
            else:
                has_old_logger = True
    
    return has_structured_logger, has_old_logger, files_checked

def main():
    print("=" * 70)
    print("StructuredLogger Migration Validation")
    print("=" * 70)
    print()
    
    all_passed = True
    
    for service in TARGET_SERVICES:
        print(f"📦 Checking {service}...")
        
        has_structured, has_old, files = check_service_logging(service)
        
        if has_structured:
            print(f"  ✅ Uses StructuredLogger")
        else:
            print(f"  ❌ Does NOT use StructuredLogger")
            all_passed = False
        
        if has_old:
            print(f"  ⚠️  Still has old logging.getLogger (without fallback)")
            all_passed = False
        
        if files:
            print(f"  📄 Files checked: {', '.join(files[:3])}{' ...' if len(files) > 3 else ''}")
        
        print()
    
    print("=" * 70)
    if all_passed:
        print("✅ All target services successfully migrated to StructuredLogger!")
        return 0
    else:
        print("❌ Some services still need migration")
        return 1

if __name__ == '__main__':
    sys.exit(main())
