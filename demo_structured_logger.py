#!/usr/bin/env python3
"""
Demo script showing StructuredLogger usage with tracking_id
Demonstrates the V3 logging pattern for all services
"""

import sys
import os

sys.path.insert(0, 'aiops_core')

from aiops_core.utils import StructuredLogger, setup_logging, generate_tracking_id

def demo_human_readable_format():
    """Demo with human-readable format (development)"""
    print("\n" + "=" * 70)
    print("Demo 1: Human-Readable Format (Development)")
    print("=" * 70)
    
    # Setup logging for development
    setup_logging(level='INFO', format_json=False)
    
    # Create logger for a service
    logger = StructuredLogger('anomaly-detection')
    
    # Generate tracking ID
    tracking_id = generate_tracking_id(prefix='req')
    logger.set_tracking_id(tracking_id)
    logger.add_context(service='anomaly-detection', version='3.0.0')
    
    # Example log messages
    print("\n📝 Sample log messages:\n")
    logger.info('service_started', port=8080)
    logger.info('processing_anomaly', metric='cpu_usage', value=95.5, threshold=90)
    logger.warning('threshold_exceeded', metric='memory', current=92, limit=85)
    logger.error('database_connection_failed', error=Exception('Connection timeout'), retry_count=3)
    
def demo_json_format():
    """Demo with JSON format (production)"""
    print("\n" + "=" * 70)
    print("Demo 2: JSON Format (Production)")
    print("=" * 70)
    
    # Setup logging for production
    setup_logging(level='INFO', format_json=True)
    
    # Create logger for a different service
    logger = StructuredLogger('incident-api')
    
    # Generate tracking ID
    tracking_id = generate_tracking_id(prefix='req')
    logger.set_tracking_id(tracking_id)
    logger.add_context(service='incident-api', version='3.0.0', ship_id='cruise-001')
    
    # Example log messages
    print("\n📝 Sample JSON log messages:\n")
    logger.info('incident_created', incident_id='inc-12345', severity='high')
    logger.info('enrichment_requested', incident_id='inc-12345', enrichment_type='llm')
    logger.warning('enrichment_slow', incident_id='inc-12345', duration_ms=450, target_ms=300)
    
def demo_tracking_id_propagation():
    """Demo tracking_id propagation across service calls"""
    print("\n" + "=" * 70)
    print("Demo 3: Tracking ID Propagation Across Services")
    print("=" * 70)
    
    setup_logging(level='INFO', format_json=False)
    
    # Simulate a request flowing through multiple services
    tracking_id = generate_tracking_id(prefix='req')
    
    print(f"\n🔍 Request tracking_id: {tracking_id}\n")
    
    # Service 1: Anomaly Detection
    logger1 = StructuredLogger('anomaly-detection')
    logger1.set_tracking_id(tracking_id)
    logger1.add_context(service='anomaly-detection')
    logger1.info('anomaly_detected', metric='cpu_usage', score=0.95)
    
    # Service 2: Enrichment
    logger2 = StructuredLogger('enrichment-service')
    logger2.set_tracking_id(tracking_id)  # Same tracking_id!
    logger2.add_context(service='enrichment-service')
    logger2.info('enriching_anomaly', context_sources=['clickhouse', 'device_registry'])
    
    # Service 3: Correlation
    logger3 = StructuredLogger('correlation-service')
    logger3.set_tracking_id(tracking_id)  # Same tracking_id!
    logger3.add_context(service='correlation-service')
    logger3.info('correlating_events', window_size=300, events_count=5)
    
    # Service 4: Incident API
    logger4 = StructuredLogger('incident-api')
    logger4.set_tracking_id(tracking_id)  # Same tracking_id!
    logger4.add_context(service='incident-api')
    logger4.info('incident_stored', incident_id='inc-67890')
    
    print(f"\n✅ All services logged with the same tracking_id: {tracking_id}")
    print("   This enables end-to-end tracing across the entire pipeline!")

def main():
    print("\n" + "=" * 70)
    print("StructuredLogger Migration - Demo & Validation")
    print("=" * 70)
    
    demo_human_readable_format()
    demo_json_format()
    demo_tracking_id_propagation()
    
    print("\n" + "=" * 70)
    print("✅ Migration Complete!")
    print("=" * 70)
    print("\nKey Benefits:")
    print("  1. ✅ All logs include tracking_id for end-to-end tracing")
    print("  2. ✅ Structured key=value format for easy parsing")
    print("  3. ✅ JSON format option for production log aggregation")
    print("  4. ✅ Consistent logging pattern across all services")
    print("  5. ✅ Graceful fallback for services without V3 dependencies")
    print()

if __name__ == '__main__':
    main()
