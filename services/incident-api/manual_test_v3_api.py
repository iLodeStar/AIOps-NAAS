#!/usr/bin/env python3
"""
Manual test script for V3 API endpoints
This script tests the V3 endpoints without requiring a running Docker environment
"""

import sys
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_v3_endpoints():
    """Test V3 endpoints manually"""
    print("=" * 80)
    print("Manual V3 API Endpoint Testing")
    print("=" * 80)
    
    # Mock ClickHouse and NATS
    with patch('incident_api.ClickHouseClient'), \
         patch('incident_api.nats'):
        
        # Import after patching
        from incident_api import (
            app, service, 
            V3StatsResponse, V3TraceResponse, 
            V3IncidentCreate, V3IncidentResponse,
            get_v3_stats, get_v3_trace, create_v3_incident, get_v3_incident
        )
        from fastapi import Request
        from unittest.mock import AsyncMock
        
        print("\n✅ Successfully imported V3 endpoints and models")
        
        # Test 1: V3 Stats endpoint
        print("\n" + "=" * 80)
        print("TEST 1: /api/v3/stats endpoint")
        print("=" * 80)
        
        # Mock ClickHouse responses
        service.clickhouse_client = Mock()
        service.clickhouse_client.execute = Mock(side_effect=[
            [("critical", 10), ("high", 25), ("medium", 40)],  # severity
            [("open", 50), ("ack", 20), ("resolved", 5)],      # status
            [("cpu_pressure", 30), ("memory_pressure", 25)]    # category
        ])
        
        # Call the endpoint
        import asyncio
        stats_response = asyncio.run(get_v3_stats(time_range="1h"))
        
        print(f"✅ Stats endpoint returned successfully")
        print(f"   Time range: {stats_response.time_range}")
        print(f"   Incidents by severity: {stats_response.incidents_by_severity}")
        print(f"   Incidents by status: {stats_response.incidents_by_status}")
        print(f"   Incidents by category: {stats_response.incidents_by_category}")
        print(f"   Processing metrics: {stats_response.processing_metrics}")
        print(f"   SLO compliance: {stats_response.slo_compliance}")
        
        assert stats_response.time_range == "1h"
        assert "critical" in stats_response.incidents_by_severity
        assert "open" in stats_response.incidents_by_status
        print("   ✅ All assertions passed")
        
        # Test 2: V3 Trace endpoint
        print("\n" + "=" * 80)
        print("TEST 2: /api/v3/trace/{tracking_id} endpoint")
        print("=" * 80)
        
        tracking_id = "test-tracking-123"
        service.clickhouse_client.execute = Mock(return_value=[])
        
        trace_response = asyncio.run(get_v3_trace(tracking_id))
        
        print(f"✅ Trace endpoint returned successfully")
        print(f"   Tracking ID: {trace_response.tracking_id}")
        print(f"   Total latency: {trace_response.total_latency_ms}ms")
        print(f"   Number of stages: {len(trace_response.stages)}")
        print(f"   Stages:")
        for stage in trace_response.stages:
            print(f"      - {stage.stage}: {stage.latency_ms}ms ({stage.status})")
        
        assert trace_response.tracking_id == tracking_id
        assert trace_response.total_latency_ms > 0
        assert len(trace_response.stages) > 0
        print("   ✅ All assertions passed")
        
        # Test 3: V3 Create Incident endpoint
        print("\n" + "=" * 80)
        print("TEST 3: POST /api/v3/incidents endpoint")
        print("=" * 80)
        
        incident_create = V3IncidentCreate(
            incident_type="cpu_pressure",
            incident_severity="high",
            ship_id="ship-001",
            service="cpu-monitor",
            metric_name="cpu_usage",
            metric_value=95.5,
            anomaly_score=0.9,
            detector_name="threshold_detector",
            suggested_runbooks=["restart_service", "scale_resources"],
            metadata={"test": True}
        )
        
        service.store_incident = AsyncMock()
        
        incident_response = asyncio.run(create_v3_incident(incident_create))
        
        print(f"✅ Create incident endpoint returned successfully")
        print(f"   Incident ID: {incident_response.incident_id}")
        print(f"   Incident type: {incident_response.incident_type}")
        print(f"   Severity: {incident_response.incident_severity}")
        print(f"   Ship ID: {incident_response.ship_id}")
        print(f"   Service: {incident_response.service}")
        print(f"   Status: {incident_response.status}")
        print(f"   Tracking ID: {incident_response.tracking_id}")
        print(f"   Timeline entries: {len(incident_response.timeline)}")
        
        assert incident_response.incident_type == "cpu_pressure"
        assert incident_response.ship_id == "ship-001"
        assert incident_response.status == "open"
        assert incident_response.tracking_id is not None
        assert len(incident_response.timeline) > 0
        print("   ✅ All assertions passed")
        
        # Test 4: V3 Get Incident endpoint
        print("\n" + "=" * 80)
        print("TEST 4: GET /api/v3/incidents/{incident_id} endpoint")
        print("=" * 80)
        
        incident_id = incident_response.incident_id
        
        # Mock service response
        mock_incident = {
            "incident_id": incident_id,
            "incident_type": "cpu_pressure",
            "incident_severity": "high",
            "ship_id": "ship-001",
            "service": "cpu-monitor",
            "status": "open",
            "acknowledged": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "correlation_id": "corr-123",
            "metric_name": "cpu_usage",
            "metric_value": 95.5,
            "anomaly_score": 0.9,
            "detector_name": "threshold_detector",
            "timeline": json.dumps([{
                "timestamp": datetime.now().isoformat(),
                "event": "incident_created",
                "description": "Test incident"
            }]),
            "correlated_events": json.dumps([]),
            "suggested_runbooks": json.dumps(["restart_service"]),
            "metadata": json.dumps({"tracking_id": "test-123"})
        }
        
        service.get_incident_by_id = Mock(return_value=mock_incident)
        
        get_response = asyncio.run(get_v3_incident(incident_id))
        
        print(f"✅ Get incident endpoint returned successfully")
        print(f"   Incident ID: {get_response.incident_id}")
        print(f"   Incident type: {get_response.incident_type}")
        print(f"   Ship ID: {get_response.ship_id}")
        print(f"   Status: {get_response.status}")
        print(f"   Tracking ID: {get_response.tracking_id}")
        print(f"   Timeline: {len(get_response.timeline)} entries")
        print(f"   Suggested runbooks: {get_response.suggested_runbooks}")
        
        assert get_response.incident_id == incident_id
        assert get_response.incident_type == "cpu_pressure"
        assert get_response.tracking_id == "test-123"
        assert isinstance(get_response.timeline, list)
        assert isinstance(get_response.suggested_runbooks, list)
        print("   ✅ All assertions passed")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ ALL MANUAL TESTS PASSED")
        print("=" * 80)
        print("\nSummary:")
        print("  ✅ /api/v3/stats - Returns categorized incident counts and metrics")
        print("  ✅ /api/v3/trace/{tracking_id} - Returns end-to-end trace with latency")
        print("  ✅ POST /api/v3/incidents - Creates incident with V3 model")
        print("  ✅ GET /api/v3/incidents/{incident_id} - Retrieves incident with V3 model")
        print("\nAll V3 endpoints are functioning correctly! ✅")
        print("=" * 80)

if __name__ == "__main__":
    try:
        test_v3_endpoints()
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
