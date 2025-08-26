#!/bin/bash
# Test script to validate OLLAMA default model configuration implementation
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

echo "=== OLLAMA Default Model Configuration Test ==="
echo

cd "$ROOT_DIR"

# Test 1: Environment variables
echo "✓ Test 1: Environment Configuration"
if [[ -f .env.example ]]; then
    if grep -q "OLLAMA_DEFAULT_MODEL=mistral" .env.example && grep -q "OLLAMA_AUTO_PULL=true" .env.example; then
        echo "  ✅ Environment variables present in .env.example"
    else
        echo "  ❌ Environment variables missing in .env.example"
        exit 1
    fi
else
    echo "  ❌ .env.example not found"
    exit 1
fi
echo

# Test 2: Bootstrap script exists and is executable
echo "✓ Test 2: Bootstrap Script"
if [[ -x scripts/ollama_bootstrap.sh ]]; then
    echo "  ✅ scripts/ollama_bootstrap.sh is executable"
else
    echo "  ❌ scripts/ollama_bootstrap.sh not found or not executable"
    exit 1
fi

# Test 3: Bootstrap script help
echo "  Testing bootstrap script help..."
if scripts/ollama_bootstrap.sh --help | grep -q "Specify model to pull"; then
    echo "  ✅ Bootstrap script help works correctly"
else
    echo "  ❌ Bootstrap script help failed"
    exit 1
fi
echo

# Test 4: Docker compose configuration
echo "✓ Test 3: Docker Compose Configuration"
cp .env.example .env
if docker compose config | grep -q "OLLAMA_DEFAULT_MODEL"; then
    echo "  ✅ Docker compose includes OLLAMA environment variables"
else
    echo "  ❌ Docker compose missing OLLAMA environment variables"
    exit 1
fi
echo

# Test 5: Main script help includes new option
echo "✓ Test 4: Main Script Integration"
if bash scripts/aiops.sh --help | grep -q "ollama-model"; then
    echo "  ✅ aiops.sh includes --ollama-model option"
else
    echo "  ❌ aiops.sh missing --ollama-model option"
    exit 1
fi
echo

# Test 6: Command-line model override
echo "✓ Test 5: Command-Line Model Override"
# Reset .env
cp .env.example .env
# Test the override (without starting services)
if echo "n" | timeout 10 bash scripts/aiops.sh up --minimal --ollama-model phi 2>/dev/null || true; then
    if grep -q "OLLAMA_DEFAULT_MODEL=phi" .env; then
        echo "  ✅ Command-line model override works"
    else
        echo "  ❌ Command-line model override failed to update .env"
        exit 1
    fi
else
    echo "  ❌ Command-line override test failed"
    exit 1
fi
echo

# Test 7: Documentation updates
echo "✓ Test 6: Documentation Updates"
docs_updated=0
if grep -q "automatically pulled\|Default model.*automatically" README.md; then
    echo "  ✅ README.md updated"
    docs_updated=$((docs_updated + 1))
else
    echo "  ❌ README.md not properly updated"
fi
if grep -q "Automatically Configured" docs/quickstart.md; then
    echo "  ✅ docs/quickstart.md updated"
    docs_updated=$((docs_updated + 1))
else
    echo "  ❌ docs/quickstart.md not properly updated"
fi
if grep -q "OLLAMA LLM Configuration" docs/configuration/vendor-config.md; then
    echo "  ✅ docs/configuration/vendor-config.md updated"
    docs_updated=$((docs_updated + 1))
else
    echo "  ❌ docs/configuration/vendor-config.md not properly updated"
fi

if [[ $docs_updated -eq 3 ]]; then
    echo "  ✅ All documentation files updated"
else
    echo "  ❌ Some documentation updates missing ($docs_updated/3)"
    exit 1
fi
echo

echo "=== All Tests Passed! ==="
echo
echo "OLLAMA Default Model Configuration Implementation Summary:"
echo "- ✅ Environment variables configured (OLLAMA_DEFAULT_MODEL, OLLAMA_AUTO_PULL)"
echo "- ✅ Bootstrap script created with proper argument handling"
echo "- ✅ Docker compose integration with environment variables"
echo "- ✅ Main script integration with --ollama-model option"
echo "- ✅ Command-line model override functionality"
echo "- ✅ Documentation updated across README, quickstart, and config guides"
echo
echo "🎉 OLLAMA now automatically configures with mistral model by default!"
echo
echo "Usage examples:"
echo "  bash scripts/aiops.sh up --all                    # Use default mistral"
echo "  bash scripts/aiops.sh up --all --ollama-model phi # Use phi model"
echo "  OLLAMA_AUTO_PULL=false bash scripts/aiops.sh up --all # Skip auto-pull"