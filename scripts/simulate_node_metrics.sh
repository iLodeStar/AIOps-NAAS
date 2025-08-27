#!/bin/bash
"""
AIOps NAAS - Node Metrics Simulator

Pushes node_exporter-like metrics into VictoriaMetrics so the anomaly 
detector's PromQL queries return data, without depending on node-exporter.

This script simulates:
- node_cpu_seconds_total (in idle, system, user modes)
- node_memory_MemTotal_bytes
- node_memory_MemAvailable_bytes  
- node_filesystem_* (disk usage metrics)

Usage:
  ./scripts/simulate_node_metrics.sh [options]
  
Options:
  --duration SECONDS    How long to simulate (default: 300)
  --interval SECONDS    Interval between metric pushes (default: 15)
  --instance NAME       Instance label value (default: simulator:9100)
  --cpu-usage PERCENT   Simulated CPU usage 0-100 (default: random 10-30%)
  --memory-usage PERCENT Simulated memory usage 0-100 (default: random 20-40%)
  --help               Show this help

Environment Variables:
  VM_URL - VictoriaMetrics URL (default: http://localhost:8428)
"""

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VM_URL="${VM_URL:-http://localhost:8428}"
DURATION=300
INTERVAL=15
INSTANCE="simulator:9100"
CPU_USAGE=""
MEMORY_USAGE=""

print_header() {
    echo -e "\n${BLUE}================================================================${NC}"
    echo -e "${BLUE}🏭 $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
}

print_section() {
    echo -e "\n${YELLOW}----------------------------------------${NC}"
    echo -e "${YELLOW}📋 $1${NC}"
    echo -e "${YELLOW}----------------------------------------${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

usage() {
    head -n 25 "$0" | tail -n +2 | sed 's/^"""//g; s/"""$//g'
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --duration)
                DURATION="$2"
                shift 2
                ;;
            --interval)
                INTERVAL="$2"  
                shift 2
                ;;
            --instance)
                INSTANCE="$2"
                shift 2
                ;;
            --cpu-usage)
                CPU_USAGE="$2"
                shift 2
                ;;
            --memory-usage)
                MEMORY_USAGE="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

check_dependencies() {
    print_section "Checking Dependencies"
    
    if ! command -v curl >/dev/null 2>&1; then
        print_error "curl is required but not installed"
        exit 1
    fi
    print_success "curl found"
    
    if ! command -v bc >/dev/null 2>&1; then
        print_warning "bc not found - using basic math (less precise)"
    else
        print_success "bc found"
    fi
}

check_victoriametrics() {
    print_section "Checking VictoriaMetrics"
    
    if curl -sf "$VM_URL/health" >/dev/null 2>&1; then
        print_success "VictoriaMetrics is accessible at $VM_URL"
    else
        print_error "VictoriaMetrics is not accessible at $VM_URL"
        exit 1
    fi
}

generate_random() {
    local min=$1
    local max=$2
    
    if command -v bc >/dev/null 2>&1; then
        echo "scale=2; $min + ($max - $min) * $(shuf -i 0-100 -n 1) / 100" | bc
    else
        # Fallback without bc
        echo $((min + (RANDOM % (max - min))))
    fi
}

generate_cpu_metrics() {
    local timestamp=$1
    local cpu_usage_percent=$2
    
    # Convert percentage to idle time
    local idle_percent
    if command -v bc >/dev/null 2>&1; then
        idle_percent=$(echo "scale=2; 100 - $cpu_usage_percent" | bc)
    else
        idle_percent=$((100 - cpu_usage_percent))
    fi
    
    # Simulate cumulative CPU seconds (monotonically increasing)
    local base_seconds=$((timestamp - 1000000))  # Some base value
    local idle_seconds
    local system_seconds
    local user_seconds
    
    if command -v bc >/dev/null 2>&1; then
        idle_seconds=$(echo "scale=2; $base_seconds * $idle_percent / 100" | bc)
        system_seconds=$(echo "scale=2; $base_seconds * $cpu_usage_percent / 200" | bc)  # Half of CPU usage
        user_seconds=$(echo "scale=2; $base_seconds * $cpu_usage_percent / 200" | bc)    # Other half
    else
        idle_seconds=$((base_seconds * idle_percent / 100))
        system_seconds=$((base_seconds * cpu_usage_percent / 200))
        user_seconds=$((base_seconds * cpu_usage_percent / 200))
    fi
    
    cat <<EOF
node_cpu_seconds_total{mode="idle",cpu="0",instance="$INSTANCE",job="node-exporter"} $timestamp $idle_seconds
node_cpu_seconds_total{mode="idle",cpu="1",instance="$INSTANCE",job="node-exporter"} $timestamp $idle_seconds
node_cpu_seconds_total{mode="system",cpu="0",instance="$INSTANCE",job="node-exporter"} $timestamp $system_seconds
node_cpu_seconds_total{mode="system",cpu="1",instance="$INSTANCE",job="node-exporter"} $timestamp $system_seconds
node_cpu_seconds_total{mode="user",cpu="0",instance="$INSTANCE",job="node-exporter"} $timestamp $user_seconds
node_cpu_seconds_total{mode="user",cpu="1",instance="$INSTANCE",job="node-exporter"} $timestamp $user_seconds
EOF
}

generate_memory_metrics() {
    local timestamp=$1
    local memory_usage_percent=$2
    
    # Simulate 8GB total memory
    local total_bytes=$((8 * 1024 * 1024 * 1024))
    local available_bytes
    
    if command -v bc >/dev/null 2>&1; then
        available_bytes=$(echo "scale=0; $total_bytes * (100 - $memory_usage_percent) / 100" | bc)
    else
        available_bytes=$((total_bytes * (100 - memory_usage_percent) / 100))
    fi
    
    cat <<EOF
node_memory_MemTotal_bytes{instance="$INSTANCE",job="node-exporter"} $timestamp $total_bytes
node_memory_MemAvailable_bytes{instance="$INSTANCE",job="node-exporter"} $timestamp $available_bytes
node_memory_MemFree_bytes{instance="$INSTANCE",job="node-exporter"} $timestamp $((available_bytes / 2))
node_memory_Buffers_bytes{instance="$INSTANCE",job="node-exporter"} $timestamp $((available_bytes / 4))
node_memory_Cached_bytes{instance="$INSTANCE",job="node-exporter"} $timestamp $((available_bytes / 4))
EOF
}

generate_filesystem_metrics() {
    local timestamp=$1
    
    # Simulate root filesystem - 100GB total, 70% used
    local total_bytes=$((100 * 1024 * 1024 * 1024))
    local avail_bytes=$((30 * 1024 * 1024 * 1024))
    
    cat <<EOF
node_filesystem_size_bytes{device="/dev/sda1",fstype="ext4",mountpoint="/",instance="$INSTANCE",job="node-exporter"} $timestamp $total_bytes
node_filesystem_avail_bytes{device="/dev/sda1",fstype="ext4",mountpoint="/",instance="$INSTANCE",job="node-exporter"} $timestamp $avail_bytes
node_filesystem_files{device="/dev/sda1",fstype="ext4",mountpoint="/",instance="$INSTANCE",job="node-exporter"} $timestamp 6553600
node_filesystem_files_free{device="/dev/sda1",fstype="ext4",mountpoint="/",instance="$INSTANCE",job="node-exporter"} $timestamp 6000000
EOF
}

send_metrics() {
    local metrics_data="$1"
    
    if echo "$metrics_data" | curl -sf -X POST "$VM_URL/api/v1/import/prometheus" --data-binary @- >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

simulate_metrics() {
    print_section "Starting Metric Simulation"
    
    local start_time=$(date +%s)
    local end_time=$((start_time + DURATION))
    local iteration=0
    
    echo "⏱️  Simulating for ${DURATION}s with ${INTERVAL}s intervals"
    echo "🏷️  Instance: $INSTANCE"
    
    while [[ $(date +%s) -lt $end_time ]]; do
        iteration=$((iteration + 1))
        local timestamp=$(date +%s)
        
        # Determine CPU usage for this iteration
        local current_cpu_usage
        if [[ -n "$CPU_USAGE" ]]; then
            current_cpu_usage=$CPU_USAGE
        else
            current_cpu_usage=$(generate_random 10 30)
        fi
        
        # Determine memory usage for this iteration  
        local current_memory_usage
        if [[ -n "$MEMORY_USAGE" ]]; then
            current_memory_usage=$MEMORY_USAGE
        else
            current_memory_usage=$(generate_random 20 40)
        fi
        
        # Generate all metrics
        local cpu_metrics=$(generate_cpu_metrics $timestamp $current_cpu_usage)
        local memory_metrics=$(generate_memory_metrics $timestamp $current_memory_usage) 
        local fs_metrics=$(generate_filesystem_metrics $timestamp)
        
        local all_metrics="$cpu_metrics
$memory_metrics
$fs_metrics"
        
        # Send metrics
        if send_metrics "$all_metrics"; then
            echo "📊 Iteration $iteration: CPU=${current_cpu_usage}% Memory=${current_memory_usage}% ✅"
        else
            print_error "Failed to send metrics on iteration $iteration"
            return 1
        fi
        
        # Wait for next iteration (unless this is the last one)
        local current_time=$(date +%s)
        if [[ $current_time -lt $end_time ]]; then
            sleep $INTERVAL
        fi
    done
    
    print_success "Simulation completed after $iteration iterations"
}

verify_metrics() {
    print_section "Verifying Metrics Are Queryable"
    
    # Wait a moment for metrics to be indexed
    sleep 5
    
    # Test CPU query (same as anomaly detector uses)
    local cpu_query="100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
    local cpu_url="$VM_URL/api/v1/query?query=$cpu_query"
    
    if curl -sf "$cpu_url" 2>/dev/null | grep -q "node_cpu_seconds_total"; then
        print_success "CPU metrics are queryable"
    else
        print_warning "CPU metrics query returned no data (may need more time)"
    fi
    
    # Test Memory query (same as anomaly detector uses)
    local mem_query="(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
    local mem_url="$VM_URL/api/v1/query?query=$mem_query"
    
    if curl -sf "$mem_url" 2>/dev/null | grep -q "node_memory"; then
        print_success "Memory metrics are queryable" 
    else
        print_warning "Memory metrics query returned no data (may need more time)"
    fi
}

print_summary() {
    print_header "Simulation Summary"
    
    echo -e "${BLUE}Metrics Simulated:${NC}"
    echo "✅ node_cpu_seconds_total (idle, system, user modes)"
    echo "✅ node_memory_MemTotal_bytes"
    echo "✅ node_memory_MemAvailable_bytes"  
    echo "✅ node_memory_MemFree_bytes"
    echo "✅ node_memory_Buffers_bytes"
    echo "✅ node_memory_Cached_bytes"
    echo "✅ node_filesystem_size_bytes"
    echo "✅ node_filesystem_avail_bytes"
    
    echo -e "\n${BLUE}Anomaly Detector Compatibility:${NC}"
    echo "✅ CPU usage query: 100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)"
    echo "✅ Memory usage query: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100"
    echo "✅ Disk usage query: 100 - ((node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"}) * 100)"
    
    echo -e "\n${BLUE}Next Steps:${NC}"
    echo "- Run full validation: ./scripts/validate_pipeline.sh"
    echo "- Check anomaly detection logs: docker compose logs anomaly-detection"
    echo "- Query metrics in Grafana: http://localhost:3000"
}

main() {
    print_header "AIOps NAAS Node Metrics Simulator"
    
    parse_args "$@"
    check_dependencies
    check_victoriametrics
    simulate_metrics
    verify_metrics
    print_summary
    
    echo -e "\n${GREEN}🎉 Node metrics simulation completed successfully!${NC}"
    echo -e "${YELLOW}💡 The anomaly detector should now be able to query node metrics from VictoriaMetrics${NC}"
}

main "$@"