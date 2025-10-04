#!/usr/bin/env python3
"""
Service Endpoint Validation Script
=================================

This script validates all service endpoints defined in docker-compose.yml
and ensures they are accessible and properly configured.

Usage:
    python3 scripts/validate_service_endpoints.py
    python3 scripts/validate_service_endpoints.py --check-ports-only
"""

import json
import requests
import time
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import subprocess
import socket

@dataclass
class ServiceEndpoint:
    """Represents a service endpoint configuration"""
    name: str
    external_port: int
    internal_port: int
    health_endpoint: str
    additional_endpoints: List[str]
    expected_status_codes: List[int] = None

    def __post_init__(self):
        if self.expected_status_codes is None:
            self.expected_status_codes = [200]

class ServiceEndpointValidator:
    """Validates all service endpoints for consistency and accessibility"""
    
    def __init__(self):
        self.services = self._define_service_endpoints()
        self.results = {}
        
    def _define_service_endpoints(self) -> List[ServiceEndpoint]:
        """Define all service endpoints based on docker-compose.yml"""
        return [
            # Core Infrastructure
            ServiceEndpoint("ClickHouse", 8123, 8123, "http://localhost:8123/ping", []),
            ServiceEndpoint("ClickHouse Native", 9000, 9000, "", []),  # Native protocol, no HTTP
            ServiceEndpoint("Victoria Metrics", 8428, 8428, "http://localhost:8428/health", [
                "http://localhost:8428/api/v1/query",
                "http://localhost:8428/api/v1/import/prometheus"
            ]),
            ServiceEndpoint("Grafana", 3000, 3000, "http://localhost:3000/api/health", []),
            
            # Message Bus & Processing
            ServiceEndpoint("NATS Client", 4222, 4222, "", []),  # Native protocol
            ServiceEndpoint("NATS Monitoring", 8222, 8222, "http://localhost:8222/healthz", [
                "http://localhost:8222/connz"
            ]),
            ServiceEndpoint("Vector", 8686, 8686, "http://localhost:8686/health", [
                "http://localhost:8686/metrics"
            ]),
            ServiceEndpoint("Benthos", 4195, 4195, "http://localhost:4195/ping", [
                "http://localhost:4195/stats"
            ]),
            ServiceEndpoint("Benthos Enrichment", 4196, 4196, "http://localhost:4196/ping", []),
            
            # AI/ML Services
            ServiceEndpoint("Qdrant", 6333, 6333, "http://localhost:6333/health", []),
            ServiceEndpoint("Ollama", 11434, 11434, "http://localhost:11434/api/version", []),
            
            # AIOps Core Services
            ServiceEndpoint("Anomaly Detection", 8080, 8080, "http://localhost:8080/health", []),
            ServiceEndpoint("Enhanced Anomaly Detection", 9082, 9082, "http://localhost:9082/health", []),
            ServiceEndpoint("Incident API", 9081, 9081, "http://localhost:9081/health", []),
            ServiceEndpoint("Device Registry", 8081, 8080, "http://localhost:8081/health", [
                "http://localhost:8081/devices"
            ]),
            
            # V3 Services - Fast Path Enrichment and Correlation
            ServiceEndpoint("Enrichment Service", 8092, 8085, "http://localhost:8092/health", []),
            ServiceEndpoint("Correlation Service", 8093, 8082, "http://localhost:8093/health", []),
            ServiceEndpoint("LLM Enricher", 9090, 9090, "http://localhost:9090/health", []),
            
            # v0.3 Services
            ServiceEndpoint("Link Health", 8082, 8082, "http://localhost:8082/health", []),
            ServiceEndpoint("Remediation", 8083, 8083, "http://localhost:8083/health", []),
            ServiceEndpoint("OPA", 8181, 8181, "http://localhost:8181/health", []),
            
            # v0.4 Services  
            ServiceEndpoint("Fleet Aggregation", 8084, 8084, "http://localhost:8084/health", []),
            ServiceEndpoint("Capacity Forecasting", 8085, 8085, "http://localhost:8085/health", []),
            ServiceEndpoint("Cross-Ship Benchmarking", 8086, 8086, "http://localhost:8086/health", []),
            ServiceEndpoint("Incident Explanation", 8087, 8087, "http://localhost:8087/health", []),
            ServiceEndpoint("Data Flow Visualization", 8089, 8089, "http://localhost:8089/health", []),
            ServiceEndpoint("Onboarding Service", 8090, 8090, "http://localhost:8090/health", []),
            ServiceEndpoint("Application Log Collector", 8091, 8090, "http://localhost:8091/health", []),
            
            # Monitoring & Alerting
            ServiceEndpoint("Node Exporter", 9100, 9100, "", []),  # Prometheus metrics, no health endpoint
            ServiceEndpoint("VMAlert", 8880, 8880, "", []),
            ServiceEndpoint("Alertmanager", 9093, 9093, "", []),
            ServiceEndpoint("MailHog Web", 8025, 8025, "http://localhost:8025/", []),
            ServiceEndpoint("MailHog SMTP", 1025, 1025, "", []),  # SMTP protocol
            ServiceEndpoint("Network Device Collector", 8088, 8080, "", []),  # Prometheus metrics endpoint
        ]
    
    def check_port_availability(self, port: int) -> bool:
        """Check if a port is available (not in use)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result != 0  # Port is available if connection fails
        except:
            return True
    
    def check_port_conflicts(self) -> List[Tuple[int, List[str]]]:
        """Check for port conflicts between services"""
        port_map = {}
        conflicts = []
        
        for service in self.services:
            port = service.external_port
            if port in port_map:
                port_map[port].append(service.name)
            else:
                port_map[port] = [service.name]
        
        for port, services in port_map.items():
            if len(services) > 1:
                conflicts.append((port, services))
                
        return conflicts
    
    def test_endpoint_accessibility(self, service: ServiceEndpoint) -> Dict:
        """Test if service endpoint is accessible"""
        result = {
            "service": service.name,
            "port": service.external_port,
            "accessible": False,
            "status_code": None,
            "error": None,
            "additional_endpoints": {}
        }
        
        if not service.health_endpoint:
            result["accessible"] = None  # No HTTP endpoint to test
            result["error"] = "No HTTP health endpoint defined"
            return result
            
        try:
            response = requests.get(service.health_endpoint, timeout=5)
            result["status_code"] = response.status_code
            result["accessible"] = response.status_code in service.expected_status_codes
            
            # Test additional endpoints
            for endpoint in service.additional_endpoints:
                try:
                    add_resp = requests.get(endpoint, timeout=3)
                    result["additional_endpoints"][endpoint] = {
                        "accessible": add_resp.status_code < 400,
                        "status_code": add_resp.status_code
                    }
                except Exception as e:
                    result["additional_endpoints"][endpoint] = {
                        "accessible": False,
                        "error": str(e)
                    }
                    
        except requests.exceptions.ConnectionError:
            result["error"] = "Connection refused - service likely not running"
        except requests.exceptions.Timeout:
            result["error"] = "Request timeout"
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def validate_all_endpoints(self) -> Dict:
        """Validate all service endpoints"""
        print("🔍 VALIDATING ALL SERVICE ENDPOINTS")
        print("=" * 50)
        
        # Check for port conflicts first
        conflicts = self.check_port_conflicts()
        if conflicts:
            print("\n❌ PORT CONFLICTS DETECTED:")
            for port, services in conflicts:
                print(f"   Port {port}: {', '.join(services)}")
            print()
        
        accessible_services = []
        inaccessible_services = []
        no_endpoint_services = []
        
        for service in self.services:
            result = self.test_endpoint_accessibility(service)
            self.results[service.name] = result
            
            if result["accessible"] is None:
                no_endpoint_services.append(service.name)
                print(f"ℹ️  {service.name:25} (:{service.external_port}) - No HTTP endpoint")
            elif result["accessible"]:
                accessible_services.append(service.name)
                print(f"✅ {service.name:25} (:{service.external_port}) - Accessible")
                
                # Show additional endpoints status
                for endpoint, status in result["additional_endpoints"].items():
                    status_icon = "✅" if status["accessible"] else "❌"
                    endpoint_path = endpoint.split('localhost:' + str(service.external_port))[-1]
                    print(f"   └── {status_icon} {endpoint_path}")
            else:
                inaccessible_services.append(service.name)
                error_msg = result["error"] or f"HTTP {result['status_code']}"
                print(f"❌ {service.name:25} (:{service.external_port}) - {error_msg}")
        
        # Summary
        total_http_services = len([s for s in self.services if s.health_endpoint])
        print(f"\n📊 VALIDATION SUMMARY")
        print(f"   Total Services: {len(self.services)}")
        print(f"   HTTP Services: {total_http_services}")
        print(f"   ✅ Accessible: {len(accessible_services)}")
        print(f"   ❌ Inaccessible: {len(inaccessible_services)}")
        print(f"   ℹ️  No HTTP Endpoint: {len(no_endpoint_services)}")
        
        if conflicts:
            print(f"   ⚠️  Port Conflicts: {len(conflicts)}")
            
        return {
            "total_services": len(self.services),
            "accessible": accessible_services,
            "inaccessible": inaccessible_services,
            "no_endpoint": no_endpoint_services,
            "port_conflicts": conflicts,
            "results": self.results
        }
    
    def generate_port_reference(self) -> str:
        """Generate a comprehensive port reference"""
        reference = """
# AIOps Platform Service Port Reference
# =====================================

## Core Infrastructure
- ClickHouse HTTP: 8123
- ClickHouse Native: 9000  
- Victoria Metrics: 8428
- Grafana: 3000

## Message Bus & Processing  
- NATS Client: 4222
- NATS Monitoring: 8222
- Vector: 8686
- Benthos: 4195
- Benthos Enrichment: 4196

## AI/ML Services
- Qdrant: 6333
- Ollama: 11434

## AIOps Core Services (8080-8099)
- Anomaly Detection: 8080
- Device Registry: 8081 → 8080 (container)
- Link Health: 8082  
- Remediation: 8083
- Fleet Aggregation: 8084
- Capacity Forecasting: 8085
- Cross-Ship Benchmarking: 8086
- Incident Explanation: 8087
- Network Device Collector: 8088 → 8080 (container)
- Data Flow Visualization: 8089
- Onboarding Service: 8090
- Application Log Collector: 8091 → 8090 (container)
- Enrichment Service (V3): 8092 → 8085 (container)
- Correlation Service (V3): 8093 → 8082 (container)
- Enhanced Anomaly Detection: 9082

## API Services (9080-9099)
- Incident API: 9081
- LLM Enricher (V3): 9090

## Monitoring & Alerting
- Node Exporter: 9100
- VMAlert: 8880
- Alertmanager: 9093
- MailHog Web: 8025
- MailHog SMTP: 1025

## Policy & Security
- OPA: 8181
"""
        return reference

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate AIOps service endpoints")
    parser.add_argument("--check-ports-only", action="store_true", 
                       help="Only check for port conflicts, don't test endpoints")
    parser.add_argument("--generate-reference", action="store_true",
                       help="Generate port reference documentation")
    
    args = parser.parse_args()
    
    validator = ServiceEndpointValidator()
    
    if args.generate_reference:
        print(validator.generate_port_reference())
        return
        
    if args.check_ports_only:
        conflicts = validator.check_port_conflicts()
        if conflicts:
            print("❌ PORT CONFLICTS DETECTED:")
            for port, services in conflicts:
                print(f"   Port {port}: {', '.join(services)}")
            sys.exit(1)
        else:
            print("✅ No port conflicts detected")
            sys.exit(0)
    
    results = validator.validate_all_endpoints()
    
    # Exit with error code if there are inaccessible services or port conflicts
    if results["inaccessible"] or results["port_conflicts"]:
        sys.exit(1)

if __name__ == "__main__":
    main()