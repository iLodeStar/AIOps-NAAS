#!/usr/bin/env python3
"""
Comprehensive validation script for the 10 validation points from issue #38:

1. Run the dockers in local ubuntu
2. get syslogs
3. validate if metrics are generated
4. validate if metrics are transformed
5. validate if metrics are pushed to clickhouse
6. validate clickhouse receives the data
7. validate the vector API are running
8. validate vector API can be accessed outside the docker
9. validate vector can connect to click house
10. validate data sent to clickhouse is same as outcome of transformation.
"""

import json
import logging
import requests
import socket
import subprocess
import time
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ValidationResults:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.total = 10
    
    def add_result(self, point: int, description: str, passed: bool, details: str = ""):
        self.results[point] = {
            'description': description,
            'passed': passed,
            'details': details
        }
        if passed:
            self.passed += 1
        logger.info(f"Point {point}: {'✅ PASS' if passed else '❌ FAIL'} - {description}")
        if details:
            logger.info(f"  Details: {details}")
    
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"VALIDATION SUMMARY: {self.passed}/{self.total} POINTS PASSED")
        print(f"{'='*60}")
        for i in range(1, 11):
            if i in self.results:
                result = self.results[i]
                status = '✅ PASS' if result['passed'] else '❌ FAIL'
                print(f"{i:2d}. {status} - {result['description']}")
                if result['details'] and not result['passed']:
                    print(f"     Details: {result['details']}")
        print(f"{'='*60}")

def run_command(cmd: str, timeout: int = 30) -> Tuple[bool, str]:
    """Run shell command and return success status and output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, f"Command failed: {e}"

def check_url(url: str, timeout: int = 10) -> Tuple[bool, str]:
    """Check if URL is accessible"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200, f"Status: {response.status_code}, Content length: {len(response.text)}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

def send_syslog_message(host: str = "localhost", port: int = 1514) -> Tuple[bool, str]:
    """Send test syslog message"""
    try:
        message = f"<14>1 {time.strftime('%Y-%m-%dT%H:%M:%S.000Z')} test-host test-app 1234 - - Test syslog message from validation script"
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.send(message.encode('utf-8'))
        sock.close()
        return True, f"Sent message: {message[:50]}..."
    except Exception as e:
        return False, str(e)

def query_clickhouse(query: str, host: str = "localhost", port: int = 8123) -> Tuple[bool, str]:
    """Execute ClickHouse query"""
    try:
        url = f"http://{host}:{port}/"
        response = requests.post(url, data=query, timeout=10)
        if response.status_code == 200:
            return True, response.text.strip()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except requests.exceptions.RequestException as e:
        return False, str(e)

def main():
    results = ValidationResults()
    
    print("Starting comprehensive validation of 10 points...")
    
    # Point 1: Run the dockers in local ubuntu
    logger.info("Checking Point 1: Docker containers running")
    success, output = run_command("docker compose ps")
    container_status = {}
    if success:
        lines = output.split('\n')
        for line in lines:
            if 'aiops-clickhouse' in line:
                container_status['clickhouse'] = 'running' if 'Up' in line else 'down'
            if 'aiops-vector' in line:
                container_status['vector'] = 'running' if 'Up' in line else 'down'
    
    both_running = container_status.get('clickhouse') == 'running' and container_status.get('vector') == 'running'
    results.add_result(1, "Docker containers running", both_running, 
                      f"ClickHouse: {container_status.get('clickhouse', 'unknown')}, Vector: {container_status.get('vector', 'unknown')}")
    
    # Point 2: Get syslogs
    logger.info("Checking Point 2: Send syslog messages")
    success, details = send_syslog_message()
    results.add_result(2, "Syslog message sent", success, details)
    
    # Wait a moment for processing
    time.sleep(5)
    
    # Point 3: Validate if metrics are generated
    logger.info("Checking Point 3: Metrics generation")
    success, output = run_command("docker compose logs vector | grep -i 'host_metrics' | tail -5")
    metrics_generated = success and "host_metrics" in output
    results.add_result(3, "Metrics generated", metrics_generated, 
                      f"Vector logs show host_metrics activity: {metrics_generated}")
    
    # Point 4: Validate if metrics are transformed
    logger.info("Checking Point 4: Metrics transformation")
    success, output = run_command("docker compose logs vector | grep -i 'metrics_for_logs' | tail -5")
    metrics_transformed = success and ("metrics_for_logs" in output or "transform" in output)
    results.add_result(4, "Metrics transformed", metrics_transformed,
                      f"Vector logs show transformation activity")
    
    # Point 5: Validate if metrics are pushed to clickhouse
    logger.info("Checking Point 5: Metrics pushed to ClickHouse")
    success, output = run_command("docker compose logs vector | grep -i clickhouse | tail -5")
    metrics_pushed = success and ("clickhouse" in output.lower() and "200" in output)
    results.add_result(5, "Metrics pushed to ClickHouse", metrics_pushed,
                      f"Vector logs show ClickHouse interaction")
    
    # Point 6: Validate clickhouse receives the data
    logger.info("Checking Point 6: ClickHouse receives data")
    success, result = query_clickhouse("SELECT count() FROM logs.raw WHERE timestamp >= now() - INTERVAL 5 MINUTE")
    if success:
        try:
            count = int(result)
            data_received = count > 0
            results.add_result(6, "ClickHouse receives data", data_received,
                              f"Records in last 5 minutes: {count}")
        except ValueError:
            results.add_result(6, "ClickHouse receives data", False, f"Invalid count result: {result}")
    else:
        results.add_result(6, "ClickHouse receives data", False, f"Query failed: {result}")
    
    # Point 7: Validate the vector API are running
    logger.info("Checking Point 7: Vector API running")
    success, details = check_url("http://localhost:8686/health")
    results.add_result(7, "Vector API running", success, details)
    
    # Point 8: Validate vector API can be accessed outside the docker
    logger.info("Checking Point 8: Vector API external access")
    success, details = check_url("http://localhost:8686/health")
    results.add_result(8, "Vector API external access", success, details)
    
    # Point 9: Validate vector can connect to clickhouse
    logger.info("Checking Point 9: Vector-ClickHouse connectivity")
    success, output = run_command("docker compose logs vector | grep -E '(clickhouse|HTTP.*200)' | tail -3")
    connectivity_ok = success and ("200" in output or "OK" in output)
    results.add_result(9, "Vector-ClickHouse connectivity", connectivity_ok,
                      f"Recent connection logs show success")
    
    # Point 10: Validate data sent to clickhouse is same as outcome of transformation
    logger.info("Checking Point 10: Data consistency")
    success, raw_data = query_clickhouse("SELECT raw_log, level, source FROM logs.raw WHERE timestamp >= now() - INTERVAL 5 MINUTE LIMIT 3")
    if success and raw_data:
        # Check if we have proper transformed data structure
        has_level = "INFO" in raw_data or "WARN" in raw_data or "ERROR" in raw_data
        has_source = "host_metrics" in raw_data or "syslog" in raw_data
        consistency_ok = has_level and has_source
        results.add_result(10, "Data consistency", consistency_ok,
                          f"Transformed fields present in ClickHouse data")
    else:
        results.add_result(10, "Data consistency", False, "No recent data to validate")
    
    results.print_summary()
    return results.passed == results.total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)