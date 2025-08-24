#!/usr/bin/env python3
"""
AIOps NAAS Simulator Soak Test

10-minute end-to-end test that:
1. Starts the data simulator with anomalies enabled
2. Subscribes to NATS subjects to consume messages  
3. Periodically queries service health endpoints
4. Checks remediation approval endpoints
5. Produces final outcome report

Usage:
    pytest tests/e2e/test_simulator_soak.py -v
    python3 tests/e2e/test_simulator_soak.py --standalone
"""

import asyncio
import json
import logging
import pytest
import requests
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading

# Add tools to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "data-simulator"))

try:
    from consumer import NATSConsumer
    CONSUMER_AVAILABLE = True
except ImportError:
    CONSUMER_AVAILABLE = False
    print("Warning: Consumer not available - install nats-py: pip install nats-py")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SoakTestRunner:
    """Main soak test runner"""
    
    def __init__(self, duration_seconds: int = 600):
        self.duration_seconds = duration_seconds
        self.start_time = None
        self.end_time = None
        self.simulator_process = None
        self.consumer_task = None
        self.health_checks = []
        self.approval_checks = []
        self.message_stats = {}
        self.errors = []
        
    def start_simulator(self, config_path: Optional[str] = None) -> bool:
        """Start the data simulator as subprocess"""
        try:
            cmd = [
                sys.executable, 
                "tools/data-simulator/data_simulator.py",
                "--duration", str(self.duration_seconds),
                "--anomalies",
                "--log-level", "INFO"
            ]
            
            if config_path:
                cmd.extend(["--config", config_path])
            
            logger.info(f"Starting simulator: {' '.join(cmd)}")
            self.simulator_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=Path(__file__).parent.parent.parent
            )
            
            # Give simulator time to start
            time.sleep(5)
            
            # Check if process started successfully
            if self.simulator_process.poll() is None:
                logger.info("Simulator started successfully")
                return True
            else:
                logger.error("Simulator failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start simulator: {e}")
            return False
    
    async def start_consumer(self) -> bool:
        """Start NATS consumer for message collection"""
        if not CONSUMER_AVAILABLE:
            logger.warning("Consumer not available - skipping message collection")
            return True
            
        try:
            subjects = [
                "telemetry.modem.kpis",
                "telemetry.weather.current", 
                "telemetry.ship.navigation",
                "link.health.prediction",
                "link.health.alert"
            ]
            
            consumer = NATSConsumer(subjects)
            
            # Run consumer in background
            self.consumer_task = asyncio.create_task(
                consumer.run_consumer(self.duration_seconds + 10)  # Extra time for cleanup
            )
            
            # Give consumer time to connect
            await asyncio.sleep(2)
            
            logger.info("Consumer started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            return False
    
    def check_service_health(self) -> Dict[str, Any]:
        """Check health of all services"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'services': {}
        }
        
        # Health endpoints to check
        endpoints = {
            'link-health': 'http://localhost:8082/health',
            'remediation': 'http://localhost:8083/health', 
            'incident-api': 'http://localhost:8081/health',
            'anomaly-detection': 'http://localhost:8080/health',
            'fleet-aggregation': 'http://localhost:8084/health',
            'capacity-forecasting': 'http://localhost:8085/health',
            'cross-ship-benchmarking': 'http://localhost:8086/health'
        }
        
        for service_name, url in endpoints.items():
            try:
                response = requests.get(url, timeout=5)
                health_status['services'][service_name] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'response_time_ms': round(response.elapsed.total_seconds() * 1000, 2)
                }
                if response.status_code == 200:
                    try:
                        health_status['services'][service_name]['details'] = response.json()
                    except:
                        health_status['services'][service_name]['details'] = response.text
                        
            except requests.RequestException as e:
                health_status['services'][service_name] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return health_status
    
    def check_remediation_approvals(self) -> Dict[str, Any]:
        """Check remediation approval queue"""
        try:
            response = requests.get('http://localhost:8083/approvals', timeout=5)
            if response.status_code == 200:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success',
                    'approvals': response.json()
                }
            else:
                return {
                    'timestamp': datetime.now().isoformat(),
                    'status': 'error',
                    'status_code': response.status_code
                }
        except requests.RequestException as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'status': 'error', 
                'error': str(e)
            }
    
    async def run_periodic_checks(self):
        """Run periodic health and approval checks"""
        logger.info("Starting periodic checks (every 30 seconds)")
        
        while datetime.now() < self.end_time:
            try:
                # Health check
                health_status = self.check_service_health()
                self.health_checks.append(health_status)
                
                healthy_services = sum(1 for s in health_status['services'].values() 
                                     if s.get('status') == 'healthy')
                total_services = len(health_status['services'])
                logger.info(f"Health check: {healthy_services}/{total_services} services healthy")
                
                # Approval check
                approval_status = self.check_remediation_approvals()
                self.approval_checks.append(approval_status)
                
                # Wait before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                error_msg = f"Error in periodic checks: {e}"
                logger.error(error_msg)
                self.errors.append({
                    'timestamp': datetime.now().isoformat(),
                    'error': error_msg
                })
                await asyncio.sleep(10)  # Shorter wait after error
    
    def stop_simulator(self):
        """Stop the simulator process"""
        if self.simulator_process:
            try:
                self.simulator_process.terminate()
                self.simulator_process.wait(timeout=10)
                logger.info("Simulator stopped")
            except subprocess.TimeoutExpired:
                logger.warning("Simulator did not stop gracefully, killing")
                self.simulator_process.kill()
                self.simulator_process.wait()
            except Exception as e:
                logger.error(f"Error stopping simulator: {e}")
    
    async def stop_consumer(self):
        """Stop the consumer task"""
        if self.consumer_task:
            try:
                self.consumer_task.cancel()
                try:
                    await self.consumer_task
                except asyncio.CancelledError:
                    pass
                logger.info("Consumer stopped")
            except Exception as e:
                logger.error(f"Error stopping consumer: {e}")
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate final test summary report"""
        elapsed_seconds = (self.end_time - self.start_time).total_seconds()
        
        # Analyze health checks
        total_health_checks = len(self.health_checks)
        healthy_checks = 0
        service_availability = {}
        
        for health_check in self.health_checks:
            all_healthy = True
            for service_name, service_status in health_check['services'].items():
                if service_name not in service_availability:
                    service_availability[service_name] = {'healthy': 0, 'total': 0}
                
                service_availability[service_name]['total'] += 1
                if service_status.get('status') == 'healthy':
                    service_availability[service_name]['healthy'] += 1
                else:
                    all_healthy = False
            
            if all_healthy:
                healthy_checks += 1
        
        # Calculate service availability percentages
        for service_name in service_availability:
            stats = service_availability[service_name]
            stats['availability_percent'] = (stats['healthy'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        # Count approval checks
        total_approval_checks = len(self.approval_checks)
        successful_approval_checks = sum(1 for check in self.approval_checks 
                                       if check.get('status') == 'success')
        
        summary = {
            'test_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(), 
                'duration_seconds': elapsed_seconds,
                'target_duration_seconds': self.duration_seconds,
                'completed_successfully': elapsed_seconds >= self.duration_seconds * 0.95  # 95% completion
            },
            'health_monitoring': {
                'total_checks': total_health_checks,
                'healthy_checks': healthy_checks,
                'overall_health_rate': (healthy_checks / total_health_checks * 100) if total_health_checks > 0 else 0,
                'service_availability': service_availability
            },
            'remediation_monitoring': {
                'total_checks': total_approval_checks,
                'successful_checks': successful_approval_checks,
                'success_rate': (successful_approval_checks / total_approval_checks * 100) if total_approval_checks > 0 else 0
            },
            'errors': self.errors,
            'assertions': {
                'minimum_duration_met': elapsed_seconds >= self.duration_seconds * 0.95,
                'health_checks_performed': total_health_checks >= 10,  # At least 10 health checks in 10 minutes
                'no_critical_errors': len(self.errors) == 0,
                'at_least_one_service_healthy': any(
                    stats['availability_percent'] > 0 
                    for stats in service_availability.values()
                )
            }
        }
        
        return summary
    
    async def run_soak_test(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Run the complete soak test"""
        logger.info(f"Starting {self.duration_seconds}-second soak test")
        
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(seconds=self.duration_seconds)
        
        try:
            # Start simulator
            if not self.start_simulator(config_path):
                raise RuntimeError("Failed to start simulator")
            
            # Start consumer
            await self.start_consumer()
            
            # Run periodic checks in parallel with main test duration
            await self.run_periodic_checks()
            
        except Exception as e:
            error_msg = f"Soak test failed: {e}"
            logger.error(error_msg)
            self.errors.append({
                'timestamp': datetime.now().isoformat(),
                'error': error_msg
            })
        finally:
            # Clean up
            self.stop_simulator()
            await self.stop_consumer()
            
            # Ensure we have end time
            if not self.end_time or datetime.now() < self.end_time:
                self.end_time = datetime.now()
        
        # Generate and save summary
        summary = self.generate_summary_report()
        
        # Save summary to file
        reports_dir = Path(__file__).parent.parent.parent / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        summary_file = reports_dir / "soak-summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Soak test completed. Summary saved to {summary_file}")
        return summary

# Pytest test functions
@pytest.mark.asyncio
async def test_simulator_soak_basic():
    """Basic 10-minute soak test"""
    runner = SoakTestRunner(duration_seconds=600)
    summary = await runner.run_soak_test()
    
    # Assert test outcomes
    assert summary['assertions']['minimum_duration_met'], "Test did not run for minimum duration"
    assert summary['assertions']['health_checks_performed'], "Insufficient health checks performed"
    assert summary['assertions']['at_least_one_service_healthy'], "No services were healthy during test"

@pytest.mark.asyncio  
async def test_simulator_soak_with_config():
    """Soak test with configuration file"""
    config_path = "configs/vendor-integrations.example.yaml"
    if not Path(config_path).exists():
        pytest.skip("Configuration file not found")
    
    runner = SoakTestRunner(duration_seconds=600)
    summary = await runner.run_soak_test(config_path)
    
    # Assert test outcomes
    assert summary['assertions']['minimum_duration_met'], "Test did not run for minimum duration"
    assert summary['assertions']['no_critical_errors'], f"Critical errors occurred: {summary['errors']}"

# Standalone execution
async def main():
    """Main entry point for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AIOps NAAS Simulator Soak Test")
    parser.add_argument("--duration", type=int, default=600, help="Test duration in seconds")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--log-level", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run soak test
    runner = SoakTestRunner(duration_seconds=args.duration)
    summary = await runner.run_soak_test(args.config)
    
    # Print results
    print("\n" + "="*50)
    print("SOAK TEST SUMMARY")
    print("="*50)
    print(f"Duration: {summary['test_info']['duration_seconds']:.1f} seconds")
    print(f"Health Checks: {summary['health_monitoring']['total_checks']}")
    print(f"Overall Health Rate: {summary['health_monitoring']['overall_health_rate']:.1f}%")
    print(f"Errors: {len(summary['errors'])}")
    
    # Check assertions
    all_passed = all(summary['assertions'].values())
    print(f"\nAll Assertions Passed: {'✅ YES' if all_passed else '❌ NO'}")
    
    for assertion, passed in summary['assertions'].items():
        status = "✅" if passed else "❌"
        print(f"  {status} {assertion}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))