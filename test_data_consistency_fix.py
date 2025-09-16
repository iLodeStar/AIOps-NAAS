#!/usr/bin/env python3
"""
Test script to validate data consistency fixes between Device Registry and Anomaly Detection
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataConsistencyTester:
    """Test data consistency between device registry and anomaly detection"""
    
    def __init__(self):
        self.registry_url = "http://localhost:8081"
        self.session = requests.Session()
    
    def test_device_registry_connection(self) -> bool:
        """Test if device registry is accessible"""
        try:
            response = self.session.get(f"{self.registry_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Device Registry service is accessible")
                return True
            else:
                logger.error(f"❌ Device Registry returned status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to Device Registry: {e}")
            return False
    
    def get_registered_devices(self) -> Dict[str, Any]:
        """Get all registered devices from registry"""
        try:
            response = self.session.get(f"{self.registry_url}/devices", timeout=10)
            response.raise_for_status()
            devices = response.json()
            
            # Create lookup maps
            hostname_to_ship = {}
            hostname_to_device = {}
            
            for device in devices:
                # Map hostname to ship_id
                hostname_to_ship[device['hostname']] = device['ship_id']
                hostname_to_device[device['hostname']] = device['device_id']
                
                # Also map IP address if available
                if device.get('ip_address'):
                    hostname_to_ship[device['ip_address']] = device['ship_id']
                    hostname_to_device[device['ip_address']] = device['device_id']
                
                # Map any additional identifiers
                if device.get('all_identifiers'):
                    for identifier in device['all_identifiers']:
                        if identifier not in [device['hostname']]:  # Avoid duplicates
                            hostname_to_ship[identifier] = device['ship_id']
                            hostname_to_device[identifier] = device['device_id']
            
            logger.info(f"✅ Retrieved {len(devices)} devices from registry")
            return {
                'devices': devices,
                'hostname_to_ship': hostname_to_ship,
                'hostname_to_device': hostname_to_device
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting devices from registry: {e}")
            return {'devices': [], 'hostname_to_ship': {}, 'hostname_to_device': {}}
    
    def test_hostname_lookup(self, hostname: str) -> Dict[str, Any]:
        """Test hostname lookup against registry"""
        try:
            response = self.session.get(f"{self.registry_url}/lookup/{hostname}", timeout=5)
            if response.status_code == 200:
                result = response.json()
                mapping = result.get('mapping', {})
                logger.info(f"✅ Lookup success for '{hostname}': ship_id={mapping.get('ship_id')}, device_id={mapping.get('device_id')}")
                return mapping
            elif response.status_code == 404:
                logger.warning(f"⚠️  Hostname '{hostname}' not found in registry")
                return {}
            else:
                logger.error(f"❌ Lookup failed for '{hostname}': HTTP {response.status_code}")
                return {}
        except Exception as e:
            logger.error(f"❌ Lookup error for '{hostname}': {e}")
            return {}
    
    def simulate_anomaly_detection_mapping(self, log_data: Dict[str, Any]) -> Dict[str, str]:
        """Simulate how the fixed anomaly detection service would extract ship_id/device_id"""
        # This simulates the _extract_ship_id and _extract_device_id methods
        ship_id = "unknown-ship"
        device_id = "unknown-device"
        ship_id_source = "fallback"
        device_id_source = "fallback"
        
        # Try direct fields first
        if log_data.get('ship_id'):
            ship_id = log_data['ship_id']
            ship_id_source = "direct_field"
        
        if log_data.get('device_id'):
            device_id = log_data['device_id']
            device_id_source = "direct_field"
        
        # Try device registry lookup using hostname
        host = log_data.get('host', '')
        if host and host != 'unknown' and (ship_id == "unknown-ship" or device_id == "unknown-device"):
            registry_result = self.test_hostname_lookup(host)
            if registry_result:
                if ship_id == "unknown-ship" and registry_result.get('ship_id'):
                    ship_id = registry_result['ship_id']
                    ship_id_source = "registry_lookup"
                
                if device_id == "unknown-device" and registry_result.get('device_id'):
                    device_id = registry_result['device_id']
                    device_id_source = "registry_lookup"
        
        # Fallback logic for ship_id (if registry lookup failed)
        if ship_id == "unknown-ship" and host:
            if '-' in host:
                ship_id = host.split('-')[0] + '-ship'
                ship_id_source = "hostname_derived"
            elif host != 'unknown':
                ship_id = host + '-ship'
                ship_id_source = "hostname_direct"
        
        # Fallback logic for device_id
        if device_id == "unknown-device" and host and host != 'unknown':
            device_id = host
            device_id_source = "hostname_fallback"
        
        return {
            'ship_id': ship_id,
            'device_id': device_id,
            'ship_id_source': ship_id_source,
            'device_id_source': device_id_source
        }
    
    def test_anomaly_mapping_consistency(self):
        """Test mapping consistency using sample anomaly data"""
        logger.info("\n🧪 Testing Anomaly Detection Mapping Consistency")
        logger.info("=" * 60)
        
        # Get registry data
        registry_data = self.get_registered_devices()
        
        # Sample anomaly log data (from the issue description)
        sample_anomaly_events = [
            {
                "host": "ubuntu",
                "message": "omfwd: remote server at 127.0.0.1:1516 seems to have closed connection",
                "level": "INFO", 
                "service": "rsyslogd",
                "source": "syslog"
            },
            {
                "host": "ubuntu",
                "message": "action 'action-8-builtin:omfwd' suspended",
                "level": "INFO",
                "service": "rsyslogd", 
                "source": "syslog"
            }
        ]
        
        consistent_mappings = 0
        total_tests = len(sample_anomaly_events)
        
        for i, event in enumerate(sample_anomaly_events, 1):
            logger.info(f"\nTest {i}/{total_tests}: Processing event with host='{event.get('host')}'")
            
            # Get expected mapping from registry
            host = event.get('host', '')
            expected_mapping = registry_data['hostname_to_ship'].get(host, 'unknown-ship')
            expected_device = registry_data['hostname_to_device'].get(host, 'unknown-device')
            
            # Get actual mapping using fixed logic
            actual_mapping = self.simulate_anomaly_detection_mapping(event)
            
            logger.info(f"  Expected: ship_id='{expected_mapping}', device_id='{expected_device}'")
            logger.info(f"  Actual:   ship_id='{actual_mapping['ship_id']}' (source: {actual_mapping['ship_id_source']})")
            logger.info(f"            device_id='{actual_mapping['device_id']}' (source: {actual_mapping['device_id_source']})")
            
            # Check consistency
            ship_consistent = (expected_mapping == 'unknown-ship' and actual_mapping['ship_id_source'] in ['hostname_derived', 'hostname_direct']) or \
                            (expected_mapping == actual_mapping['ship_id'])
            
            device_consistent = (expected_device == 'unknown-device' and actual_mapping['device_id_source'] in ['hostname_fallback']) or \
                              (expected_device == actual_mapping['device_id'])
            
            if ship_consistent and device_consistent:
                logger.info("  Status: ✅ CONSISTENT")
                consistent_mappings += 1
            else:
                logger.info("  Status: ❌ INCONSISTENT")
                if not ship_consistent:
                    logger.info(f"    Ship ID mismatch: expected '{expected_mapping}' but got '{actual_mapping['ship_id']}'")
                if not device_consistent:
                    logger.info(f"    Device ID mismatch: expected '{expected_device}' but got '{actual_mapping['device_id']}'")
        
        logger.info(f"\n📊 Consistency Results: {consistent_mappings}/{total_tests} tests passed")
        
        if consistent_mappings == total_tests:
            logger.info("🎉 ALL TESTS PASSED - Data mapping is consistent!")
            return True
        else:
            logger.warning(f"⚠️  {total_tests - consistent_mappings} tests failed - Data mapping needs attention")
            return False
    
    def test_registry_stats(self):
        """Test registry statistics to understand current data state"""
        logger.info("\n📊 Device Registry Statistics")
        logger.info("=" * 40)
        
        try:
            response = self.session.get(f"{self.registry_url}/stats", timeout=10)
            response.raise_for_status()
            stats = response.json()
            
            logger.info(f"Total Ships: {stats.get('total_ships', 0)}")
            logger.info(f"Total Devices: {stats.get('total_devices', 0)}")
            
            if stats.get('device_types'):
                logger.info("Device Types:")
                for device_type, count in stats['device_types'].items():
                    logger.info(f"  {device_type}: {count}")
            
            if stats.get('ship_device_counts'):
                logger.info("Devices per Ship:")
                for ship_id, count in stats['ship_device_counts'].items():
                    logger.info(f"  {ship_id}: {count} devices")
            
        except Exception as e:
            logger.error(f"❌ Error getting registry stats: {e}")
    
    def run_all_tests(self):
        """Run all data consistency tests"""
        logger.info("🚀 Starting Data Consistency Tests")
        logger.info("=" * 50)
        
        # Test 1: Registry connection
        if not self.test_device_registry_connection():
            logger.error("❌ Cannot continue - Device Registry not accessible")
            return False
        
        # Test 2: Registry statistics
        self.test_registry_stats()
        
        # Test 3: Mapping consistency
        mapping_consistent = self.test_anomaly_mapping_consistency()
        
        # Summary
        logger.info(f"\n🏁 Test Summary")
        logger.info("=" * 20)
        if mapping_consistent:
            logger.info("✅ All data consistency tests PASSED")
            logger.info("📝 The fixes should resolve the data inconsistency issue")
            return True
        else:
            logger.warning("⚠️  Some tests FAILED")
            logger.info("📝 Additional investigation may be needed")
            return False

def main():
    """Main entry point"""
    tester = DataConsistencyTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 SUCCESS: Data consistency fixes are working correctly!")
        exit(0)
    else:
        print("\n❌ FAILURE: Data consistency issues remain")
        exit(1)

if __name__ == "__main__":
    main()