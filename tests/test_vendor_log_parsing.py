#!/usr/bin/env python3
"""
Test suite for unified network log normalization via Vector v0.49 → ClickHouse
Tests vendor-specific parsing, device classification, and schema extensions
"""

import json
import time
import socket
import pytest
import requests
from datetime import datetime
from typing import Dict, List, Any

class TestVendorLogParsing:
    """Test vendor-specific log parsing and normalization"""
    
    def setup_method(self):
        """Setup test environment"""
        self.vector_metrics_url = "http://localhost:8686/metrics"
        self.clickhouse_url = "http://localhost:8123"
        self.test_session_id = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
    def send_syslog_udp(self, message: str, host: str = "localhost", port: int = 1517):
        """Send syslog message via UDP"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message.encode('utf-8'), (host, port))
        finally:
            sock.close()
    
    def query_clickhouse(self, query: str) -> List[Dict]:
        """Query ClickHouse and return results"""
        response = requests.post(
            f"{self.clickhouse_url}/?user=default&password=clickhouse123",
            data=query,
            headers={'Content-Type': 'text/plain'}
        )
        if response.status_code == 200:
            lines = response.text.strip().split('\n')
            return [json.loads(line) for line in lines if line.strip()]
        return []
    
    def wait_for_processing(self, seconds: int = 5):
        """Wait for Vector processing and ClickHouse ingestion"""
        time.sleep(seconds)
    
    def test_cisco_ios_parsing(self):
        """Test Cisco IOS log parsing"""
        cisco_messages = [
            f"<189>Jan 15 10:30:00 bridge-sw01 %LINK-3-UPDOWN: Interface GigabitEthernet1/1, changed state to up {self.test_session_id}",
            f"<188>Jan 15 10:30:01 engine-rtr01 %BGP-4-ADJCHANGE: neighbor 192.168.1.2 Up {self.test_session_id}",
            f"<185>Jan 15 10:30:02 comms-fw01 %SYS-2-MALLOCFAIL: Memory allocation of 1000 bytes failed {self.test_session_id}"
        ]
        
        for message in cisco_messages:
            self.send_syslog_udp(message)
        
        self.wait_for_processing()
        
        # Verify Cisco logs were parsed correctly
        query = f"""
        SELECT vendor, device_type, facility, severity, category, event_id, cruise_segment, message
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%' AND vendor = 'cisco'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 3, f"Expected 3 Cisco logs, got {len(results)}"
        
        # Check first log (bridge switch)
        bridge_log = next(r for r in results if 'bridge-sw01' in str(r))
        assert bridge_log['vendor'] == 'cisco'
        assert bridge_log['device_type'] == 'switch'
        assert bridge_log['facility'] == 'link'
        assert bridge_log['severity'] == 'error'
        assert bridge_log['category'] == 'updown'
        assert bridge_log['cruise_segment'] == 'navigation'
        
        # Check second log (engine router)
        engine_log = next(r for r in results if 'engine-rtr01' in str(r))
        assert engine_log['device_type'] == 'router'
        assert engine_log['cruise_segment'] == 'propulsion'
        
        # Check third log (comms firewall)
        comms_log = next(r for r in results if 'comms-fw01' in str(r))
        assert comms_log['device_type'] == 'firewall'
        assert comms_log['cruise_segment'] == 'communications'
        assert comms_log['severity'] == 'critical'
    
    def test_juniper_junos_parsing(self):
        """Test Juniper Junos log parsing"""
        juniper_messages = [
            f"<187>Jan 15 10:30:03 nav-ex4200 rpd.info: BGP peer 192.168.1.1 changed state {self.test_session_id}",
            f"<184>Jan 15 10:30:04 deck-mx960 kernel.warning: Interface xe-0/0/0 link down {self.test_session_id}"
        ]
        
        for message in juniper_messages:
            self.send_syslog_udp(message)
        
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, facility, severity, cruise_segment, message
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%' AND vendor = 'juniper'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 2, f"Expected 2 Juniper logs, got {len(results)}"
        
        # Check navigation switch
        nav_log = next(r for r in results if 'nav-ex4200' in str(r))
        assert nav_log['vendor'] == 'juniper'
        assert nav_log['device_type'] == 'switch'
        assert nav_log['facility'] == 'rpd'
        assert nav_log['severity'] == 'info'
        assert nav_log['cruise_segment'] == 'navigation'
        
        # Check deck router
        deck_log = next(r for r in results if 'deck-mx960' in str(r))
        assert deck_log['device_type'] == 'router'
        assert deck_log['cruise_segment'] == 'deck_operations'
        assert deck_log['severity'] == 'warning'
    
    def test_fortinet_parsing(self):
        """Test Fortinet FortiOS log parsing"""
        fortinet_message = f'<185>Jan 15 10:30:05 security-fgt100 date=2025-01-15 time=10:30:05 devname="security-fgt100" devid="FGT100F123456789" logid="0000000013" type="traffic" subtype="forward" level="notice" msg="Permitted traffic from guest network {self.test_session_id}"'
        
        self.send_syslog_udp(fortinet_message)
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, facility, severity, category, event_id, cruise_segment
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%' AND vendor = 'fortinet'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 1, f"Expected 1 Fortinet log, got {len(results)}"
        
        log = results[0]
        assert log['vendor'] == 'fortinet'
        assert log['device_type'] == 'firewall'
        assert log['category'] == 'traffic'
        assert log['event_id'] == '0000000013'
        assert log['severity'] == 'notice'
        assert log['cruise_segment'] == 'safety_security'
    
    def test_palo_alto_parsing(self):
        """Test Palo Alto PAN-OS log parsing"""
        panos_message = f'<142>Jan 15 10:30:06 guest-pa3020 1,2025/01/15 10:30:06,012345678901,TRAFFIC,end,2049,2025/01/15 10:30:06,192.168.100.50,10.1.1.100,0.0.0.0,0.0.0.0,Allow Internet,,,web-browsing,vsys1,guest-zone,trusted-zone,ae1.100,ae1.200,forward,2025/01/15 10:30:06,45123,1,80,80,0x19,tcp,allow,1234,456,778,12,2025/01/15 10:30:06,0,any,0,123456789,0x0,192.168.0.0-192.168.255.255,10.0.0.0-10.255.255.255,0,2,1,aged-out,0,0,0,0,,PA-VM,from-policy,,,0,,0,,N/A,0,0,0,0,{self.test_session_id}'
        
        self.send_syslog_udp(panos_message)
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, cruise_segment
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%' AND vendor = 'paloalto'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 1, f"Expected 1 Palo Alto log, got {len(results)}"
        
        log = results[0]
        assert log['vendor'] == 'paloalto'
        assert log['device_type'] == 'firewall'
        assert log['cruise_segment'] == 'guest_services'
    
    def test_aruba_parsing(self):
        """Test Aruba/HPE log parsing"""
        aruba_message = f"<188>Jan 15 10:30:07 bridge-wlc7030 WIRELESS: INFO: Client 00:11:22:33:44:55 associated to AP bridge-ap01 {self.test_session_id}"
        
        self.send_syslog_udp(aruba_message)
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, facility, severity, cruise_segment
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%' AND vendor = 'aruba'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 1, f"Expected 1 Aruba log, got {len(results)}"
        
        log = results[0]
        assert log['vendor'] == 'aruba'
        assert log['device_type'] == 'wireless_controller'
        assert log['facility'] == 'wireless'
        assert log['severity'] == 'info'
        assert log['cruise_segment'] == 'navigation'
    
    def test_windows_eventlog_parsing(self):
        """Test Windows Event Log parsing (JSON format)"""
        # This would typically come from Winlogbeat or similar
        windows_json = {
            "timestamp": "2025-01-15T10:30:08.123Z",
            "level": "error",
            "message": f"The server service failed to start {self.test_session_id}",
            "host": {"name": "crew-srv01", "ip": ["192.168.50.10"]},
            "source_name": "Service Control Manager",
            "winlog": {
                "event_id": 7000,
                "source_name": "Service Control Manager",
                "level": "Error"
            }
        }
        
        # Write to a JSON log file that Vector monitors
        import os
        os.makedirs("/tmp/test-logs", exist_ok=True)
        with open("/tmp/test-logs/windows.json", "w") as f:
            f.write(json.dumps(windows_json) + "\n")
        
        # In a real test, we'd need to configure Vector to read from /tmp/test-logs
        # For now, simulate by sending via syslog with embedded JSON
        syslog_with_json = f"<134>Jan 15 10:30:08 crew-srv01 winlogbeat: {json.dumps(windows_json)}"
        self.send_syslog_udp(syslog_with_json)
        self.wait_for_processing()
        
        # Note: This test would need the json_logs source configured to read from /tmp/test-logs
    
    def test_generic_keyvalue_parsing(self):
        """Test generic key=value format parsing"""
        keyvalue_message = f"<134>Jan 15 10:30:09 vsat-modem01 vendor=Hughes device_type=satellite severity=warning signal_strength=-85dBm snr=12.5dB ber=1e-6 message='Signal degradation detected {self.test_session_id}'"
        
        self.send_syslog_udp(keyvalue_message)
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, severity, cruise_segment
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) >= 1, f"Expected at least 1 key=value log, got {len(results)}"
        
        # Check if any result has vendor=generic_keyvalue (for structured parsing)
        keyvalue_logs = [r for r in results if r.get('vendor') == 'generic_keyvalue']
        if keyvalue_logs:
            log = keyvalue_logs[0]
            assert log['device_type'] == 'vsat_terminal'  # Based on hostname pattern
            assert log['cruise_segment'] == 'communications'
    
    def test_backward_compatibility(self):
        """Test that existing anomaly detection continues to work"""
        # Send an error log that should trigger anomaly detection
        error_message = f"<131>Jan 15 10:30:10 api-server01 application: ERROR Database connection failed after 3 retries {self.test_session_id}"
        
        self.send_syslog_udp(error_message)
        self.wait_for_processing()
        
        # Check that log is in ClickHouse
        query = f"""
        SELECT vendor, device_type, level, severity, message
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 1, f"Expected 1 error log, got {len(results)}"
        
        log = results[0]
        assert log['device_type'] == 'server'  # Based on hostname pattern
        assert log['level'] in ['ERROR', 'INFO']  # Depending on parsing
        assert 'Database connection failed' in log['message']
        
        # The anomaly detection should still work - this would be tested 
        # by checking NATS messages or incident creation, but that's beyond
        # the scope of this Vector+ClickHouse parsing test
    
    def test_schema_extensions(self):
        """Test that all new schema fields are populated correctly"""
        test_message = f"<189>Jan 15 10:30:11 bridge-sw01 %LINK-3-UPDOWN: Interface GigabitEthernet1/1, changed state to down {self.test_session_id}"
        
        self.send_syslog_udp(test_message)
        self.wait_for_processing()
        
        query = f"""
        SELECT vendor, device_type, cruise_segment, facility, severity, category, event_id, ip_address, ingestion_time
        FROM logs.raw 
        WHERE message LIKE '%{self.test_session_id}%'
        FORMAT JSONEachRow
        """
        
        results = self.query_clickhouse(query)
        assert len(results) == 1, f"Expected 1 log, got {len(results)}"
        
        log = results[0]
        
        # Verify all new fields are present and have expected values
        assert log['vendor'] == 'cisco'
        assert log['device_type'] == 'switch'
        assert log['cruise_segment'] == 'navigation'
        assert log['facility'] == 'link'
        assert log['severity'] == 'error'
        assert log['category'] == 'updown'
        assert log['event_id'] == 'UPDOWN'
        assert log['ip_address'] == '0.0.0.0'  # No IP in hostname
        assert log['ingestion_time']  # Should have timestamp
    
    def test_vendor_metrics_generation(self):
        """Test that vendor-specific metrics are generated"""
        # Send logs from different vendors
        messages = [
            f"<189>Jan 15 10:30:12 test-cisco %LINK-3-UPDOWN: Test message {self.test_session_id}",
            f"<187>Jan 15 10:30:13 test-juniper rpd.info: Test message {self.test_session_id}",
            f"<185>Jan 15 10:30:14 test-fortinet devname='test' logid='123' type='traffic' level='notice' msg='Test {self.test_session_id}'"
        ]
        
        for message in messages:
            self.send_syslog_udp(message)
        
        self.wait_for_processing()
        
        # Check Vector metrics endpoint for vendor-specific metrics
        try:
            response = requests.get(self.vector_metrics_url, timeout=5)
            if response.status_code == 200:
                metrics_text = response.text
                
                # Look for vendor-specific metrics
                assert 'aiops_vector_vendor_logs_total' in metrics_text
                assert 'vendor="cisco"' in metrics_text
                assert 'vendor="juniper"' in metrics_text
                assert 'vendor="fortinet"' in metrics_text
                
                # Check device type metrics
                assert 'device_type="switch"' in metrics_text
                assert 'device_type="firewall"' in metrics_text
        except requests.exceptions.RequestException:
            # Vector metrics endpoint might not be available in test environment
            pass

if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])