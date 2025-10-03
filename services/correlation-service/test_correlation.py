#!/usr/bin/env python3
"""
Test script for Correlation Service V3
Tests deduplication, windowing, and incident creation
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops_core.models import AnomalyEnriched, Domain, Severity, ContextData

# Import from current directory
sys.path.insert(0, os.path.dirname(__file__))
from deduplication import DeduplicationCache
from windowing import TimeWindowManager


def create_test_anomaly(
    tracking_id: str,
    ship_id: str = "test-ship",
    domain: Domain = Domain.SYSTEM,
    service: str = "test-service",
    severity: Severity = Severity.MEDIUM,
    anomaly_type: str = "cpu_high"
) -> AnomalyEnriched:
    """Create a test anomaly for testing"""
    return AnomalyEnriched(
        tracking_id=tracking_id,
        ts=datetime.utcnow(),
        ship_id=ship_id,
        domain=domain,
        anomaly_type=anomaly_type,
        service=service,
        device_id="device-1",
        score=0.85,
        detector="threshold_detector",
        metric_name="cpu_usage",
        metric_value=95.5,
        threshold=80.0,
        context=ContextData(
            similar_count_1h=2,
            similar_count_24h=5
        ),
        severity=severity,
        tags=["resource", "cpu"]
    )


def test_deduplication():
    """Test deduplication logic"""
    print("\n" + "="*60)
    print("TEST 1: Deduplication")
    print("="*60)
    
    cache = DeduplicationCache(ttl_seconds=60)
    
    # Create two identical anomalies
    anomaly1 = create_test_anomaly("track-1")
    anomaly2 = create_test_anomaly("track-2")  # Same attributes, different tracking_id
    
    # First anomaly should not be suppressed
    should_suppress_1, key_1 = cache.should_suppress(anomaly1)
    print(f"✓ First anomaly: suppress={should_suppress_1}, key={key_1}")
    assert not should_suppress_1, "First anomaly should not be suppressed"
    
    # Second anomaly should be suppressed (duplicate)
    should_suppress_2, key_2 = cache.should_suppress(anomaly2)
    print(f"✓ Second anomaly: suppress={should_suppress_2}, key={key_2}")
    assert should_suppress_2, "Second anomaly should be suppressed"
    assert key_1 == key_2, "Suppression keys should match"
    
    # Different severity should not be suppressed
    anomaly3 = create_test_anomaly("track-3", severity=Severity.CRITICAL)
    should_suppress_3, key_3 = cache.should_suppress(anomaly3)
    print(f"✓ Different severity: suppress={should_suppress_3}, key={key_3}")
    assert not should_suppress_3, "Different severity should not be suppressed"
    
    stats = cache.get_stats()
    print(f"\nDeduplication stats:")
    print(f"  Total checks: {stats['total_checks']}")
    print(f"  Duplicates found: {stats['duplicates_found']}")
    print(f"  Unique incidents: {stats['unique_incidents']}")
    print(f"  Cache size: {stats['cache_size']}")
    
    print("✅ Deduplication tests PASSED")


def test_windowing():
    """Test time-windowing logic"""
    print("\n" + "="*60)
    print("TEST 2: Time Windowing")
    print("="*60)
    
    manager = TimeWindowManager(correlation_threshold=3)
    
    # Add first anomaly - should not trigger
    anomaly1 = create_test_anomaly("track-1")
    result1 = manager.add_anomaly(anomaly1)
    print(f"✓ Added anomaly 1: triggered={result1 is not None}")
    assert result1 is None, "Should not trigger with 1 anomaly"
    
    # Add second anomaly - should not trigger
    anomaly2 = create_test_anomaly("track-2")
    result2 = manager.add_anomaly(anomaly2)
    print(f"✓ Added anomaly 2: triggered={result2 is not None}")
    assert result2 is None, "Should not trigger with 2 anomalies"
    
    # Add third anomaly - should trigger incident
    anomaly3 = create_test_anomaly("track-3")
    result3 = manager.add_anomaly(anomaly3)
    print(f"✓ Added anomaly 3: triggered={result3 is not None}")
    assert result3 is not None, "Should trigger with 3 anomalies"
    assert len(result3) == 3, "Should return 3 correlated anomalies"
    
    # Fourth anomaly should start new window
    anomaly4 = create_test_anomaly("track-4")
    result4 = manager.add_anomaly(anomaly4)
    print(f"✓ Added anomaly 4: triggered={result4 is not None}")
    assert result4 is None, "Should start new window after trigger"
    
    # Different ship should use different window
    anomaly5 = create_test_anomaly("track-5", ship_id="other-ship")
    result5 = manager.add_anomaly(anomaly5)
    print(f"✓ Added anomaly 5 (different ship): triggered={result5 is not None}")
    assert result5 is None, "Different ship should use separate window"
    
    stats = manager.get_stats()
    print(f"\nWindowing stats:")
    print(f"  Total anomalies: {stats['total_anomalies']}")
    print(f"  Windows created: {stats['windows_created']}")
    print(f"  Windows triggered: {stats['windows_triggered']}")
    print(f"  Active windows: {stats['active_windows']}")
    
    window_info = manager.get_window_info()
    print(f"\nActive windows:")
    for key, info in window_info.items():
        print(f"  {key}: {info['anomaly_count']} anomalies")
    
    print("✅ Windowing tests PASSED")


def test_integrated_workflow():
    """Test integrated deduplication + windowing workflow"""
    print("\n" + "="*60)
    print("TEST 3: Integrated Workflow")
    print("="*60)
    
    # Simulate the full correlation service logic
    import asyncio
    
    async def run_test():
        from correlation_service import CorrelationService
        
        # Mock NATS client
        class MockNATS:
            async def publish(self, topic, data):
                pass  # Mock publish - don't actually send
        
        service = CorrelationService()
        service.running = True  # Simulate running state
        service.nats = MockNATS()  # Mock NATS to avoid connection errors
        
        incidents_created = 0
        
        # Simulate processing anomalies for different issue types
        test_anomalies = [
            # CPU issues on ship-1 (3 anomalies -> 1 incident)
            create_test_anomaly("track-1", ship_id="ship-1", anomaly_type="cpu_high"),
            create_test_anomaly("track-2", ship_id="ship-1", anomaly_type="cpu_high"),
            create_test_anomaly("track-3", ship_id="ship-1", anomaly_type="cpu_high"),
            
            # Memory issues on ship-1 (3 anomalies -> 1 incident, different type)
            create_test_anomaly("track-4", ship_id="ship-1", anomaly_type="memory_high", service="memory-service"),
            create_test_anomaly("track-5", ship_id="ship-1", anomaly_type="memory_high", service="memory-service"),
            create_test_anomaly("track-6", ship_id="ship-1", anomaly_type="memory_high", service="memory-service"),
            
            # CPU issues on ship-2 (3 anomalies -> 1 incident, different ship)
            create_test_anomaly("track-7", ship_id="ship-2", anomaly_type="cpu_high"),
            create_test_anomaly("track-8", ship_id="ship-2", anomaly_type="cpu_high"),
            create_test_anomaly("track-9", ship_id="ship-2", anomaly_type="cpu_high"),
            
            # More CPU issues on ship-1 - window will trigger but incident suppressed (duplicate)
            create_test_anomaly("track-10", ship_id="ship-1", anomaly_type="cpu_high"),
            create_test_anomaly("track-11", ship_id="ship-1", anomaly_type="cpu_high"),
            create_test_anomaly("track-12", ship_id="ship-1", anomaly_type="cpu_high"),
        ]
        
        for anomaly in test_anomalies:
            # Simulate service correlation logic
            result = await service.correlate(anomaly)
            if result:
                incidents_created += 1
                print(f"  {anomaly.tracking_id}: INCIDENT CREATED (type={anomaly.anomaly_type}, ship={anomaly.ship_id})")
            else:
                prev_count = incidents_created
                if service.stats["duplicates_suppressed"] > 0 and anomaly.tracking_id == "track-12":
                    print(f"  {anomaly.tracking_id}: Window triggered but INCIDENT SUPPRESSED (duplicate)")
                else:
                    print(f"  {anomaly.tracking_id}: Added to window ({anomaly.anomaly_type})")
        
        print(f"\n✓ Processed {len(test_anomalies)} anomalies")
        print(f"✓ Created {incidents_created} incidents")
        print(f"✓ Suppressed {service.stats['duplicates_suppressed']} duplicate incidents")
        print(f"✓ Active windows: {service.window_manager.get_stats()['active_windows']}")
        
        # Should create 3 incidents (cpu/ship-1, memory/ship-1, cpu/ship-2) and suppress 1 duplicate
        assert incidents_created == 3, f"Expected 3 incidents, got {incidents_created}"
        assert service.stats['duplicates_suppressed'] == 1, f"Expected 1 suppressed, got {service.stats['duplicates_suppressed']}"
        
        return True
    
    success = asyncio.run(run_test())
    if success:
        print("✅ Integrated workflow tests PASSED")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CORRELATION SERVICE V3 - UNIT TESTS")
    print("="*60)
    
    try:
        test_deduplication()
        test_windowing()
        test_integrated_workflow()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
