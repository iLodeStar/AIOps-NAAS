#!/usr/bin/env python3
"""
Test script to validate the ship_id resolution fix in the incident API
"""
import asyncio
import sys
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Add the services directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'incident-api'))

from incident_api import IncidentAPIService


async def test_ship_id_resolution():
    """Test the new ship_id resolution logic"""
    
    # Create a service instance with mocked dependencies
    service = IncidentAPIService()
    
    # Test case 1: Valid ship_id already present
    incident_data_1 = {
        "incident_id": "test-1",
        "ship_id": "ship-dhruv",
        "host": "test-host"
    }
    
    result_1 = await service.resolve_ship_id(incident_data_1)
    print(f"Test 1 - Valid ship_id: {result_1} (Expected: ship-dhruv)")
    assert result_1 == "ship-dhruv", f"Expected 'ship-dhruv', got '{result_1}'"
    
    # Test case 2: Missing ship_id, hostname derivation
    incident_data_2 = {
        "incident_id": "test-2",
        "host": "dhruv-system-01"
    }
    
    with patch('requests.get') as mock_get:
        # Mock device registry response failure
        mock_get.return_value.status_code = 404
        
        result_2 = await service.resolve_ship_id(incident_data_2)
        print(f"Test 2 - Hostname derivation: {result_2} (Expected: dhruv-ship)")
        assert result_2 == "dhruv-ship", f"Expected 'dhruv-ship', got '{result_2}'"
    
    # Test case 3: Device registry successful lookup
    incident_data_3 = {
        "incident_id": "test-3",
        "host": "ubuntu-vm-01"
    }
    
    with patch('requests.get') as mock_get:
        # Mock successful device registry response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "mapping": {"ship_id": "ship-dhruv"}
        }
        mock_get.return_value = mock_response
        
        result_3 = await service.resolve_ship_id(incident_data_3)
        print(f"Test 3 - Device registry lookup: {result_3} (Expected: ship-dhruv)")
        assert result_3 == "ship-dhruv", f"Expected 'ship-dhruv', got '{result_3}'"
    
    # Test case 4: No hostname available, fallback
    incident_data_4 = {
        "incident_id": "test-4",
        "ship_id": "unknown"
    }
    
    result_4 = await service.resolve_ship_id(incident_data_4)
    print(f"Test 4 - No hostname fallback: {result_4} (Expected: unknown-ship)")
    assert result_4 == "unknown-ship", f"Expected 'unknown-ship', got '{result_4}'"
    
    print("✅ All ship_id resolution tests passed!")


async def test_incident_storage_integration():
    """Test that store_incident properly uses the new ship_id resolution"""
    service = IncidentAPIService()
    
    # Mock ClickHouse client
    service.clickhouse_client = MagicMock()
    
    # Test incident data
    incident_data = {
        "incident_id": "test-incident-1",
        "incident_type": "test_anomaly",
        "incident_severity": "warning",
        "host": "dhruv-system-01",
        "service": "test-service",
        "created_at": "2025-09-11T13:45:54.029Z",
        "updated_at": "2025-09-11T13:45:54.029Z"
    }
    
    with patch('requests.get') as mock_get:
        # Mock device registry failure (should fallback to hostname derivation)
        mock_get.return_value.status_code = 404
        
        # Store the incident
        await service.store_incident(incident_data)
        
        # Verify ClickHouse was called with resolved ship_id
        service.clickhouse_client.execute.assert_called_once()
        call_args = service.clickhouse_client.execute.call_args[0]
        stored_values = call_args[1][0]
        
        # The ship_id should be at index 4 in the values tuple
        stored_ship_id = stored_values[4]
        print(f"Stored ship_id: {stored_ship_id} (Expected: dhruv-ship)")
        assert stored_ship_id == "dhruv-ship", f"Expected 'dhruv-ship', got '{stored_ship_id}'"
    
    print("✅ Incident storage integration test passed!")


async def main():
    """Run all tests"""
    try:
        await test_ship_id_resolution()
        await test_incident_storage_integration()
        print("\n🎉 All tests passed! The ship_id fix is working correctly.")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)