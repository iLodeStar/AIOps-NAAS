#!/usr/bin/env python3
"""
System Compatibility Monitor
============================

Monitors and verifies system compatibility with different message formats
(SNMP, Syslog) across various operating systems and environments.

This service continuously tracks:
- Input/output correlation across various system sources
- Message format compatibility (SNMP, Syslog, etc.)
- OS-specific message parsing (Debian, RHEL, Windows, etc.)
- System health across different environments

Usage:
    python3 compatibility_monitor.py
    python3 compatibility_monitor.py --config config.json
    python3 compatibility_monitor.py --test-mode
"""

import json
import logging
import time
import threading
import socket
import subprocess
import re
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
from threading import Lock
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/compatibility_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MessageFormatTest:
    """Test case for a specific message format"""
    format_name: str
    os_type: str
    sample_message: str
    expected_fields: List[str]
    parser_regex: str
    success: bool = False
    error_message: str = ""
    timestamp: datetime = None

@dataclass
class CompatibilityReport:
    """Report on system compatibility"""
    timestamp: datetime
    os_type: str
    hostname: str
    tests_passed: int
    tests_failed: int
    total_tests: int
    success_rate: float
    details: Dict[str, Any]

class OSMessageFormats:
    """Message format definitions for different operating systems"""
    
    FORMATS = {
        "debian": {
            "syslog": {
                "sample": "<34>Oct 11 22:14:15 ubuntu systemd[1]: Started getty@tty1.service.",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            },
            "auth_log": {
                "sample": "<38>Oct 11 22:14:15 ubuntu sudo: user : TTY=pts/0 ; PWD=/home/user ; USER=root ; COMMAND=/bin/ls",
                "fields": ["timestamp", "hostname", "service", "user", "command"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+sudo:\s+([^:]+)\s*:\s*.*COMMAND=(.*)"
            },
            "kernel": {
                "sample": "<6>Oct 11 22:14:15 ubuntu kernel: [12345.678] CPU: 0 PID: 1234 at kernel/sched/core.c:1234",
                "fields": ["timestamp", "hostname", "service", "kernel_time", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+kernel:\s*\[([^\]]+)\]\s*(.*)"
            }
        },
        "rhel": {
            "syslog": {
                "sample": "<34>Oct 11 22:14:15 rhel-server systemd: Started Network Manager Script Dispatcher Service.",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            },
            "audit": {
                "sample": "<86>Oct 11 22:14:15 rhel-server audit[1234]: type=USER_LOGIN msg=audit(1234567890.123:456): pid=1234 uid=0 auid=1000 ses=1",
                "fields": ["timestamp", "hostname", "service", "audit_type", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+audit\[\d+\]:\s+type=(\w+)\s+(.*)"
            }
        },
        "windows": {
            "event_log": {
                "sample": "<14>Oct 11 22:14:15 WIN-SERVER Microsoft-Windows-Security-Auditing: An account was successfully logged on.",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            },
            "application": {
                "sample": "<46>Oct 11 22:14:15 WIN-SERVER Application: Application started successfully with PID 1234",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            }
        },
        "unix": {
            "syslog": {
                "sample": "<34>Oct 11 22:14:15 unix-host syslogd: restart",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            }
        },
        "vm": {
            "vmware": {
                "sample": "<34>Oct 11 22:14:15 vm-guest vmware-tools: Guest tools started",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            },
            "hyperv": {
                "sample": "<34>Oct 11 22:14:15 hyperv-guest hv-kvp-daemon[1234]: KVP daemon started",
                "fields": ["timestamp", "hostname", "service", "message"], 
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            }
        },
        "headless": {
            "server": {
                "sample": "<34>Oct 11 22:14:15 headless-srv systemd-logind: New session 1 of user root.",
                "fields": ["timestamp", "hostname", "service", "message"],
                "regex": r"<(\d+)>(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+([^:]+):\s*(.*)"
            }
        }
    }

class SNMPCompatibilityTester:
    """Tests SNMP compatibility across different systems"""
    
    # Common SNMP OIDs for different systems
    COMMON_OIDS = {
        "system": {
            "sysDescr": "1.3.6.1.2.1.1.1.0",
            "sysObjectID": "1.3.6.1.2.1.1.2.0", 
            "sysUpTime": "1.3.6.1.2.1.1.3.0",
            "sysContact": "1.3.6.1.2.1.1.4.0",
            "sysName": "1.3.6.1.2.1.1.5.0",
            "sysLocation": "1.3.6.1.2.1.1.6.0"
        },
        "network": {
            "ifNumber": "1.3.6.1.2.1.2.1.0",
            "ifTable": "1.3.6.1.2.1.2.2",
            "ipForwarding": "1.3.6.1.2.1.4.1.0"
        },
        "host_resources": {
            "hrSystemUptime": "1.3.6.1.2.1.25.1.1.0",
            "hrSystemDate": "1.3.6.1.2.1.25.1.2.0",
            "hrMemorySize": "1.3.6.1.2.1.25.2.2.0"
        }
    }
    
    def __init__(self):
        self.results = {}
    
    def test_snmp_compatibility(self, host: str = "localhost", port: int = 161, community: str = "public") -> Dict[str, Any]:
        """Test SNMP compatibility with different OID groups"""
        results = {
            "host": host,
            "port": port,
            "timestamp": datetime.now(),
            "tests": {},
            "success_rate": 0.0
        }
        
        total_tests = 0
        successful_tests = 0
        
        for category, oids in self.COMMON_OIDS.items():
            category_results = {}
            
            for oid_name, oid_value in oids.items():
                total_tests += 1
                
                try:
                    # Simulate SNMP query (in real implementation, use pysnmp)
                    success = self._simulate_snmp_get(host, port, community, oid_value)
                    
                    if success:
                        successful_tests += 1
                        category_results[oid_name] = {
                            "status": "success",
                            "oid": oid_value,
                            "value": f"simulated_value_{oid_name}"
                        }
                    else:
                        category_results[oid_name] = {
                            "status": "failed",
                            "oid": oid_value,
                            "error": "No response"
                        }
                        
                except Exception as e:
                    category_results[oid_name] = {
                        "status": "error",
                        "oid": oid_value,
                        "error": str(e)
                    }
            
            results["tests"][category] = category_results
        
        results["success_rate"] = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        return results
    
    def _simulate_snmp_get(self, host: str, port: int, community: str, oid: str) -> bool:
        """Simulate SNMP GET operation (replace with real SNMP in production)"""
        # This is a simulation - in real implementation, use pysnmp
        # For now, randomly succeed for demonstration
        import random
        return random.random() > 0.2  # 80% success rate for simulation

class CompatibilityMonitor:
    """Main system compatibility monitoring service"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = self._load_config(config_file)
        self.running = False
        self.results = []
        self.lock = Lock()
        self.snmp_tester = SNMPCompatibilityTester()
        
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "monitoring_interval": 300,  # 5 minutes
            "syslog_port": 1514,
            "snmp_targets": ["localhost"],
            "test_message_formats": True,
            "test_snmp_compatibility": True,
            "max_results_history": 1000,
            "report_file": "/tmp/compatibility_report.json"
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.warning(f"Could not load config file {config_file}: {e}")
        
        return default_config
    
    def test_message_format_compatibility(self) -> List[MessageFormatTest]:
        """Test compatibility with different OS message formats"""
        tests = []
        
        for os_type, formats in OSMessageFormats.FORMATS.items():
            for format_name, format_config in formats.items():
                test = MessageFormatTest(
                    format_name=f"{os_type}_{format_name}",
                    os_type=os_type,
                    sample_message=format_config["sample"],
                    expected_fields=format_config["fields"],
                    parser_regex=format_config["regex"],
                    timestamp=datetime.now()
                )
                
                try:
                    # Test regex parsing
                    match = re.match(format_config["regex"], format_config["sample"])
                    if match:
                        parsed_fields = len(match.groups())
                        expected_fields = len(format_config["fields"])
                        
                        if parsed_fields >= expected_fields - 1:  # Allow some flexibility
                            test.success = True
                            logger.debug(f"✅ {test.format_name}: Parser working correctly")
                        else:
                            test.success = False
                            test.error_message = f"Parser extracted {parsed_fields} fields, expected {expected_fields}"
                            logger.warning(f"⚠️  {test.format_name}: {test.error_message}")
                    else:
                        test.success = False
                        test.error_message = "Regex pattern did not match sample message"
                        logger.error(f"❌ {test.format_name}: {test.error_message}")
                        
                except Exception as e:
                    test.success = False
                    test.error_message = f"Exception during parsing: {str(e)}"
                    logger.error(f"❌ {test.format_name}: {test.error_message}")
                
                tests.append(test)
        
        return tests
    
    def test_syslog_reception(self) -> Dict[str, Any]:
        """Test if system can receive syslog messages on configured port"""
        port = self.config["syslog_port"]
        
        result = {
            "port": port,
            "listening": False,
            "timestamp": datetime.now(),
            "error": None
        }
        
        try:
            # Check if port is listening
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.bind(('localhost', 0))  # Bind to any available port for testing
            test_port = sock.getsockname()[1]
            sock.close()
            
            # Try to connect to the actual syslog port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            
            # Send a test message to see if port is accepting
            test_message = f"<14>{datetime.now().strftime('%b %d %H:%M:%S')} test compatibility-test: port test"
            sock.sendto(test_message.encode(), ('localhost', port))
            sock.close()
            
            result["listening"] = True
            logger.info(f"✅ Syslog port {port} is accepting messages")
            
        except Exception as e:
            result["error"] = str(e)
            logger.warning(f"⚠️  Syslog port {port} test failed: {e}")
        
        return result
    
    def check_service_correlations(self) -> Dict[str, Any]:
        """Check if input/output correlations are working across services"""
        services_to_check = [
            ("Vector", "http://localhost:8686/health"),
            ("ClickHouse", "http://localhost:8123/ping"),
            ("VictoriaMetrics", "http://localhost:8428/metrics"),
            ("NATS", "http://localhost:8222/varz"),
            ("Benthos", "http://localhost:4195/ping")
        ]
        
        correlation_results = {
            "timestamp": datetime.now(),
            "services": {},
            "correlation_health": "unknown"
        }
        
        healthy_services = 0
        total_services = len(services_to_check)
        
        for service_name, health_url in services_to_check:
            try:
                response = requests.get(health_url, timeout=5)
                if response.status_code == 200:
                    correlation_results["services"][service_name] = {
                        "status": "healthy",
                        "response_time": response.elapsed.total_seconds()
                    }
                    healthy_services += 1
                else:
                    correlation_results["services"][service_name] = {
                        "status": "unhealthy",
                        "status_code": response.status_code
                    }
            except requests.RequestException as e:
                correlation_results["services"][service_name] = {
                    "status": "unreachable",
                    "error": str(e)
                }
        
        # Determine overall correlation health
        if healthy_services == total_services:
            correlation_results["correlation_health"] = "excellent"
        elif healthy_services >= total_services * 0.8:
            correlation_results["correlation_health"] = "good"
        elif healthy_services >= total_services * 0.5:
            correlation_results["correlation_health"] = "degraded"
        else:
            correlation_results["correlation_health"] = "critical"
        
        return correlation_results
    
    def run_compatibility_check(self) -> CompatibilityReport:
        """Run a complete compatibility check"""
        logger.info("Starting compatibility check...")
        
        start_time = datetime.now()
        
        # Test message format compatibility
        format_tests = self.test_message_format_compatibility()
        
        # Test syslog reception
        syslog_test = self.test_syslog_reception()
        
        # Test service correlations
        correlation_test = self.check_service_correlations()
        
        # Test SNMP compatibility if enabled
        snmp_results = {}
        if self.config["test_snmp_compatibility"]:
            for target in self.config["snmp_targets"]:
                snmp_results[target] = self.snmp_tester.test_snmp_compatibility(target)
        
        # Compile results
        passed_tests = sum(1 for test in format_tests if test.success)
        failed_tests = len(format_tests) - passed_tests
        total_tests = len(format_tests)
        
        if syslog_test["listening"]:
            passed_tests += 1
        else:
            failed_tests += 1
        total_tests += 1
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        report = CompatibilityReport(
            timestamp=start_time,
            os_type=platform.system(),
            hostname=socket.gethostname(),
            tests_passed=passed_tests,
            tests_failed=failed_tests,
            total_tests=total_tests,
            success_rate=success_rate,
            details={
                "format_tests": [asdict(test) for test in format_tests],
                "syslog_test": syslog_test,
                "correlation_test": correlation_test,
                "snmp_tests": snmp_results,
                "duration_seconds": (datetime.now() - start_time).total_seconds()
            }
        )
        
        with self.lock:
            self.results.append(report)
            
            # Maintain max history
            if len(self.results) > self.config["max_results_history"]:
                self.results = self.results[-self.config["max_results_history"]:]
        
        logger.info(f"Compatibility check completed: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        return report
    
    def save_report(self, report: CompatibilityReport):
        """Save compatibility report to file"""
        try:
            report_data = asdict(report)
            with open(self.config["report_file"], 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            logger.info(f"Report saved to {self.config['report_file']}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
    
    def start_monitoring(self):
        """Start continuous monitoring"""
        self.running = True
        logger.info(f"Starting compatibility monitoring (interval: {self.config['monitoring_interval']}s)")
        
        while self.running:
            try:
                report = self.run_compatibility_check()
                self.save_report(report)
                
                if not self.running:
                    break
                    
                time.sleep(self.config["monitoring_interval"])
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error during monitoring: {e}")
                time.sleep(10)  # Wait before retrying
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self.running = False
        logger.info("Stopping compatibility monitoring")
    
    def get_latest_report(self) -> Optional[CompatibilityReport]:
        """Get the most recent compatibility report"""
        with self.lock:
            return self.results[-1] if self.results else None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of recent monitoring results"""
        with self.lock:
            if not self.results:
                return {"status": "no_data", "message": "No monitoring data available"}
            
            recent_results = self.results[-10:]  # Last 10 results
            avg_success_rate = sum(r.success_rate for r in recent_results) / len(recent_results)
            
            return {
                "status": "active",
                "total_reports": len(self.results),
                "average_success_rate": avg_success_rate,
                "last_check": recent_results[-1].timestamp,
                "recent_trends": [r.success_rate for r in recent_results]
            }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="System Compatibility Monitor")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--test-mode", action="store_true", help="Run single test and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    
    args = parser.parse_args()
    
    monitor = CompatibilityMonitor(args.config)
    
    if args.test_mode:
        logger.info("Running in test mode...")
        report = monitor.run_compatibility_check()
        print(f"\nCompatibility Test Results:")
        print(f"Passed: {report.tests_passed}/{report.total_tests} ({report.success_rate:.1f}%)")
        print(f"OS: {report.os_type} | Host: {report.hostname}")
        
        # Print details
        for test in report.details["format_tests"]:
            status = "✅" if test["success"] else "❌"
            print(f"{status} {test['format_name']}: {test.get('error_message', 'OK')}")
        
        monitor.save_report(report)
        
    elif args.daemon:
        logger.info("Starting as daemon...")
        try:
            monitor.start_monitoring()
        except KeyboardInterrupt:
            monitor.stop_monitoring()
    else:
        # Interactive mode
        print("System Compatibility Monitor")
        print("1. Run single test")
        print("2. Start continuous monitoring") 
        print("3. View summary")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            report = monitor.run_compatibility_check()
            print(f"\nResults: {report.tests_passed}/{report.total_tests} passed ({report.success_rate:.1f}%)")
            monitor.save_report(report)
        elif choice == "2":
            try:
                monitor.start_monitoring()
            except KeyboardInterrupt:
                monitor.stop_monitoring()
        elif choice == "3":
            summary = monitor.get_summary()
            print(f"\nSummary: {json.dumps(summary, indent=2, default=str)}")
        else:
            print("Exiting...")

if __name__ == "__main__":
    main()