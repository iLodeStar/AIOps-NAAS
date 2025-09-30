#!/usr/bin/env python3
"""
Test script for Benthos v4.27.0 HTTP POST fix
Validates that enrichment.yaml and correlation.yaml use correct Benthos v4 syntax
"""

import subprocess
import sys
from pathlib import Path

def test_benthos_config(config_file: str) -> tuple[bool, str]:
    """
    Test a Benthos config file using the official Benthos lint command
    
    Args:
        config_file: Path to the Benthos YAML config file
        
    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            [
                'docker', 'run', '--rm',
                '-v', f'{config_file}:/config.yaml:ro',
                'jeffail/benthos:latest',
                'lint', '/config.yaml'
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "✅ Configuration is valid"
        else:
            return False, f"❌ Validation failed:\n{result.stdout}\n{result.stderr}"
            
    except subprocess.TimeoutExpired:
        return False, "❌ Validation timed out"
    except Exception as e:
        return False, f"❌ Error running validation: {str(e)}"


def check_http_post_syntax(config_file: Path) -> tuple[bool, list[str]]:
    """
    Check that the config file doesn't use the deprecated 'body:' parameter
    in HTTP POST requests
    
    Returns:
        Tuple of (valid: bool, issues: list[str])
    """
    issues = []
    
    try:
        content = config_file.read_text()
        lines = content.split('\n')
        
        in_http_block = False
        http_line = 0
        has_body_param = False
        
        for i, line in enumerate(lines, 1):
            # Check if we're entering an http processor block
            if '- http:' in line:
                in_http_block = True
                http_line = i
                has_body_param = False
                
            # Check if we exit the http block
            elif in_http_block and line and not line.startswith(' ' * 16):
                in_http_block = False
                
            # Check for deprecated body: parameter
            elif in_http_block and 'body:' in line:
                has_body_param = True
                issues.append(
                    f"Line {i}: Found deprecated 'body:' parameter in HTTP processor "
                    f"(started at line {http_line})"
                )
        
        return len(issues) == 0, issues
        
    except Exception as e:
        return False, [f"Error reading file: {str(e)}"]


def main():
    """Run all tests for the Benthos HTTP POST fix"""
    print("🚀 Testing Benthos v4.27.0 HTTP POST Fix")
    print("=" * 70)
    
    base_dir = Path(__file__).parent
    configs_to_test = [
        base_dir / "benthos" / "enrichment.yaml",
        base_dir / "benthos" / "correlation.yaml"
    ]
    
    all_passed = True
    
    for config_file in configs_to_test:
        print(f"\n📄 Testing: {config_file.name}")
        print("-" * 70)
        
        if not config_file.exists():
            print(f"❌ File not found: {config_file}")
            all_passed = False
            continue
        
        # Test 1: Check for deprecated body: syntax
        print("\n🔍 Test 1: Checking for deprecated 'body:' parameter...")
        syntax_valid, issues = check_http_post_syntax(config_file)
        
        if syntax_valid:
            print("✅ No deprecated 'body:' parameters found")
        else:
            print("❌ Found deprecated syntax:")
            for issue in issues:
                print(f"   {issue}")
            all_passed = False
        
        # Test 2: Validate with Benthos lint
        print("\n🔍 Test 2: Running Benthos lint validation...")
        lint_valid, output = test_benthos_config(str(config_file.absolute()))
        print(output)
        
        if not lint_valid:
            all_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 Test Summary")
    print("=" * 70)
    
    if all_passed:
        print("🎉 All tests passed!")
        print("\n✅ Fixes Applied:")
        print("   - Removed deprecated 'body:' parameter from HTTP processors")
        print("   - Added 'mapping' processor before HTTP POST to prepare request body")
        print("   - Updated Ollama integration in enrichment.yaml")
        print("   - Updated ClickHouse and Ollama integration in correlation.yaml")
        print("   - Simplified metrics configuration to match Benthos v4")
        print("\n📖 Technical Details:")
        print("   In Benthos v4, HTTP POST requests use the message content directly")
        print("   as the request body. Use a 'mapping' processor before the 'http'")
        print("   processor to prepare the desired POST payload.")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
