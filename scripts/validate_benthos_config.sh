#!/bin/bash
# Simple script to validate Benthos configuration syntax

echo "🔧 Benthos Configuration Validation"
echo "===================================="

# Check if benthos command is available (for syntax validation)
if command -v benthos &> /dev/null; then
    echo "✅ Benthos CLI found, validating configuration..."
    
    cd /home/runner/work/AIOps-NAAS/AIOps-NAAS
    
    # Validate main benthos configuration
    if benthos lint benthos/benthos.yaml; then
        echo "✅ benthos.yaml syntax is valid"
    else
        echo "❌ benthos.yaml has syntax errors"
        exit 1
    fi
    
    # Validate device registry integration
    if benthos lint benthos/device-registry-integration.yaml; then
        echo "✅ device-registry-integration.yaml syntax is valid"
    else
        echo "❌ device-registry-integration.yaml has syntax errors"
        exit 1
    fi
    
else
    echo "⚠️  Benthos CLI not found. Using basic YAML syntax check..."
    
    # Basic YAML syntax check using Python
    python3 -c "
import yaml
import sys

try:
    with open('benthos/benthos.yaml', 'r') as f:
        yaml.safe_load(f)
    print('✅ benthos.yaml is valid YAML')
    
    with open('benthos/device-registry-integration.yaml', 'r') as f:
        yaml.safe_load(f)
    print('✅ device-registry-integration.yaml is valid YAML')
    
except yaml.YAMLError as e:
    print(f'❌ YAML syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"
fi

echo ""
echo "✅ Benthos configuration validation completed"