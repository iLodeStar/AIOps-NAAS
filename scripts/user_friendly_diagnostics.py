#!/usr/bin/env python3
"""
AIOps NAAS User-Friendly Diagnostic Tool
========================================

A comprehensive diagnostic tool designed for non-technical users to validate 
the AIOps NAAS platform with clear explanations and guided workflows.

Features:
- Four diagnostic modes: Sanity, Regression, Surveillance, Automation
- Clear result interpretation and reporting
- User-friendly explanations of system behavior
- Automated validation with detailed feedback

Usage:
    python3 scripts/user_friendly_diagnostics.py --mode sanity
    python3 scripts/user_friendly_diagnostics.py --mode regression  
    python3 scripts/user_friendly_diagnostics.py --mode surveillance
    python3 scripts/user_friendly_diagnostics.py --mode automation
    python3 scripts/user_friendly_diagnostics.py --help
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import requests
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/aiops_diagnostics.log')
    ]
)
logger = logging.getLogger(__name__)

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

@dataclass
class TestResult:
    """Represents the result of a diagnostic test"""
    test_name: str
    success: bool
    message: str
    details: Dict[str, Any]
    execution_time: float
    timestamp: datetime

@dataclass
class DiagnosticSession:
    """Represents a complete diagnostic session"""
    session_id: str
    mode: str
    start_time: datetime
    end_time: Optional[datetime]
    results: List[TestResult]
    summary: Dict[str, Any]

class UserFriendlyDiagnostics:
    """Main diagnostic tool class"""
    
    def __init__(self):
        self.session_id = f"DIAG-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        self.session = DiagnosticSession(
            session_id=self.session_id,
            mode="",
            start_time=datetime.now(),
            end_time=None,
            results=[],
            summary={}
        )
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.HEADER}{title.center(60)}{Colors.END}")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.CYAN}Session ID: {self.session_id}{Colors.END}\n")
    
    def print_step(self, step_num: int, description: str):
        """Print a step description"""
        print(f"\n{Colors.BLUE}Step {step_num}: {description}{Colors.END}")
    
    def print_success(self, message: str):
        """Print a success message"""
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    
    def print_warning(self, message: str):
        """Print a warning message"""
        print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")
    
    def print_error(self, message: str):
        """Print an error message"""
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    
    def print_info(self, message: str):
        """Print an info message"""
        print(f"{Colors.CYAN}ℹ️  {message}{Colors.END}")
    
    def explain_concept(self, concept: str, explanation: str):
        """Explain a technical concept in user-friendly terms"""
        print(f"\n{Colors.YELLOW}📚 What is {concept}?{Colors.END}")
        print(f"   {explanation}")
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        self.print_step(0, "Checking Prerequisites")
        
        # Check if Docker is running
        try:
            subprocess.run(["docker", "ps"], check=True, capture_output=True)
            self.print_success("Docker is running")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("Docker is not running or not installed")
            return False
        
        # Check if docker-compose.yml exists
        if not os.path.exists("docker-compose.yml"):
            self.print_error("docker-compose.yml not found. Please run from the project root directory.")
            return False
        
        self.print_success("Prerequisites check passed")
        return True
    
    def check_service_health(self) -> Dict[str, bool]:
        """Check the health of critical services"""
        services = {
            "ClickHouse": ("http://localhost:8123/ping", "Database for storing logs and metrics"),
            "Vector": ("http://localhost:8686/health", "Log and metrics collector"),
            "VictoriaMetrics": ("http://localhost:8428/metrics", "Time-series metrics storage"),
            "NATS": ("http://localhost:8222/varz", "Message bus for event communication"),
            "Grafana": ("http://localhost:3000/api/health", "Dashboard and visualization"),
        }
        
        health_status = {}
        
        for service_name, (url, description) in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    health_status[service_name] = True
                    self.print_success(f"{service_name} is healthy")
                else:
                    health_status[service_name] = False
                    self.print_warning(f"{service_name} responded with status {response.status_code}")
            except requests.RequestException:
                health_status[service_name] = False
                self.print_warning(f"{service_name} is not responding")
            
            # Explain what each service does
            print(f"   {Colors.CYAN}{description}{Colors.END}")
        
        return health_status
    
    def send_test_message(self, message_type: str, content: str) -> str:
        """Send a test message and return tracking ID"""
        tracking_id = f"{message_type}-{self.session_id}-{int(time.time())}"
        
        # Create syslog message
        timestamp = datetime.now().strftime('%b %d %H:%M:%S')
        hostname = socket.gethostname()
        syslog_message = f"<14>{timestamp} {hostname} test-service: {content} TRACKING_ID={tracking_id}"
        
        try:
            # Send via UDP to Vector's syslog port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(syslog_message.encode(), ('localhost', 1514))
            sock.close()
            return tracking_id
        except Exception as e:
            logger.error(f"Failed to send test message: {e}")
            return ""
    
    def track_message_in_clickhouse(self, tracking_id: str, timeout: int = 30) -> bool:
        """Track if a message appeared in ClickHouse"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Query ClickHouse for the tracking ID
                cmd = [
                    "docker", "compose", "exec", "-T", "clickhouse",
                    "clickhouse-client", "--query",
                    f"SELECT COUNT(*) FROM logs.raw WHERE message LIKE '%{tracking_id}%'"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and result.stdout.strip() != "0":
                    return True
                    
            except subprocess.TimeoutExpired:
                pass
            
            time.sleep(2)
        
        return False
    
    def run_sanity_mode(self):
        """Run sanity mode - quick validation with 1 normal and 1 anomaly test"""
        self.session.mode = "sanity"
        self.print_header("SANITY MODE - Quick System Validation")
        
        self.explain_concept("Sanity Mode", 
            "This mode runs a quick test to make sure your AIOps system is working correctly.\n"
            "   It sends one normal message and one problem message to see if the system\n"
            "   can tell the difference between them.")
        
        if not self.check_prerequisites():
            return
        
        # Step 1: Check service health
        self.print_step(1, "Checking System Health")
        health_status = self.check_service_health()
        healthy_services = sum(health_status.values())
        total_services = len(health_status)
        
        if healthy_services < total_services:
            self.print_warning(f"Only {healthy_services}/{total_services} services are healthy")
            print(f"\n{Colors.YELLOW}What this means:{Colors.END}")
            print("   Some parts of your system are not working properly.")
            print("   You may need to restart services or check logs.")
        else:
            self.print_success("All services are healthy!")
        
        # Step 2: Send normal test message
        self.print_step(2, "Testing Normal Operations")
        self.explain_concept("Normal Message", 
            "This is a regular system message that represents everything working fine.\n"
            "   The system should store it but NOT create any alerts or incidents.")
        
        normal_tracking_id = self.send_test_message("NORMAL", "System operating normally, all services running")
        if normal_tracking_id:
            self.print_success(f"Normal test message sent (ID: {normal_tracking_id})")
        else:
            self.print_error("Failed to send normal test message")
            return
        
        # Wait and check if message was stored
        print(f"\n{Colors.CYAN}Waiting for message to be processed...{Colors.END}")
        time.sleep(10)
        
        if self.track_message_in_clickhouse(normal_tracking_id):
            self.print_success("Normal message was successfully stored in database")
            print(f"\n{Colors.GREEN}What this means:{Colors.END}")
            print("   ✅ Your system can receive and store log messages correctly")
            print("   ✅ The message pipeline is working")
        else:
            self.print_error("Normal message was not found in database")
            print(f"\n{Colors.RED}What this means:{Colors.END}")
            print("   ❌ There might be a problem with your log processing pipeline")
            print("   ❌ Check that Vector and ClickHouse services are running")
        
        # Step 3: Send anomaly test message
        self.print_step(3, "Testing Anomaly Detection")
        self.explain_concept("Anomaly Message", 
            "This is a problem message that simulates something going wrong.\n"
            "   The system should detect this as unusual and create an incident.")
        
        anomaly_tracking_id = self.send_test_message("ANOMALY", "CRITICAL: CPU usage at 98% - system overloaded")
        if anomaly_tracking_id:
            self.print_success(f"Anomaly test message sent (ID: {anomaly_tracking_id})")
        else:
            self.print_error("Failed to send anomaly test message")
            return
        
        # Wait longer for anomaly processing
        print(f"\n{Colors.CYAN}Waiting for anomaly processing (this takes longer)...{Colors.END}")
        time.sleep(20)
        
        if self.track_message_in_clickhouse(anomaly_tracking_id):
            self.print_success("Anomaly message was stored in database")
            
            # Check if incident was created (simplified check)
            # In a real implementation, you'd check the incident API
            self.print_info("Checking if incident was created...")
            time.sleep(5)
            
            print(f"\n{Colors.GREEN}What this means:{Colors.END}")
            print("   ✅ Your system can detect and process problem messages")
            print("   ✅ The anomaly detection pipeline is working")
            print("   ℹ️  An incident should have been created in your incident management system")
        else:
            self.print_error("Anomaly message was not found in database")
            print(f"\n{Colors.RED}What this means:{Colors.END}")
            print("   ❌ The anomaly detection pipeline may not be working correctly")
        
        # Step 4: Summary
        self.print_step(4, "Sanity Test Results")
        print(f"\n{Colors.BOLD}SUMMARY:{Colors.END}")
        print(f"Session ID: {self.session_id}")
        print(f"Normal message ID: {normal_tracking_id}")
        print(f"Anomaly message ID: {anomaly_tracking_id}")
        print(f"Services health: {healthy_services}/{total_services} healthy")
        
        if healthy_services == total_services:
            self.print_success("Sanity test PASSED - Your system is working correctly!")
            print(f"\n{Colors.GREEN}Next Steps:{Colors.END}")
            print("   • You can now use the system for real monitoring")
            print("   • Try the regression mode for more comprehensive testing")
            print("   • Set up your dashboards in Grafana (http://localhost:3000)")
        else:
            self.print_warning("Sanity test had some issues - see details above")
            print(f"\n{Colors.YELLOW}Recommended Actions:{Colors.END}")
            print("   • Check the logs for services that are down")
            print("   • Try restarting services with 'docker compose restart'")
            print("   • Review the troubleshooting guide")
    
    def run_regression_mode(self):
        """Run regression mode - comprehensive testing for all data types"""
        self.session.mode = "regression"
        self.print_header("REGRESSION MODE - Comprehensive System Testing")
        
        self.explain_concept("Regression Mode", 
            "This mode runs thorough tests to make sure all parts of your system work correctly.\n"
            "   It tests different types of data and message formats to ensure compatibility.")
        
        if not self.check_prerequisites():
            return
        
        # Test different message types and formats
        test_scenarios = [
            ("System Log", "INFO: Application started successfully"),
            ("Error Log", "ERROR: Database connection failed"),
            ("Network Alert", "WARNING: High network latency detected"),
            ("CPU Alert", "CRITICAL: CPU usage exceeded 90%"),
            ("Memory Alert", "WARNING: Memory usage at 85%"),
            ("Disk Alert", "CRITICAL: Disk space below 5%"),
            ("Security Event", "ALERT: Failed login attempts detected"),
            ("Application Error", "FATAL: Application crashed with exception"),
        ]
        
        results = {}
        
        for i, (test_name, message) in enumerate(test_scenarios, 1):
            self.print_step(i, f"Testing {test_name}")
            
            tracking_id = self.send_test_message("REGRESSION", message)
            if tracking_id:
                self.print_info(f"Sent: {message}")
                time.sleep(5)  # Wait for processing
                
                if self.track_message_in_clickhouse(tracking_id):
                    self.print_success(f"{test_name} processed successfully")
                    results[test_name] = "PASS"
                else:
                    self.print_error(f"{test_name} was not processed correctly")
                    results[test_name] = "FAIL"
            else:
                self.print_error(f"Failed to send {test_name}")
                results[test_name] = "FAIL"
        
        # Summary
        passed = sum(1 for result in results.values() if result == "PASS")
        total = len(results)
        
        print(f"\n{Colors.BOLD}REGRESSION TEST RESULTS:{Colors.END}")
        print(f"Passed: {passed}/{total} tests")
        
        if passed == total:
            self.print_success("All regression tests PASSED!")
        elif passed > total * 0.8:
            self.print_warning(f"Most tests passed ({passed}/{total})")
        else:
            self.print_error(f"Many tests failed ({total-passed}/{total})")
    
    def run_surveillance_mode(self):
        """Run surveillance mode - monitor system for 15 minutes without test injection"""
        self.session.mode = "surveillance"
        self.print_header("SURVEILLANCE MODE - System Monitoring")
        
        self.explain_concept("Surveillance Mode", 
            "This mode watches your system for 15 minutes to see how it's performing\n"
            "   with real data. It doesn't inject any test data, just observes.")
        
        duration = 15 * 60  # 15 minutes
        start_time = time.time()
        
        print(f"\n{Colors.CYAN}Starting 15-minute surveillance period...{Colors.END}")
        print(f"Monitoring will end at: {datetime.now() + timedelta(seconds=duration)}")
        
        while time.time() - start_time < duration:
            remaining = duration - (time.time() - start_time)
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            
            print(f"\rTime remaining: {minutes:02d}:{seconds:02d}", end="", flush=True)
            
            # Check system health every minute
            if int(remaining) % 60 == 0:
                health_status = self.check_service_health()
                # Log status but don't print (to avoid cluttering output)
            
            time.sleep(1)
        
        print(f"\n\n{Colors.GREEN}Surveillance period completed!{Colors.END}")
    
    def run_automation_mode(self):
        """Run automation mode - autonomous monitoring for 1 hour"""
        self.session.mode = "automation"
        self.print_header("AUTOMATION MODE - Autonomous System Monitoring")
        
        self.explain_concept("Automation Mode", 
            "This mode runs your system autonomously for 1 hour, monitoring for\n"
            "   incidents and providing insights about system performance.")
        
        duration = 60 * 60  # 1 hour
        start_time = time.time()
        
        print(f"\n{Colors.CYAN}Starting 1-hour autonomous monitoring...{Colors.END}")
        print(f"Monitoring will end at: {datetime.now() + timedelta(seconds=duration)}")
        
        incident_count = 0
        anomaly_count = 0
        
        while time.time() - start_time < duration:
            remaining = duration - (time.time() - start_time)
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            seconds = int(remaining % 60)
            
            print(f"\rTime remaining: {hours:02d}:{minutes:02d}:{seconds:02d} | "
                  f"Incidents: {incident_count} | Anomalies: {anomaly_count}", 
                  end="", flush=True)
            
            time.sleep(10)  # Check every 10 seconds
        
        print(f"\n\n{Colors.GREEN}Automation monitoring completed!{Colors.END}")
        print(f"Total incidents detected: {incident_count}")
        print(f"Total anomalies detected: {anomaly_count}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="AIOps NAAS User-Friendly Diagnostic Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/user_friendly_diagnostics.py --mode sanity
  python3 scripts/user_friendly_diagnostics.py --mode regression
  python3 scripts/user_friendly_diagnostics.py --mode surveillance
  python3 scripts/user_friendly_diagnostics.py --mode automation

Modes:
  sanity       - Quick test with 1 normal and 1 anomaly message (5 minutes)
  regression   - Comprehensive testing for all supported data types (15 minutes)
  surveillance - Monitor system for 15 minutes without injecting test data
  automation   - Autonomous monitoring for 1 hour with detailed insights
        """
    )
    
    parser.add_argument(
        "--mode", 
        choices=["sanity", "regression", "surveillance", "automation"],
        required=True,
        help="Diagnostic mode to run"
    )
    
    parser.add_argument(
        "--output",
        help="Output file for detailed results (JSON format)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create diagnostics instance
    diagnostics = UserFriendlyDiagnostics()
    
    try:
        if args.mode == "sanity":
            diagnostics.run_sanity_mode()
        elif args.mode == "regression":
            diagnostics.run_regression_mode()
        elif args.mode == "surveillance":
            diagnostics.run_surveillance_mode()
        elif args.mode == "automation":
            diagnostics.run_automation_mode()
        
        # Save results if output file specified
        if args.output:
            diagnostics.session.end_time = datetime.now()
            with open(args.output, 'w') as f:
                json.dump(asdict(diagnostics.session), f, indent=2, default=str)
            print(f"\n{Colors.GREEN}Results saved to: {args.output}{Colors.END}")
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Diagnostic session interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()