#!/bin/bash

# One-Click Incident Debugging - Easy Launch Script
# This script provides a simple interface to run the comprehensive diagnostic tool

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 ONE-CLICK INCIDENT DEBUGGING TOOL"
echo "====================================="
echo "This tool provides comprehensive end-to-end incident data debugging."
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Check if Docker Compose is running
check_services() {
    print_status "$BLUE" "🔍 Checking service status..."
    
    # Try both docker compose and docker-compose for compatibility
    local compose_cmd=""
    if docker compose ps > /dev/null 2>&1; then
        compose_cmd="docker compose"
    elif docker-compose ps > /dev/null 2>&1; then
        compose_cmd="docker-compose"
    else
        print_status "$RED" "❌ Docker Compose not found or not running"
        echo "Please ensure Docker Compose is installed and services are running:"
        echo "  docker-compose up -d  OR  docker compose up -d"
        exit 1
    fi
    
    # Check if key services are running
    local running_services=$($compose_cmd ps --services --filter "status=running" 2>/dev/null | wc -l)
    local total_services=$($compose_cmd config --services 2>/dev/null | wc -l)
    
    if [ "$running_services" -lt 5 ]; then
        print_status "$YELLOW" "⚠️  Only $running_services/$total_services services running"
        echo "Consider starting all services: docker-compose up -d"
        echo ""
        echo "Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_status "$GREEN" "✅ Services are running ($running_services/$total_services)"
    fi
}

# Install Python dependencies if needed
check_dependencies() {
    print_status "$BLUE" "📦 Checking Python dependencies..."
    
    if ! python3 -c "import requests" &> /dev/null; then
        print_status "$YELLOW" "📥 Installing required Python packages..."
        pip3 install requests
    fi
    
    print_status "$GREEN" "✅ Dependencies ready"
}

# Show menu options
show_menu() {
    echo ""
    echo "Select diagnostic mode:"
    echo "1) 🔍 Quick Diagnostic (recommended for first run)"
    echo "2) 🔬 Deep Analysis (comprehensive with extended monitoring)" 
    echo "3) 📝 Full Report Generation (creates GitHub-ready issue)"
    echo "4) 🛠  Advanced Options"
    echo "5) ❓ Help & Documentation"
    echo "6) 🚪 Exit"
    echo ""
    echo -n "Enter your choice (1-6): "
}

# Run quick diagnostic
run_quick_diagnostic() {
    print_status "$GREEN" "🔍 Running Quick Diagnostic..."
    echo ""
    cd "$PROJECT_ROOT"
    python3 scripts/one_click_incident_debugging.py
}

# Run deep analysis
run_deep_analysis() {
    print_status "$GREEN" "🔬 Running Deep Analysis..."
    echo ""
    cd "$PROJECT_ROOT"
    python3 scripts/one_click_incident_debugging.py --deep-analysis
}

# Run full report generation
run_full_report() {
    print_status "$GREEN" "📝 Running Full Report Generation..."
    echo ""
    cd "$PROJECT_ROOT"
    python3 scripts/one_click_incident_debugging.py --deep-analysis --generate-issue-report
    
    echo ""
    print_status "$GREEN" "✅ Report generated! Check for INCIDENT_DATA_ISSUE_REPORT_*.md file"
}

# Show advanced options
show_advanced_options() {
    echo ""
    echo "Advanced Options:"
    echo "a) 🔧 Install/Update NATS CLI in containers"
    echo "b) 📊 Check current incident data quality"
    echo "c) 🧪 Generate test data only (no analysis)"
    echo "d) 🔙 Back to main menu"
    echo ""
    echo -n "Enter your choice (a-d): "
    
    read -r adv_choice
    case $adv_choice in
        a|A)
            install_nats_cli
            ;;
        b|B)
            check_incident_quality
            ;;
        c|C)
            generate_test_data_only
            ;;
        d|D)
            return
            ;;
        *)
            echo "Invalid option. Please try again."
            show_advanced_options
            ;;
    esac
}

# Install NATS CLI
install_nats_cli() {
    print_status "$BLUE" "🔧 Installing NATS CLI..."
    
    # Check if NATS container is running
    if ! docker ps | grep -q "aiops-nats"; then
        print_status "$RED" "❌ NATS container not running"
        return
    fi
    
    print_status "$YELLOW" "📥 Installing NATS CLI in container..."
    
    # Install NATS CLI
    docker exec aiops-nats sh -c "
        apk update && 
        apk add curl && 
        curl -sf https://binaries.nats.dev/nats-io/nats/v2@latest | sh && 
        mv nats /usr/local/bin/ && 
        chmod +x /usr/local/bin/nats
    " 2>/dev/null
    
    # Verify installation
    if docker exec aiops-nats nats --version > /dev/null 2>&1; then
        print_status "$GREEN" "✅ NATS CLI installed successfully"
        
        # Show available streams
        echo ""
        print_status "$BLUE" "📊 Available NATS streams:"
        docker exec aiops-nats nats stream ls 2>/dev/null || echo "  No streams found"
    else
        print_status "$RED" "❌ NATS CLI installation failed"
    fi
}

# Check current incident quality
check_incident_quality() {
    print_status "$BLUE" "📊 Checking current incident data quality..."
    
    if ! docker ps | grep -q "aiops-clickhouse"; then
        print_status "$RED" "❌ ClickHouse container not running"
        return
    fi
    
    echo ""
    print_status "$YELLOW" "Recent incidents:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \
        --query="SELECT incident_id, ship_id, service, metric_name, metric_value, processing_timestamp FROM logs.incidents ORDER BY processing_timestamp DESC LIMIT 5" 2>/dev/null || \
        print_status "$RED" "❌ Could not query ClickHouse"
    
    echo ""
    print_status "$YELLOW" "Data quality summary:"
    docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \
        --query="SELECT 
            COUNT(*) as total_incidents,
            SUM(CASE WHEN ship_id = 'unknown-ship' THEN 1 ELSE 0 END) as unknown_ships,
            SUM(CASE WHEN service = 'unknown_service' THEN 1 ELSE 0 END) as unknown_services,
            SUM(CASE WHEN metric_name = 'unknown_metric' THEN 1 ELSE 0 END) as unknown_metrics,
            SUM(CASE WHEN metric_value = 0 THEN 1 ELSE 0 END) as zero_values
         FROM logs.incidents" 2>/dev/null || \
        print_status "$RED" "❌ Could not analyze data quality"
}

# Generate test data only
generate_test_data_only() {
    print_status "$BLUE" "🧪 This would generate test data only..."
    echo "This feature is integrated into the main diagnostic tool."
    echo "Use option 1 or 2 to run the full analysis with test data generation."
}

# Show help
show_help() {
    echo ""
    echo "🔍 ONE-CLICK INCIDENT DEBUGGING TOOL HELP"
    echo "=========================================="
    echo ""
    echo "This tool addresses the issue where ClickHouse incidents contain fallback values:"
    echo "  - ship_id: 'unknown-ship'"
    echo "  - service: 'unknown_service'"
    echo "  - metric_name: 'unknown_metric'"
    echo "  - metric_value: 0"
    echo ""
    echo "DIAGNOSTIC MODES:"
    echo ""
    echo "1) Quick Diagnostic:"
    echo "   - Checks service health"
    echo "   - Generates 3 test data points"
    echo "   - Tracks data through pipeline"
    echo "   - Identifies basic mismatches"
    echo "   - Runtime: ~2-3 minutes"
    echo ""
    echo "2) Deep Analysis:"
    echo "   - All quick diagnostic features"
    echo "   - Extended monitoring periods"
    echo "   - Detailed NATS stream analysis"
    echo "   - Component-level debugging"
    echo "   - Runtime: ~5-7 minutes"
    echo ""
    echo "3) Full Report Generation:"
    echo "   - Deep analysis + GitHub issue report"
    echo "   - Reproduction steps with exact data"
    echo "   - Copy-paste ready issue content"
    echo "   - Complete diagnostic log"
    echo "   - Runtime: ~5-7 minutes"
    echo ""
    echo "OUTPUT:"
    echo "  - Console: Real-time diagnostic progress"
    echo "  - File: INCIDENT_DATA_ISSUE_REPORT_*.md (if report generated)"
    echo ""
    echo "REQUIREMENTS:"
    echo "  - Docker Compose services running"
    echo "  - Python 3 with requests library"
    echo "  - Network access to service ports"
    echo ""
    echo "TROUBLESHOOTING:"
    echo "  - If services are unhealthy: docker-compose up -d"
    echo "  - If Python errors: pip3 install requests"
    echo "  - If NATS issues: Use Advanced Options → Install NATS CLI"
    echo ""
    echo "For more details, see: docs/incident-data-debugging-guide.md"
    echo ""
    read -p "Press Enter to continue..."
}

# Main execution
main() {
    # Check prerequisites
    check_services
    check_dependencies
    
    # Main menu loop
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1)
                run_quick_diagnostic
                ;;
            2)
                run_deep_analysis
                ;;
            3)
                run_full_report
                ;;
            4)
                show_advanced_options
                ;;
            5)
                show_help
                ;;
            6)
                print_status "$GREEN" "👋 Goodbye!"
                exit 0
                ;;
            *)
                echo "Invalid option. Please enter 1-6."
                ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Handle script interruption
trap 'print_status "$YELLOW" "\n⚠️  Diagnostic interrupted. Partial results may be available."; exit 1' INT

# Run main function
main "$@"
