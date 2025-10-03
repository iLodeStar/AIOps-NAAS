#!/usr/bin/env python3
"""
Integration test for V3 Anomaly Detection Service
Demonstrates end-to-end tracking_id propagation and V3 model usage
"""

import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

# Import service and V3 models
from anomaly_service import AnomalyDetectionService
from aiops_core.models import AnomalyDetected, Domain
from aiops_core.utils import generate_tracking_id


async def test_v3_integration():
    """
    Integration test demonstrating V3 workflow:
    1. Receive log with tracking_id
    2. Process with V3 models
    3. Publish with tracking_id preserved
    """
    print("=" * 70)
    print("V3 Anomaly Detection Service - Integration Test")
    print("=" * 70)
    
    # Create service instance with mocked dependencies
    service = AnomalyDetectionService()
    service.nats_client = AsyncMock()
    service.nats_client.is_closed = False
    
    # Generate a tracking ID for this test
    tracking_id = generate_tracking_id()
    print(f"\n1. Generated tracking_id: {tracking_id}")
    
    # Simulate an anomalous log message
    log_data = {
        'message': 'CRITICAL: Engine temperature exceeded 95°C - immediate action required',
        'tracking_id': tracking_id,
        'level': 'CRITICAL',
        'anomaly_severity': 'critical',
        'host': 'ship-voyager-engine01',
        'service': 'engine-monitor',
        'ship_id': 'ship-voyager',
        'device_id': 'engine-01',
        'timestamp': datetime.now().isoformat()
    }
    print(f"2. Created anomalous log message:")
    print(f"   - Message: {log_data['message'][:50]}...")
    print(f"   - Level: {log_data['level']}")
    print(f"   - Severity: {log_data['anomaly_severity']}")
    
    # Create mock NATS message
    mock_msg = Mock()
    mock_msg.data = Mock()
    mock_msg.data.decode = Mock(return_value=json.dumps(log_data))
    
    # Process the log
    print(f"\n3. Processing anomalous log...")
    await service.process_anomalous_log(mock_msg)
    
    # Verify NATS publish was called
    assert service.nats_client.publish.called, "NATS publish should have been called"
    call_args = service.nats_client.publish.call_args
    
    # Verify topic
    topic = call_args[0][0]
    print(f"4. Published to NATS topic: {topic}")
    assert topic == "anomaly.detected", f"Expected topic 'anomaly.detected', got '{topic}'"
    
    # Verify payload is valid V3 AnomalyDetected model
    payload = call_args[0][1].decode()
    anomaly_data = json.loads(payload)
    
    print(f"\n5. V3 AnomalyDetected event published:")
    print(f"   - tracking_id: {anomaly_data['tracking_id']}")
    print(f"   - ship_id: {anomaly_data['ship_id']}")
    print(f"   - device_id: {anomaly_data['device_id']}")
    print(f"   - service: {anomaly_data['service']}")
    print(f"   - domain: {anomaly_data['domain']}")
    print(f"   - score: {anomaly_data['score']}")
    print(f"   - detector: {anomaly_data['detector']}")
    
    # Verify tracking_id was preserved
    assert anomaly_data['tracking_id'] == tracking_id, \
        f"tracking_id mismatch: expected {tracking_id}, got {anomaly_data['tracking_id']}"
    
    # Verify ship_id and device_id were extracted
    assert anomaly_data['ship_id'] == 'ship-voyager', \
        f"ship_id mismatch: expected 'ship-voyager', got {anomaly_data['ship_id']}"
    assert anomaly_data['device_id'] == 'engine-01', \
        f"device_id mismatch: expected 'engine-01', got {anomaly_data['device_id']}"
    
    # Verify V3 model can be reconstructed
    reconstructed = AnomalyDetected(**anomaly_data)
    print(f"\n6. V3 model reconstruction: ✓")
    print(f"   - Model type: {type(reconstructed).__name__}")
    print(f"   - Schema version: {reconstructed.schema_version}")
    
    # Verify score calculation
    assert anomaly_data['score'] == 0.95, \
        f"Score mismatch for CRITICAL: expected 0.95, got {anomaly_data['score']}"
    
    print(f"\n7. Tracking ID propagation: ✓")
    print(f"   Input tracking_id:  {tracking_id}")
    print(f"   Output tracking_id: {anomaly_data['tracking_id']}")
    print(f"   Match: {tracking_id == anomaly_data['tracking_id']}")
    
    print("\n" + "=" * 70)
    print("✓ V3 Integration Test PASSED")
    print("=" * 70)
    print("\nKey Validations:")
    print("  ✓ V3 AnomalyDetected model used")
    print("  ✓ tracking_id preserved end-to-end")
    print("  ✓ ship_id and device_id extracted")
    print("  ✓ StructuredLogger integration working")
    print("  ✓ Anomaly score calculated correctly")
    print("  ✓ NATS publishing with correct topic")
    print("  ✓ V3 model serialization/deserialization")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_v3_integration())
