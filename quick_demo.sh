#!/bin/bash
# Self-Healing Router E2E Test - Quick Demo (Non-interactive)

echo "============================================================"
echo "SELF-HEALING ROUTER E2E TEST - QUICK DEMO"
echo "============================================================"

# Install dependencies if needed
python3 -c "import psutil, aiohttp, requests" 2>/dev/null || pip install psutil aiohttp requests

# Make executable
chmod +x e2e_self_healing_router_test.py

echo ""
echo "🎯 Running Quick Demo to showcase AI model capabilities..."
echo ""

# Run the quick demo
python3 e2e_self_healing_router_test.py

echo ""
echo "✅ Demo completed! The system is ready for full E2E testing."
echo ""
echo "Next steps:"
echo "  📊 Generate data: python3 e2e_self_healing_router_test.py --generate-data-only"  
echo "  ⚡ Quick test:    python3 e2e_self_healing_router_test.py --run-full-test --duration 2"
echo "  🔄 Full test:     python3 e2e_self_healing_router_test.py --run-full-test"
echo ""
echo "📖 Documentation: README_SELF_HEALING_ROUTER_E2E_TEST.md"