#!/bin/bash
# Self-Healing Router E2E Test - Quick Start Script

echo "============================================================"
echo "SELF-HEALING ROUTER E2E TEST - QUICK START"
echo "============================================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Check if required packages are installed
echo "🔍 Checking dependencies..."
python3 -c "import psutil, aiohttp, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Installing required dependencies..."
    pip install psutil aiohttp requests
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies. Please install manually:"
        echo "   pip install psutil aiohttp requests"
        exit 1
    fi
fi

echo "✅ Dependencies OK"
echo ""

# Make script executable if not already
chmod +x e2e_self_healing_router_test.py

echo "🚀 Available test options:"
echo "  1. Quick Demo (recommended for first time)"
echo "  2. Generate Synthetic Data Only"  
echo "  3. Run Full E2E Test (2 minutes)"
echo "  4. Run Full E2E Test (10 minutes)" 
echo "  5. Validate System Prerequisites"
echo "  6. Custom Command"
echo ""

read -p "Choose option (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🎯 Running Quick Demo..."
        python3 e2e_self_healing_router_test.py
        ;;
    2)
        echo ""
        echo "📊 Generating Synthetic Data..."
        python3 e2e_self_healing_router_test.py --generate-data-only
        ;;
    3)
        echo ""
        echo "⚡ Running Full E2E Test (2 minutes)..."
        python3 e2e_self_healing_router_test.py --run-full-test --duration 2
        ;;
    4)
        echo ""
        echo "🔄 Running Full E2E Test (10 minutes)..."
        python3 e2e_self_healing_router_test.py --run-full-test --duration 10
        ;;
    5)
        echo ""
        echo "🔧 Validating System Prerequisites..."
        python3 e2e_self_healing_router_test.py --validate-system
        ;;
    6)
        echo ""
        echo "Available commands:"
        python3 e2e_self_healing_router_test.py --help
        echo ""
        read -p "Enter your command: python3 e2e_self_healing_router_test.py " custom_args
        python3 e2e_self_healing_router_test.py $custom_args
        ;;
    *)
        echo "❌ Invalid option. Please choose 1-6."
        exit 1
        ;;
esac

echo ""
echo "✅ Test execution completed!"
echo ""

# Show generated files
if ls self_healing_router_test_results_*.json 1> /dev/null 2>&1; then
    echo "📄 Generated files:"
    ls -la self_healing_router_*_*.json self_healing_router_*_*.txt 2>/dev/null | tail -5
    echo ""
fi

echo "📖 For more information, see: README_SELF_HEALING_ROUTER_E2E_TEST.md"
echo "🌟 Repository: https://github.com/iLodeStar/AIOps-NAAS"