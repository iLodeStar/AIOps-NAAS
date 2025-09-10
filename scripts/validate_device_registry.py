#!/usr/bin/env python3
"""
Device Registry Implementation Validation Script
Tests the Device Registry & Mapping Service functionality
"""

import requests
import json
import time
import sys
from datetime import datetime


class DeviceRegistryValidator:
    def __init__(self, registry_url="http://localhost:8081"):
        self.registry_url = registry_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message
        })
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
    
    def test_health_check(self):
        """Test service health endpoint"""
        try:
            response = self.session.get(f"{self.registry_url}/health", timeout=5)
            success = response.status_code == 200
            data = response.json() if success else {}
            message = f"Status: {response.status_code}, Service: {data.get('service', 'N/A')}"
            self.log_test("Health Check", success, message)
            return success
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {e}")
            return False
    
    def test_ship_creation(self):
        """Test ship creation"""
        ship_data = {
            "ship_id": "test-ship-001",
            "name": "Test Ship Aurora",
            "fleet_id": "test-fleet",
            "location": "Test Port",
            "status": "active"
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/ships", json=ship_data)
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                result = response.json()
                message += f", Ship ID: {result.get('ship_id')}"
            self.log_test("Ship Creation", success, message)
            return success
        except Exception as e:
            self.log_test("Ship Creation", False, f"Error: {e}")
            return False
    
    def test_device_registration(self):
        """Test device registration"""
        device_data = {
            "hostname": "test-ubuntu-vm-01",
            "ship_id": "test-ship-001",
            "device_type": "server",
            "vendor": "Dell",
            "model": "PowerEdge R740",
            "location": "Server Room"
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/devices/register", json=device_data)
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                result = response.json()
                message += f", Device ID: {result.get('device_id')}"
            self.log_test("Device Registration", success, message)
            return success
        except Exception as e:
            self.log_test("Device Registration", False, f"Error: {e}")
            return False
    
    def test_hostname_lookup(self):
        """Test hostname lookup"""
        hostname = "test-ubuntu-vm-01"
        try:
            response = self.session.get(f"{self.registry_url}/lookup/{hostname}")
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                result = response.json()
                mapping = result.get('mapping', {})
                message += f", Ship: {mapping.get('ship_id')}, Device: {mapping.get('device_id')}"
            self.log_test("Hostname Lookup", success, message)
            return success
        except Exception as e:
            self.log_test("Hostname Lookup", False, f"Error: {e}")
            return False
    
    def test_ship_listing(self):
        """Test ship listing"""
        try:
            response = self.session.get(f"{self.registry_url}/ships")
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                ships = response.json()
                message += f", Ships found: {len(ships)}"
            self.log_test("Ship Listing", success, message)
            return success
        except Exception as e:
            self.log_test("Ship Listing", False, f"Error: {e}")
            return False
    
    def test_device_listing(self):
        """Test device listing"""
        try:
            response = self.session.get(f"{self.registry_url}/devices")
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                devices = response.json()
                message += f", Devices found: {len(devices)}"
            self.log_test("Device Listing", success, message)
            return success
        except Exception as e:
            self.log_test("Device Listing", False, f"Error: {e}")
            return False
    
    def test_statistics(self):
        """Test statistics endpoint"""
        try:
            response = self.session.get(f"{self.registry_url}/stats")
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            if success:
                stats = response.json()
                message += f", Ships: {stats.get('total_ships')}, Devices: {stats.get('total_devices')}"
            self.log_test("Statistics", success, message)
            return success
        except Exception as e:
            self.log_test("Statistics", False, f"Error: {e}")
            return False
    
    def test_update_last_seen(self):
        """Test last seen timestamp update"""
        hostname = "test-ubuntu-vm-01"
        try:
            response = self.session.post(f"{self.registry_url}/lookup/{hostname}/update-last-seen")
            success = response.status_code == 200
            message = f"Status: {response.status_code}"
            self.log_test("Update Last Seen", success, message)
            return success
        except Exception as e:
            self.log_test("Update Last Seen", False, f"Error: {e}")
            return False
    
    def test_duplicate_hostname_error(self):
        """Test duplicate hostname registration error handling"""
        device_data = {
            "hostname": "test-ubuntu-vm-01",  # Same hostname as before
            "ship_id": "test-ship-001",
            "device_type": "workstation",
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/devices/register", json=device_data)
            success = response.status_code == 400  # Should fail with 400
            message = f"Status: {response.status_code} (expected 400 for duplicate)"
            self.log_test("Duplicate Hostname Error", success, message)
            return success
        except Exception as e:
            self.log_test("Duplicate Hostname Error", False, f"Error: {e}")
            return False
    
    def test_invalid_ship_id_error(self):
        """Test device registration with invalid ship_id"""
        device_data = {
            "hostname": "test-invalid-device",
            "ship_id": "non-existent-ship",
            "device_type": "server",
        }
        
        try:
            response = self.session.post(f"{self.registry_url}/devices/register", json=device_data)
            success = response.status_code == 400  # Should fail with 400
            message = f"Status: {response.status_code} (expected 400 for invalid ship)"
            self.log_test("Invalid Ship ID Error", success, message)
            return success
        except Exception as e:
            self.log_test("Invalid Ship ID Error", False, f"Error: {e}")
            return False
    
    def test_hostname_not_found(self):
        """Test lookup of non-existent hostname"""
        hostname = "non-existent-hostname"
        try:
            response = self.session.get(f"{self.registry_url}/lookup/{hostname}")
            success = response.status_code == 404  # Should fail with 404
            message = f"Status: {response.status_code} (expected 404 for not found)"
            self.log_test("Hostname Not Found", success, message)
            return success
        except Exception as e:
            self.log_test("Hostname Not Found", False, f"Error: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test data (note: this is a simple implementation without delete endpoints)"""
        print("\n🧹 Test data cleanup would require delete endpoints (not implemented in this demo)")
        print("   Test data will persist in the database")
    
    def run_all_tests(self):
        """Run all validation tests"""
        print(f"🧪 Device Registry Validation Tests")
        print(f"Registry URL: {self.registry_url}")
        print(f"Timestamp: {datetime.now()}")
        print("=" * 60)
        
        # Core functionality tests
        tests = [
            self.test_health_check,
            self.test_ship_creation,
            self.test_device_registration,
            self.test_hostname_lookup,
            self.test_ship_listing,
            self.test_device_listing,
            self.test_statistics,
            self.test_update_last_seen,
            self.test_duplicate_hostname_error,
            self.test_invalid_ship_id_error,
            self.test_hostname_not_found,
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
            time.sleep(0.5)  # Brief pause between tests
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results Summary:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed}")
        print(f"   Failed: {total - passed}")
        print(f"   Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("✅ All tests passed! Device Registry is working correctly.")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False
    
    def quick_functional_test(self):
        """Quick test to verify basic functionality"""
        print("🚀 Quick Device Registry Functional Test")
        print("=" * 50)
        
        # Test service availability
        if not self.test_health_check():
            print("❌ Service is not available. Is the device-registry container running?")
            return False
        
        # Create test ship
        print("\n1. Creating test ship...")
        if not self.test_ship_creation():
            print("❌ Failed to create ship")
            return False
        
        # Register test device
        print("2. Registering test device...")
        if not self.test_device_registration():
            print("❌ Failed to register device")
            return False
        
        # Test hostname lookup
        print("3. Testing hostname lookup...")
        if not self.test_hostname_lookup():
            print("❌ Failed to lookup hostname")
            return False
        
        print("\n✅ Quick functional test passed! Device Registry is working.")
        return True


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Device Registry Validation Script")
    parser.add_argument(
        '--registry-url', 
        default='http://localhost:8081',
        help='Device Registry service URL (default: http://localhost:8081)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick functional test instead of full test suite'
    )
    
    args = parser.parse_args()
    
    validator = DeviceRegistryValidator(args.registry_url)
    
    try:
        if args.quick:
            success = validator.quick_functional_test()
        else:
            success = validator.run_all_tests()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()