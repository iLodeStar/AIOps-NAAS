#!/usr/bin/env python3
"""
Internal Port Validation Script
===============================

This script checks if services are actually listening on their internal ports
inside Docker containers as defined in docker-compose.yml.

Usage:
    python3 scripts/check_internal_ports.py
"""

import subprocess
import json
import sys
import time
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class ServicePortMapping:
    """Represents a service with its port mapping"""
    name: str
    container_name: str
    external_port: int
    internal_port: int
    expected_health_endpoint: str = ""

class InternalPortChecker:
    """Checks if services are listening on their internal ports inside containers"""
    
    def __init__(self):
        self.services = self._define_service_port_mappings()
        
    def _define_service_port_mappings(self) -> List[ServicePortMapping]:
        """Define services with port mappings from docker-compose.yml"""
        return [
            # Services with port mappings (external:internal)
            ServicePortMapping("device-registry", "aiops-device-registry", 8081, 8080, "http://localhost:8080/health"),
            ServicePortMapping("application-log-collector", "aiops-application-log-collector", 8091, 8090, "http://localhost:8090/health"),
            ServicePortMapping("network-device-collector", "aiops-network-device-collector", 8088, 8080, ""),
            
            # Services with same external and internal ports (for comparison)
            ServicePortMapping("anomaly-detection", "aiops-anomaly-detection", 8080, 8080, "http://localhost:8080/health"),
            ServicePortMapping("clickhouse", "aiops-clickhouse", 8123, 8123, "http://localhost:8123/ping"),
            ServicePortMapping("grafana", "aiops-grafana", 3000, 3000, "http://localhost:3000/api/health"),
            ServicePortMapping("victoria-metrics", "aiops-victoria-metrics", 8428, 8428, "http://localhost:8428/health"),
            ServicePortMapping("vector", "aiops-vector", 8686, 8686, "http://localhost:8686/health"),
            ServicePortMapping("nats", "aiops-nats", 8222, 8222, "http://localhost:8222/healthz"),
            ServicePortMapping("incident-api", "aiops-incident-api", 9081, 9081, "http://localhost:9081/health"),
        ]
    
    def is_container_running(self, container_name: str) -> bool:
        """Check if a container is running"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            return container_name in result.stdout
        except subprocess.CalledProcessError:
            return False
    
    def check_port_in_container(self, container_name: str, port: int) -> Dict:
        """Check if a port is listening inside a container"""
        result = {
            "container": container_name,
            "port": port,
            "listening": False,
            "error": None,
            "details": ""
        }
        
        if not self.is_container_running(container_name):
            result["error"] = "Container not running"
            return result
        
        try:
            # Try netstat first
            cmd = ["docker", "exec", container_name, "netstat", "-ln"]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if process.returncode == 0:
                # Check if port is in netstat output
                lines = process.stdout.split('\n')
                for line in lines:
                    if f":{port}" in line and ("LISTEN" in line or "0.0.0.0" in line):
                        result["listening"] = True
                        result["details"] = line.strip()
                        break
            else:
                # Try ss command as fallback
                cmd = ["docker", "exec", container_name, "ss", "-ln"]
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if process.returncode == 0:
                    lines = process.stdout.split('\n')
                    for line in lines:
                        if f":{port}" in line and "LISTEN" in line:
                            result["listening"] = True
                            result["details"] = line.strip()
                            break
                else:
                    # Try lsof as final fallback
                    cmd = ["docker", "exec", container_name, "lsof", "-i", f":{port}"]
                    process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if process.returncode == 0 and process.stdout.strip():
                        result["listening"] = True
                        result["details"] = process.stdout.strip()
                        
        except subprocess.TimeoutExpired:
            result["error"] = "Command timeout"
        except subprocess.CalledProcessError as e:
            result["error"] = f"Command failed: {e}"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def test_health_endpoint_from_container(self, container_name: str, health_endpoint: str) -> Dict:
        """Test health endpoint from inside the container"""
        result = {
            "container": container_name,
            "endpoint": health_endpoint,
            "accessible": False,
            "status_code": None,
            "error": None
        }
        
        if not health_endpoint:
            result["error"] = "No health endpoint defined"
            return result
            
        if not self.is_container_running(container_name):
            result["error"] = "Container not running"
            return result
        
        try:
            # Use curl inside the container to test the health endpoint
            cmd = ["docker", "exec", container_name, "curl", "-s", "-w", "%{http_code}", "-o", "/dev/null", health_endpoint]
            process = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if process.returncode == 0:
                status_code = process.stdout.strip()
                if status_code.isdigit():
                    result["status_code"] = int(status_code)
                    result["accessible"] = result["status_code"] < 400
            else:
                result["error"] = f"curl failed: {process.stderr}"
                
        except subprocess.TimeoutExpired:
            result["error"] = "Request timeout"
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def get_running_containers(self) -> List[str]:
        """Get list of running AIOps containers"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=aiops-", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []
    
    def validate_internal_ports(self) -> Dict:
        """Validate that services are listening on their internal ports"""
        print("🔍 CHECKING INTERNAL PORTS IN CONTAINERS")
        print("=" * 50)
        
        running_containers = self.get_running_containers()
        if not running_containers:
            print("❌ No running AIOps containers found")
            print("   Run 'docker-compose up -d' to start services")
            return {
                "running_containers": 0, 
                "tested_services": 0,
                "port_listening_services": [],
                "port_not_listening_services": [],
                "health_accessible_services": [],
                "health_not_accessible_services": [],
                "results": []
            }
        
        print(f"📊 Found {len(running_containers)} running containers:")
        for container in running_containers:
            print(f"   - {container}")
        print()
        
        results = []
        port_listening_services = []
        port_not_listening_services = []
        health_accessible_services = []
        health_not_accessible_services = []
        
        for service in self.services:
            if service.container_name not in running_containers:
                print(f"⏸️  {service.name:25} - Container not running")
                continue
                
            # Check if internal port is listening
            port_result = self.check_port_in_container(service.container_name, service.internal_port)
            
            # Check health endpoint if defined
            health_result = None
            if service.expected_health_endpoint:
                health_result = self.test_health_endpoint_from_container(
                    service.container_name, 
                    service.expected_health_endpoint
                )
            
            result = {
                "service": service.name,
                "container": service.container_name,
                "external_port": service.external_port,
                "internal_port": service.internal_port,
                "port_listening": port_result,
                "health_check": health_result
            }
            results.append(result)
            
            # Display results
            port_status = "✅" if port_result["listening"] else "❌"
            port_error = f" ({port_result['error']})" if port_result["error"] else ""
            
            if port_result["listening"]:
                port_listening_services.append(service.name)
            else:
                port_not_listening_services.append(service.name)
            
            print(f"{port_status} {service.name:25} Internal port {service.internal_port}{port_error}")
            
            if port_result["details"]:
                print(f"   └── {port_result['details']}")
            
            # Show health check result if available
            if health_result:
                health_status = "✅" if health_result["accessible"] else "❌"
                health_error = f" ({health_result['error']})" if health_result["error"] else ""
                status_info = f" [HTTP {health_result['status_code']}]" if health_result["status_code"] else ""
                
                print(f"   └── Health: {health_status} {service.expected_health_endpoint}{status_info}{health_error}")
                
                if health_result["accessible"]:
                    health_accessible_services.append(service.name)
                else:
                    health_not_accessible_services.append(service.name)
        
        # Summary
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"   Running Containers: {len(running_containers)}")
        print(f"   Tested Services: {len(results)}")
        print(f"   ✅ Ports Listening: {len(port_listening_services)}")
        print(f"   ❌ Ports Not Listening: {len(port_not_listening_services)}")
        
        if health_accessible_services or health_not_accessible_services:
            print(f"   ✅ Health Checks Passing: {len(health_accessible_services)}")
            print(f"   ❌ Health Checks Failing: {len(health_not_accessible_services)}")
        
        return {
            "running_containers": len(running_containers),
            "tested_services": len(results),
            "port_listening_services": port_listening_services,
            "port_not_listening_services": port_not_listening_services,
            "health_accessible_services": health_accessible_services,
            "health_not_accessible_services": health_not_accessible_services,
            "results": results
        }

def main():
    checker = InternalPortChecker()
    results = checker.validate_internal_ports()
    
    # Exit with error if there are issues
    if results["port_not_listening_services"] or results["health_not_accessible_services"]:
        sys.exit(1)

if __name__ == "__main__":
    main()