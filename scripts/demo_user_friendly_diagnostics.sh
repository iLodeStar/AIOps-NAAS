#!/bin/bash
#
# Demonstration script for the user-friendly diagnostic tools
# This shows how non-technical users can use the new diagnostic features
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'  
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${PURPLE}============================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}============================================${NC}\n"
}

print_step() {
    echo -e "\n${BLUE}Step $1: $2${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
}

print_command() {
    echo -e "${YELLOW}Command: $1${NC}"
}

wait_for_user() {
    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read -r
}

print_header "AIOps NAAS User-Friendly Diagnostic Tools Demo"

echo -e "${CYAN}This demonstration shows how non-technical users can validate"
echo -e "their AIOps NAAS system using simple commands and clear explanations.${NC}"

wait_for_user

# Demonstrate help system
print_step 1 "Show Available Diagnostic Modes"
print_command "python3 scripts/user_friendly_diagnostics.py --help"
echo ""
python3 scripts/user_friendly_diagnostics.py --help
wait_for_user

# Demonstrate Makefile integration
print_step 2 "Show Makefile Integration"
print_info "The diagnostic tools are integrated into the project Makefile for easy access"
print_command "make help | grep -A 5 diagnose"
echo ""
make help | grep -A 5 diagnose
wait_for_user

# Demonstrate compatibility monitoring
print_step 3 "Test System Compatibility (Quick Mode)"
print_info "This shows how the system checks compatibility with different OS message formats"
print_command "python3 services/system-compatibility-monitor/compatibility_monitor.py --test-mode"
echo ""
python3 services/system-compatibility-monitor/compatibility_monitor.py --test-mode
wait_for_user

# Show available quick commands
print_step 4 "Show Quick Commands for Users"
echo -e "${CYAN}Non-technical users can run diagnostics with simple commands:${NC}\n"

echo -e "${GREEN}Daily Health Check:${NC}"
print_command "make diagnose MODE=sanity"
echo -e "   ${CYAN}→ 5-minute quick test to verify system is working${NC}\n"

echo -e "${GREEN}Weekly Comprehensive Test:${NC}"
print_command "make diagnose MODE=regression"
echo -e "   ${CYAN}→ 15-minute test of all system capabilities${NC}\n"

echo -e "${GREEN}System Monitoring:${NC}"
print_command "make diagnose MODE=surveillance"
echo -e "   ${CYAN}→ 15-minute passive monitoring of real system data${NC}\n"

echo -e "${GREEN}Full Certification Test:${NC}"
print_command "make diagnose MODE=automation"
echo -e "   ${CYAN}→ 1-hour autonomous system validation${NC}\n"

echo -e "${GREEN}Continuous Compatibility Monitoring:${NC}"
print_command "make compatibility-monitor"
echo -e "   ${CYAN}→ Monitor system compatibility with different OS types${NC}\n"

wait_for_user

# Show user documentation
print_step 5 "User Documentation Available"
echo -e "${CYAN}Comprehensive documentation has been created for non-technical users:${NC}\n"

echo -e "${GREEN}Main User Guide:${NC}"
echo -e "   ${CYAN}docs/user-guides/diagnostic-tool-guide.md${NC}"
echo -e "   ${CYAN}→ Complete guide with explanations in simple terms${NC}\n"

echo -e "${GREEN}Quick Reference Card:${NC}" 
echo -e "   ${CYAN}docs/user-guides/quick-reference-card.md${NC}"
echo -e "   ${CYAN}→ One-page reference for common operations${NC}\n"

print_info "Let's preview the quick reference card:"
echo ""
head -30 docs/user-guides/quick-reference-card.md
wait_for_user

# Show example of user-friendly output format
print_step 6 "Example of User-Friendly Results Interpretation"
echo -e "${CYAN}The diagnostic tools provide clear, color-coded feedback:${NC}\n"

echo -e "${GREEN}✅ Success Messages${NC} - Everything working perfectly"
echo -e "${YELLOW}⚠️  Warning Messages${NC} - Minor issues, system still functional"
echo -e "${RED}❌ Error Messages${NC} - Problems requiring attention"
echo -e "${BLUE}ℹ️  Information Messages${NC} - Helpful context, no action needed"

echo -e "\n${CYAN}Each test includes explanations like:${NC}"
echo -e "   • What the test does"
echo -e "   • What the results mean"
echo -e "   • What actions to take if needed"
echo -e "   • Troubleshooting guidance"

wait_for_user

# Show the four testing modes explained
print_step 7 "Four Testing Modes Explained for Users"

echo -e "${GREEN}1. SANITY MODE${NC} (Beginner-friendly)"
echo -e "   Duration: 5 minutes"
echo -e "   Tests: 1 normal message + 1 problem message"
echo -e "   Use: Daily checks, after system changes, troubleshooting"
echo ""

echo -e "${GREEN}2. REGRESSION MODE${NC} (Comprehensive)"
echo -e "   Duration: 15 minutes"
echo -e "   Tests: All message types and system capabilities"
echo -e "   Use: Weekly validation, after major updates, thorough testing"
echo ""

echo -e "${GREEN}3. SURVEILLANCE MODE${NC} (Passive monitoring)"
echo -e "   Duration: 15 minutes"
echo -e "   Tests: Watches real system data without injecting test data"
echo -e "   Use: Understanding normal behavior, troubleshooting real issues"
echo ""

echo -e "${GREEN}4. AUTOMATION MODE${NC} (Full autonomous)"
echo -e "   Duration: 1 hour"
echo -e "   Tests: Complete system validation with detailed insights"
echo -e "   Use: Monthly certification, compliance reporting, deep analysis"

wait_for_user

print_header "Demo Complete"

echo -e "${GREEN}Summary of Features Implemented:${NC}"
echo -e "✅ User-friendly diagnostic tool with 4 modes"
echo -e "✅ System compatibility monitoring service"
echo -e "✅ Clear documentation for non-technical users"
echo -e "✅ Makefile integration for easy access"
echo -e "✅ Color-coded results with explanations"
echo -e "✅ Support for different OS message formats"
echo -e "✅ Automated testing and validation"

echo -e "\n${CYAN}Files created:${NC}"
echo -e "• scripts/user_friendly_diagnostics.py - Main diagnostic tool"
echo -e "• services/system-compatibility-monitor/ - Compatibility monitoring"
echo -e "• docs/user-guides/diagnostic-tool-guide.md - User documentation"
echo -e "• docs/user-guides/quick-reference-card.md - Quick reference"
echo -e "• tests/test_user_friendly_diagnostics.py - Test validation"
echo -e "• Makefile updates - Easy command access"

echo -e "\n${GREEN}Ready for non-technical users to validate their AIOps NAAS system!${NC}"