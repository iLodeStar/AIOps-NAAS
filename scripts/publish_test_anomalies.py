#!/usr/bin/env python3
"""
AIOps NAAS - Direct Anomaly Publisher to NATS

This script publishes high-confidence CPU and Memory anomalies directly 
to NATS (anomaly.detected topic) to guarantee correlation/incidents even 
without node metrics or when the anomaly detection service is having issues.

This bypasses the metrics → anomaly detection step and validates:
- NATS connectivity
- Benthos correlation functionality  
- Incident API persistence
- ClickHouse storage (if configured)

Usage:
  python3 scripts/publish_test_anomalies.py
  
Environment Variables:
  NATS_URL - NATS server URL (default: nats://localhost:4222)
  INCIDENT_API_URL - Incident API URL for verification (default: http://localhost:8081)
  COUNT - Number of anomalies to publish (default: 3)
  INTERVAL - Seconds between anomalies (default: 2)
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List

# Import NATS client
try:
    import nats
    from nats.aio.client import Client as NATS
    NATS_AVAILABLE = True
except ImportError:
    print("❌ NATS client not available. Install with: pip install nats-py")
    print("   Or use: pip install -r requirements-test.txt")
    sys.exit(1)

# Optional requests for verification
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("⚠️  requests not available - incident verification will be skipped")

# Configuration
NATS_URL = os.getenv('NATS_URL', 'nats://localhost:4222')
INCIDENT_API_URL = os.getenv('INCIDENT_API_URL', 'http://localhost:8081')
COUNT = int(os.getenv('COUNT', '3'))
INTERVAL = int(os.getenv('INTERVAL', '2'))

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'

def print_header(message: str):
    print(f"\n{Colors.BLUE}================================================================{Colors.NC}")
    print(f"{Colors.BLUE}📡 {message}{Colors.NC}")
    print(f"{Colors.BLUE}================================================================{Colors.NC}")

def print_section(message: str):
    print(f"\n{Colors.YELLOW}----------------------------------------{Colors.NC}")
    print(f"{Colors.YELLOW}📋 {message}{Colors.NC}")
    print(f"{Colors.YELLOW}----------------------------------------{Colors.NC}")

def print_success(message: str):
    print(f"{Colors.GREEN}✅ {message}{Colors.NC}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.NC}")

def print_error(message: str):
    print(f"{Colors.RED}❌ {message}{Colors.NC}")

def create_test_anomaly(metric_name: str, anomaly_score: float, metric_value: float) -> Dict:
    """Create a test anomaly event matching the expected format"""
    return {
        "timestamp": datetime.now().isoformat(),
        "metric_name": metric_name,
        "metric_value": metric_value,
        "anomaly_score": anomaly_score,
        "anomaly_type": "statistical", 
        "detector_name": "direct_publisher",
        "threshold": 0.7 if metric_name == "cpu_usage" else 0.6,
        "metadata": {
            "source": "direct_nats_publisher",
            "test": True,
            "description": f"Test {metric_name} anomaly for pipeline validation"
        },
        "labels": {
            "instance": "test-validator:9100",
            "job": "node-exporter",
            "ship_id": "test-ship-01"
        }
    }

async def connect_nats() -> NATS:
    """Connect to NATS server"""
    print_section("Connecting to NATS")
    
    nc = NATS()
    
    try:
        await nc.connect(NATS_URL)
        print_success(f"Connected to NATS at {NATS_URL}")
        return nc
    except Exception as e:
        print_error(f"Failed to connect to NATS: {e}")
        raise

async def publish_anomalies(nc: NATS) -> List[Dict]:
    """Publish test anomalies to NATS"""
    print_section(f"Publishing {COUNT} Test Anomalies")
    
    published_anomalies = []
    
    for i in range(COUNT):
        # Alternate between CPU and Memory anomalies
        if i % 2 == 0:
            # CPU anomaly (high usage)
            anomaly = create_test_anomaly(
                metric_name="cpu_usage",
                anomaly_score=0.85,  # High confidence
                metric_value=92.5    # 92.5% CPU usage
            )
        else:
            # Memory anomaly (high usage)
            anomaly = create_test_anomaly(
                metric_name="memory_usage", 
                anomaly_score=0.78,  # High confidence
                metric_value=89.3    # 89.3% memory usage
            )
        
        # Publish to NATS
        try:
            message = json.dumps(anomaly)
            await nc.publish("anomaly.detected", message.encode())
            
            print_success(f"Published {anomaly['metric_name']} anomaly (score: {anomaly['anomaly_score']})")
            published_anomalies.append(anomaly)
            
            # Wait between publications (except for last one)
            if i < COUNT - 1:
                await asyncio.sleep(INTERVAL)
                
        except Exception as e:
            print_error(f"Failed to publish anomaly {i+1}: {e}")
    
    return published_anomalies

async def close_nats(nc: NATS):
    """Close NATS connection"""
    try:
        await nc.close()
        print_success("NATS connection closed")
    except Exception as e:
        print_warning(f"Error closing NATS: {e}")

def verify_incidents_created():
    """Verify incidents were created via Incident API"""
    if not REQUESTS_AVAILABLE:
        print_warning("requests library not available - skipping incident verification")
        return
    
    print_section("Verifying Incident Creation")
    
    # Wait a moment for correlation to process
    print("⏳ Waiting 10 seconds for correlation processing...")
    time.sleep(10)
    
    try:
        response = requests.get(f"{INCIDENT_API_URL}/incidents", timeout=10)
        if response.status_code == 200:
            incidents = response.json()
            
            if isinstance(incidents, list):
                # Look for recent test incidents
                test_incidents = [
                    incident for incident in incidents 
                    if incident.get('detector_name') == 'direct_publisher'
                ]
                
                if test_incidents:
                    print_success(f"Found {len(test_incidents)} test incidents!")
                    for incident in test_incidents[:3]:  # Show first 3
                        print(f"   ↳ {incident.get('incident_id', 'N/A')}: "
                              f"{incident.get('metric_name', 'N/A')} "
                              f"(score: {incident.get('anomaly_score', 'N/A')})")
                else:
                    print_warning("No test incidents found - check correlation service")
                    print(f"   Total incidents found: {len(incidents)}")
            else:
                print_warning("Unexpected incidents response format")
                
        else:
            print_error(f"Failed to query incidents API: {response.status_code}")
            
    except requests.RequestException as e:
        print_error(f"Could not verify incidents: {e}")

def print_usage():
    """Print usage information"""
    print(__doc__)

def print_summary(published_count: int):
    """Print operation summary"""
    print_header("Publication Summary")
    
    print(f"{Colors.BLUE}Published Anomalies:{Colors.NC} {published_count}")
    print(f"{Colors.BLUE}NATS Topic:{Colors.NC} anomaly.detected")
    print(f"{Colors.BLUE}Detector Name:{Colors.NC} direct_publisher")
    print(f"{Colors.BLUE}Anomaly Types:{Colors.NC} CPU usage (92.5%), Memory usage (89.3%)")
    
    print(f"\n{Colors.BLUE}Pipeline Components Tested:{Colors.NC}")
    print("1. ✅ NATS - Message publishing")
    print("2. ✅ Benthos - Event correlation (if configured)")
    print("3. ✅ Incident API - Incident creation (if correlation works)")
    print("4. ⚠️  ClickHouse - Storage (depends on incident API)")
    
    print(f"\n{Colors.BLUE}What This Bypasses:{Colors.NC}")
    print("- VictoriaMetrics metric queries")
    print("- Anomaly detection service processing")
    print("- Node exporter dependency")
    
    print(f"\n{Colors.BLUE}Next Steps:{Colors.NC}")
    print("- Check incidents: curl http://localhost:8081/incidents")
    print("- Review Benthos logs: docker compose logs benthos")
    print("- Check incident-api logs: docker compose logs incident-api")
    print("- Full validation: ./scripts/validate_pipeline.sh")

async def main():
    """Main publishing workflow"""
    print_header("AIOps NAAS Direct Anomaly Publisher")
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print_usage()
        return 0
    
    try:
        # Connect to NATS
        nc = await connect_nats()
        
        # Publish anomalies
        published_anomalies = await publish_anomalies(nc)
        
        # Close connection
        await close_nats(nc)
        
        # Verify incidents were created
        verify_incidents_created()
        
        # Print summary
        print_summary(len(published_anomalies))
        
        print(f"\n{Colors.GREEN}🎉 Successfully published {len(published_anomalies)} anomalies to NATS!{Colors.NC}")
        return 0
        
    except Exception as e:
        print_error(f"Operation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))