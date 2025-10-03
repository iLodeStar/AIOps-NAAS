#!/usr/bin/env python3
"""
Unit tests for V3 Anomaly Detection Service
Tests V3 model usage, tracking_id propagation, and StructuredLogger
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import V3 models
from aiops_core.models import AnomalyDetected, LogMessage, Domain
from aiops_core.utils import generate_tracking_id, StructuredLogger

# Import service components
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from anomaly_service import AnomalyDetectionService, AnomalyEvent


class TestV3AnomalyDetection:
    """Test suite for V3 anomaly detection service"""
    
    @pytest.fixture
    def service(self):
        """Create a test service instance"""
        with patch('anomaly_service.VictoriaMetricsClient'), \
             patch('anomaly_service.ClickHouseClient'), \
             patch('anomaly_service.DeviceRegistryClient'):
            service = AnomalyDetectionService()
            service.nats_client = AsyncMock()
            return service
    
    @pytest.fixture
    def sample_log_data(self):
        """Sample log data for testing"""
        return {
            'message': 'ERROR: Critical system failure detected',
            'tracking_id': 'test-20250103-120000-abc123',
            'level': 'ERROR',
            'anomaly_severity': 'high',
            'host': 'ship-001-device',
            'service': 'engine-monitor',
            'ship_id': 'ship-001',
            'device_id': 'engine-01',
            'timestamp': '2025-01-03T12:00:00Z'
        }
    
    def test_tracking_id_generation(self):
        """Test tracking_id generation and format"""
        tracking_id = generate_tracking_id()
        assert tracking_id.startswith('req-')
        parts = tracking_id.split('-')
        assert len(parts) == 4  # req-YYYYMMDD-HHMMSS-uuid
    
    def test_anomaly_event_to_v3_model(self):
        """Test conversion of AnomalyEvent to V3 AnomalyDetected model"""
        tracking_id = generate_tracking_id()
        event = AnomalyEvent(
            timestamp=datetime.now(),
            metric_name="cpu_usage",
            metric_value=95.5,
            anomaly_score=0.9,
            anomaly_type="threshold",
            detector_name="threshold_detector",
            threshold=0.8,
            metadata={"device_id": "cpu-01", "ship_id": "ship-001"},
            labels={"instance": "localhost"},
            tracking_id=tracking_id
        )
        
        v3_anomaly = event.to_v3_model(
            ship_id="ship-001",
            service="cpu-monitor",
            domain=Domain.SYSTEM
        )
        
        assert isinstance(v3_anomaly, AnomalyDetected)
        assert v3_anomaly.tracking_id == tracking_id
        assert v3_anomaly.ship_id == "ship-001"
        assert v3_anomaly.metric_name == "cpu_usage"
        assert v3_anomaly.metric_value == 95.5
        assert v3_anomaly.score == 0.9
        assert v3_anomaly.detector == "threshold_detector"
        assert v3_anomaly.service == "cpu-monitor"
        assert v3_anomaly.domain == Domain.SYSTEM
    
    @pytest.mark.asyncio
    async def test_process_anomalous_log_with_tracking_id(self, service, sample_log_data):
        """Test that process_anomalous_log preserves tracking_id"""
        # Create mock NATS message
        mock_msg = Mock()
        mock_msg.data = Mock()
        mock_msg.data.decode = Mock(return_value=json.dumps(sample_log_data))
        
        # Mock the publish method
        service.publish_anomaly_v3 = AsyncMock()
        
        # Process the log
        await service.process_anomalous_log(mock_msg)
        
        # Verify publish was called
        assert service.publish_anomaly_v3.called
        call_args = service.publish_anomaly_v3.call_args
        published_anomaly = call_args[0][0]
        
        # Verify V3 model and tracking_id preservation
        assert isinstance(published_anomaly, AnomalyDetected)
        assert published_anomaly.tracking_id == sample_log_data['tracking_id']
        assert published_anomaly.ship_id == sample_log_data['ship_id']
        assert published_anomaly.device_id == sample_log_data['device_id']
        assert published_anomaly.raw_msg == sample_log_data['message']
        assert published_anomaly.service == sample_log_data['service']
    
    @pytest.mark.asyncio
    async def test_publish_anomaly_v3(self, service):
        """Test V3 anomaly publishing"""
        tracking_id = generate_tracking_id()
        anomaly = AnomalyDetected(
            tracking_id=tracking_id,
            ts=datetime.now(),
            ship_id="ship-001",
            domain=Domain.SYSTEM,
            anomaly_type="log_pattern",
            metric_name="log_anomaly",
            metric_value=1.0,
            threshold=0.7,
            score=0.85,
            detector="log_pattern_detector",
            service="test-service",
            device_id="device-01",
            raw_msg="Test error message"
        )
        
        # Mock NATS client
        service.nats_client = AsyncMock()
        service.nats_client.is_closed = False
        
        # Publish
        await service.publish_anomaly_v3(anomaly)
        
        # Verify NATS publish was called
        assert service.nats_client.publish.called
        call_args = service.nats_client.publish.call_args
        
        # Check topic
        assert call_args[0][0] == "anomaly.detected"
        
        # Check payload is valid JSON
        payload = call_args[0][1].decode()
        parsed = json.loads(payload)
        assert parsed['tracking_id'] == tracking_id
        assert parsed['ship_id'] == "ship-001"
        assert parsed['score'] == 0.85
    
    def test_extract_ship_id(self, service):
        """Test ship_id extraction with various sources"""
        # Mock the device_registry_client to return None
        service.device_registry_client.lookup_hostname = Mock(return_value=None)
        
        # Test direct ship_id
        log_data = {'ship_id': 'ship-direct'}
        assert service._extract_ship_id(log_data) == 'ship-direct'
        
        # Test hostname derivation
        log_data = {'host': 'ship-002-device'}
        ship_id = service._extract_ship_id(log_data)
        assert 'ship' in ship_id.lower()
        
        # Test fallback to unknown
        log_data = {'host': 'unknown'}
        assert service._extract_ship_id(log_data) == 'unknown-ship'
    
    def test_extract_device_id(self, service):
        """Test device_id extraction"""
        # Mock the device_registry_client to return None
        service.device_registry_client.lookup_hostname = Mock(return_value=None)
        
        # Test direct device_id
        log_data = {'device_id': 'device-direct'}
        assert service._extract_device_id(log_data) == 'device-direct'
        
        # Test hostname fallback
        log_data = {'host': 'test-host'}
        assert service._extract_device_id(log_data) == 'test-host'
        
        # Test service name fallback
        log_data = {'service': 'test-service'}
        assert service._extract_device_id(log_data) == 'test-service'
    
    def test_calculate_anomaly_score(self, service):
        """Test anomaly score calculation based on severity"""
        # Critical severity
        score = service._calculate_anomaly_score('CRITICAL', 'critical')
        assert score == 0.95
        
        # Error severity
        score = service._calculate_anomaly_score('ERROR', 'high')
        assert score == 0.85
        
        # Warning severity
        score = service._calculate_anomaly_score('WARNING', 'medium')
        assert score == 0.75
        
        # Default
        score = service._calculate_anomaly_score('INFO', 'low')
        assert score == 0.6
    
    def test_is_normal_operational_message(self, service):
        """Test normal operational message filtering"""
        # Should filter out
        assert service._is_normal_operational_message("Health check OK")
        assert service._is_normal_operational_message("Status: OK")
        assert service._is_normal_operational_message("Heartbeat received")
        
        # Should NOT filter out
        assert not service._is_normal_operational_message("ERROR: System failure")
        assert not service._is_normal_operational_message("CRITICAL: Database connection lost")
    
    @pytest.mark.asyncio
    async def test_skip_info_logs(self, service, sample_log_data):
        """Test that INFO level logs are skipped"""
        # Modify to INFO level
        sample_log_data['level'] = 'INFO'
        sample_log_data['anomaly_severity'] = 'low'
        
        mock_msg = Mock()
        mock_msg.data = Mock()
        mock_msg.data.decode = Mock(return_value=json.dumps(sample_log_data))
        
        service.publish_anomaly_v3 = AsyncMock()
        
        # Process the log
        await service.process_anomalous_log(mock_msg)
        
        # Verify publish was NOT called
        assert not service.publish_anomaly_v3.called
    
    @pytest.mark.asyncio
    async def test_skip_normal_operational_messages(self, service, sample_log_data):
        """Test that normal operational messages are skipped"""
        # Set to normal operational message
        sample_log_data['message'] = "Health check passed successfully"
        sample_log_data['level'] = 'ERROR'  # Even with ERROR level
        
        mock_msg = Mock()
        mock_msg.data = Mock()
        mock_msg.data.decode = Mock(return_value=json.dumps(sample_log_data))
        
        service.publish_anomaly_v3 = AsyncMock()
        
        # Process the log
        await service.process_anomalous_log(mock_msg)
        
        # Verify publish was NOT called
        assert not service.publish_anomaly_v3.called
    
    def test_structured_logger_tracking_id(self):
        """Test StructuredLogger tracking_id propagation"""
        logger = StructuredLogger("test_logger", tracking_id="test-123")
        assert logger.tracking_id == "test-123"
        
        # Test setting tracking_id
        logger.set_tracking_id("test-456")
        assert logger.tracking_id == "test-456"
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self):
        """Test health check endpoint returns correct status"""
        with patch('anomaly_service.VictoriaMetricsClient'), \
             patch('anomaly_service.ClickHouseClient'), \
             patch('anomaly_service.DeviceRegistryClient'):
            service = AnomalyDetectionService()
            
            # Check initial health status
            assert "healthy" in service.health_status
            assert "vm_connected" in service.health_status
            assert "nats_connected" in service.health_status
            assert "clickhouse_connected" in service.health_status
            assert "registry_connected" in service.health_status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
