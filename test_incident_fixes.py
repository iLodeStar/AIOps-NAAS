#!/usr/bin/env python3
"""
Test script to validate incident creation fixes for Issue #105
Tests the complete flow from log generation to incident creation
"""

import asyncio
import json
import socket
import time
import uuid
from datetime import datetime
import requests
import subprocess
import sys

def send_test_log(message, level="ERROR", host="localhost", port=1516):
    """Send a test syslog message via TCP"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        # RFC3164 syslog format with timestamp
        timestamp = datetime.now().strftime("%b %d %H:%M:%S")
        syslog_message = f"<11>{timestamp} testhost test-service: {level} {message}\n"
        
        sock.send(syslog_message.encode())
        sock.close()
        print(f"✅ Sent {level} log: {message[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to send log: {e}")
        return False

def send_info_log_test():
    """Test that INFO logs don't create incidents"""
    print("\n📋 Test 1: INFO logs should NOT create incidents")
    
    test_id = f"INFO-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    info_message = f"Normal operation status update {test_id}"
    
    # Send INFO level message
    success = send_test_log(info_message, "INFO")
    if success:
        print(f"   🔍 Tracking ID: {test_id}")
        print("   ⏳ Waiting 10 seconds for processing...")
        time.sleep(10)
        return test_id
    return None

def send_error_log_test():
    """Test that ERROR logs DO create incidents with proper metadata"""
    print("\n📋 Test 2: ERROR logs should create incidents with metadata")
    
    test_id = f"ERROR-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
    error_message = f"Database connection failure - timeout exceeded {test_id}"
    
    # Send ERROR level message
    success = send_test_log(error_message, "ERROR")
    if success:
        print(f"   🔍 Tracking ID: {test_id}")
        print("   ⏳ Waiting 15 seconds for processing...")
        time.sleep(15)
        return test_id
    return None

def send_duplicate_test():
    """Test that duplicate errors are suppressed"""
    print("\n📋 Test 3: Duplicate ERROR logs should be suppressed")
    
    base_id = f"DUPLICATE-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    error_message = f"Critical system failure requiring attention {base_id}"
    
    tracking_ids = []
    for i in range(3):
        test_id = f"{base_id}-{i+1}"
        success = send_test_log(f"{error_message}-{i+1} {test_id}", "ERROR")
        if success:
            tracking_ids.append(test_id)
        time.sleep(2)  # Small delay between duplicates
    
    print(f"   🔍 Sent {len(tracking_ids)} similar ERROR messages")
    print("   ⏳ Waiting 20 seconds for processing...")
    time.sleep(20)
    return tracking_ids

def check_clickhouse_incidents(tracking_id=None):
    """Check ClickHouse for incidents"""
    try:
        if tracking_id:
            # Check for specific incident
            cmd = f"""docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT incident_id, incident_type, incident_severity, ship_id, service, metric_name, metric_value, anomaly_score FROM logs.incidents WHERE metadata LIKE '%{tracking_id}%' ORDER BY created_at DESC LIMIT 5" """
        else:
            # Check recent incidents
            cmd = f"""docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT incident_id, incident_type, incident_severity, ship_id, service, metric_name, metric_value, anomaly_score FROM logs.incidents ORDER BY created_at DESC LIMIT 10" """
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            print(f"   📊 Found {len(lines)} recent incidents:")
            for line in lines:
                if line.strip():
                    print(f"      {line}")
            return len(lines)
        else:
            print(f"   ❌ ClickHouse query failed: {result.stderr}")
            return 0
            
    except Exception as e:
        print(f"   ❌ Error checking ClickHouse: {e}")
        return 0

def check_incident_count():
    """Check total incident count"""
    try:
        cmd = """docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query="SELECT COUNT(*) FROM logs.incidents" """
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            count = int(result.stdout.strip())
            print(f"   📊 Total incidents in database: {count:,}")
            return count
        else:
            print(f"   ❌ Count query failed: {result.stderr}")
            return 0
            
    except Exception as e:
        print(f"   ❌ Error checking incident count: {e}")
        return 0

def check_logs_for_tracking_id(tracking_id, log_type="vector"):
    """Check if tracking ID appears in service logs"""
    try:
        cmd = f"docker compose logs {log_type} 2>/dev/null | grep '{tracking_id}' | head -5"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
        if lines and lines[0]:
            print(f"   🔍 Found {len(lines)} {log_type} log entries for {tracking_id}")
            return True
        else:
            print(f"   ❌ No {log_type} log entries found for {tracking_id}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error checking {log_type} logs: {e}")
        return False

def main():
    print("🚀 Starting Incident Creation Fix Validation")
    print("=" * 60)
    
    print("\n📈 Initial State Check:")
    initial_count = check_incident_count()
    
    # Test 1: INFO logs should not create incidents
    info_tracking_id = send_info_log_test()
    if info_tracking_id:
        print("\n🔍 Checking if INFO log created incident...")
        info_incidents = check_clickhouse_incidents(info_tracking_id)
        if info_incidents == 0:
            print("   ✅ PASS: INFO log did not create incident")
        else:
            print("   ❌ FAIL: INFO log created incident (should not happen)")
    
    # Test 2: ERROR logs should create incidents
    error_tracking_id = send_error_log_test()
    if error_tracking_id:
        print("\n🔍 Checking if ERROR log created incident with metadata...")
        error_incidents = check_clickhouse_incidents(error_tracking_id)
        if error_incidents > 0:
            print("   ✅ PASS: ERROR log created incident")
            # Check if tracking ID appears in processing logs
            check_logs_for_tracking_id(error_tracking_id, "anomaly-detection")
            check_logs_for_tracking_id(error_tracking_id, "benthos")
        else:
            print("   ❌ FAIL: ERROR log did not create incident")
    
    # Test 3: Duplicate suppression
    duplicate_tracking_ids = send_duplicate_test()
    if duplicate_tracking_ids:
        print(f"\n🔍 Checking duplicate suppression for {len(duplicate_tracking_ids)} similar errors...")
        total_found = 0
        for tid in duplicate_tracking_ids:
            found = check_clickhouse_incidents(tid)
            total_found += found
        
        if total_found <= 1:
            print(f"   ✅ PASS: Only {total_found} incident(s) created for {len(duplicate_tracking_ids)} similar errors")
        else:
            print(f"   ⚠️  PARTIAL: {total_found} incidents created for {len(duplicate_tracking_ids)} similar errors (suppression may need tuning)")
    
    print("\n📊 Final State Check:")
    final_count = check_incident_count()
    new_incidents = final_count - initial_count
    
    print(f"   📈 New incidents created during test: {new_incidents}")
    print(f"   📊 Expected: 1-2 incidents (only for ERROR logs)")
    
    if new_incidents <= 2:
        print("   ✅ OVERALL PASS: Incident creation is working correctly")
    elif new_incidents <= 5:
        print("   ⚠️  PARTIAL PASS: Some improvements working, may need fine-tuning")
    else:
        print("   ❌ NEEDS WORK: Too many incidents created")
    
    print("\n" + "=" * 60)
    print("🏁 Test Complete")
    
    # Show recent incidents for manual inspection
    print("\n📋 Recent incidents for manual inspection:")
    check_clickhouse_incidents()

if __name__ == "__main__":
    main()