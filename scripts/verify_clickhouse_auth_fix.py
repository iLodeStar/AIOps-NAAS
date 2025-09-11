#!/usr/bin/env python3
"""
Manual verification script for the incident API ClickHouse authentication fix.
This script demonstrates how to test the fix in a running environment.
"""

import json
import sys
import uuid
from datetime import datetime

def create_test_incident_payload():
    """Create a test incident payload"""
    incident_id = str(uuid.uuid4())
    
    return {
        "incident_id": incident_id,
        "event_type": "incident",
        "incident_type": "authentication_test",
        "incident_severity": "warning",
        "ship_id": "ship-01",
        "service": "test-service",
        "status": "open",
        "acknowledged": False,
        "created_at": datetime.now().isoformat() + "Z",
        "updated_at": datetime.now().isoformat() + "Z",
        "correlation_id": str(uuid.uuid4()),
        "metric_name": "test_metric",
        "metric_value": 85.0,
        "anomaly_score": 0.75,
        "detector_name": "manual_test",
        "timeline": [{
            "timestamp": datetime.now().isoformat(),
            "event": "incident_created",
            "description": "Test incident created to verify ClickHouse authentication fix",
            "source": "manual_verification",
            "metadata": {"test_type": "authentication_fix"}
        }],
        "correlated_events": [{
            "timestamp": datetime.now().isoformat(),
            "event_id": str(uuid.uuid4()),
            "source": "test_source",
            "message": "Correlated test event"
        }],
        "suggested_runbooks": [
            "check_authentication_logs",
            "verify_clickhouse_connection"
        ],
        "metadata": {
            "test_fix": True,
            "issue_number": 99,
            "fix_description": "ClickHouse authentication using environment variables"
        }
    }

def print_verification_commands():
    """Print commands to verify the fix"""
    print("=" * 80)
    print("Manual Verification Commands for ClickHouse Authentication Fix")
    print("=" * 80)
    
    print("\n🔧 STEP 1: Verify Docker Compose is running with correct credentials")
    print("-" * 65)
    print("# Check ClickHouse container environment")
    print("docker exec aiops-clickhouse env | grep CLICKHOUSE")
    print()
    print("# Check incident-api container environment")  
    print("docker exec aiops-incident-api env | grep CLICKHOUSE")
    print()
    print("# Test ClickHouse connectivity with correct credentials")
    print("docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query='SELECT 1'")
    
    print("\n🧪 STEP 2: Test incident creation via API")
    print("-" * 40)
    
    test_incident = create_test_incident_payload()
    
    print("# Create a test incident via the API endpoint")
    print("curl -X POST http://localhost:8081/incidents/test \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{}'".format(json.dumps(test_incident, indent=2)[:200] + "...}"))
    print()
    print("# Or use the built-in test endpoint")
    print("curl -X POST http://localhost:8081/incidents/test")
    
    print("\n📊 STEP 3: Verify incident storage in ClickHouse")
    print("-" * 50)
    print("# Check if the incident was stored successfully")
    print("docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \\")
    print("  --query=\"SELECT incident_id, incident_type, ship_id, created_at FROM logs.incidents ORDER BY created_at DESC LIMIT 5\"")
    print()
    print("# Check for authentication_test incidents specifically") 
    print("docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \\")
    print("  --query=\"SELECT * FROM logs.incidents WHERE incident_type='authentication_test' ORDER BY created_at DESC LIMIT 1\"")
    
    print("\n📋 STEP 4: Check application logs")
    print("-" * 35)
    print("# Check incident-api logs for authentication success")
    print("docker logs aiops-incident-api --tail 20 | grep -E '(Stored incident|ClickHouse|ERROR)'")
    print()
    print("# Check for any remaining authentication errors")
    print("docker logs aiops-incident-api --tail 50 | grep -i 'authentication\\|516'")
    
    print("\n✅ STEP 5: Expected Results")
    print("-" * 30)
    print("After the fix, you should see:")
    print("  • ✅ No 'Code: 516' authentication errors in logs")
    print("  • ✅ 'Stored incident: [UUID]' messages in incident-api logs")
    print("  • ✅ Test incidents appearing in ClickHouse queries")
    print("  • ✅ Incident API health check shows 'clickhouse_connected: true'")
    
    print("\n🔍 STEP 6: Health Check")
    print("-" * 25)
    print("# Check service health")
    print("curl http://localhost:8081/health | jq .")
    print()
    print("# Expected output:")
    print(json.dumps({
        "healthy": True,
        "clickhouse_connected": True,
        "nats_connected": True
    }, indent=2))

def save_test_incident_file():
    """Save test incident to file for easy testing"""
    incident = create_test_incident_payload()
    
    filename = "/tmp/test_incident.json"
    with open(filename, 'w') as f:
        json.dump(incident, f, indent=2)
    
    print(f"\n📝 Test incident payload saved to: {filename}")
    print("You can use this file to test incident creation:")
    print(f"curl -X POST http://localhost:8081/incidents/test -H 'Content-Type: application/json' -d @{filename}")

def main():
    """Main verification guide"""
    print_verification_commands()
    save_test_incident_file()
    
    print("\n" + "=" * 80)
    print("🚀 Ready to verify the ClickHouse authentication fix!")
    print("=" * 80)
    
    print("\nQuick Test Sequence:")
    print("1. docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query='SELECT 1'")
    print("2. curl -X POST http://localhost:8081/incidents/test")
    print("3. curl http://localhost:8081/health")
    print("4. docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin --query=\"SELECT COUNT(*) FROM logs.incidents\"")
    
    print("\nIf all steps work without authentication errors, the fix is successful! 🎉")

if __name__ == "__main__":
    main()