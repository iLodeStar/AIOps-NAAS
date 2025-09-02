#!/usr/bin/env python3
"""
AIOps NAAS - Two-Level Correlation Test Data Publisher

This script publishes test data to demonstrate the two-level correlation approach:

Level 1: Raw data enrichment and correlation across multiple sources
Level 2: Anomaly correlation to create unified incidents

The script simulates:
- System metrics with correlated satellite and weather data
- Network performance metrics with system load context  
- Maritime operational scenarios (weather impact, equipment failure)
"""

import asyncio
import json
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Optional NATS client for publishing
try:
    from nats.aio.client import Client as NATS
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TwoLevelCorrelationTestPublisher:
    """Publisher for testing two-level correlation system"""
    
    def __init__(self):
        self.nats_client = None
        self.ship_id = "ship-01"
        
    async def connect_nats(self):
        """Connect to NATS for publishing test data"""
        if not NATS_AVAILABLE:
            logger.error("NATS client not available. Install nats-py: pip install nats-py")
            return False
            
        try:
            self.nats_client = NATS()
            await self.nats_client.connect("nats://localhost:4222")
            logger.info("Connected to NATS for test data publishing")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            return False
    
    def generate_system_metrics(self, scenario: str = "normal") -> Dict[str, Any]:
        """Generate system metrics data"""
        base_cpu = 25.0
        base_memory = 40.0
        base_disk = 60.0
        
        # Adjust based on scenario
        if scenario == "high_load":
            base_cpu = 85.0  # High CPU to trigger anomaly
            base_memory = 88.0  # High memory to trigger correlation
        elif scenario == "weather_stress":
            base_cpu = 75.0  # Elevated due to weather processing
            base_memory = 65.0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "ship_id": self.ship_id,
            "cpu_usage_percent": base_cpu + random.uniform(-5, 15),
            "memory_usage_percent": base_memory + random.uniform(-5, 15),
            "disk_usage_percent": base_disk + random.uniform(-5, 10),
            "network_io_bytes": random.randint(1000000, 10000000),
            "disk_io_utilization": random.uniform(10, 50)
        }
    
    def generate_satellite_data(self, scenario: str = "normal") -> Dict[str, Any]:
        """Generate satellite/RF equipment data"""
        base_snr = 18.0  # dB
        base_ber = 0.0001
        base_signal = -65.0  # dBm
        
        # Adjust for weather scenarios
        if scenario == "rain_fade":
            base_snr = 8.0  # Poor SNR due to rain
            base_ber = 0.005  # High BER
            base_signal = -85.0  # Weak signal
        elif scenario == "weather_stress":
            base_snr = 12.0  # Marginal SNR
            base_ber = 0.0008
            base_signal = -75.0
            
        return {
            "timestamp": datetime.now().isoformat(),
            "ship_id": self.ship_id,
            "snr_db": base_snr + random.uniform(-2, 2),
            "ber": base_ber + random.uniform(-base_ber/2, base_ber*3),
            "signal_strength_dbm": base_signal + random.uniform(-5, 5),
            "es_no_db": base_snr + 3 + random.uniform(-1, 1),
            "frequency_ghz": 14.25,
            "antenna_elevation": 45.0 + random.uniform(-5, 5),
            "antenna_azimuth": 180.0 + random.uniform(-10, 10)
        }
    
    def generate_weather_data(self, scenario: str = "normal") -> Dict[str, Any]:
        """Generate weather data affecting satellite communications"""
        base_rain = 0.0
        base_wind = 15.0
        base_cloud = 20.0
        
        if scenario == "rain_fade" or scenario == "weather_stress":
            base_rain = 12.0  # Heavy rain affecting satellite
            base_wind = 35.0  # Strong winds
            base_cloud = 85.0  # Heavy cloud cover
            
        return {
            "timestamp": datetime.now().isoformat(),
            "ship_id": self.ship_id,
            "rain_rate_mm_hr": base_rain + random.uniform(0, 5),
            "wind_speed_kts": base_wind + random.uniform(-5, 10),
            "cloud_cover_percent": base_cloud + random.uniform(-10, 15),
            "temperature_celsius": 22.0 + random.uniform(-3, 8),
            "humidity_percent": 75.0 + random.uniform(-10, 15),
            "pressure_hpa": 1013.0 + random.uniform(-5, 5)
        }
    
    def generate_network_data(self, scenario: str = "normal") -> Dict[str, Any]:
        """Generate comprehensive network device data"""
        base_latency = 120.0  # ms
        base_throughput = 50.0  # Mbps
        base_packet_loss = 0.1  # %
        
        if scenario == "high_load":
            base_latency = 350.0  # High latency due to system load
            base_throughput = 25.0  # Reduced throughput
            base_packet_loss = 2.5  # Packet loss
        elif scenario == "weather_stress":
            base_latency = 200.0  # Elevated latency
            base_throughput = 35.0
            base_packet_loss = 0.8
            
        return {
            "timestamp": datetime.now().isoformat(),
            "ship_id": self.ship_id,
            "device_ip": "192.168.1.10",
            "device_type": "switch",
            "vendor": "cisco", 
            "hostname": "core-switch-bridge",
            "location": "bridge",
            "cpu_utilization_percent": 25.0 + random.uniform(-10, 40) if scenario != "high_load" else 85.0 + random.uniform(-5, 10),
            "memory_utilization_percent": 40.0 + random.uniform(-15, 30) if scenario != "high_load" else 90.0 + random.uniform(-5, 5),
            "temperature_celsius": 42.0 + random.uniform(-5, 8),
            "power_supply_status": "normal",
            "fan_status": "normal",
            # Network performance metrics
            "latency_ms": base_latency + random.uniform(-20, 50),
            "throughput_mbps": base_throughput + random.uniform(-10, 20),
            "packet_loss_percent": max(0, base_packet_loss + random.uniform(-0.5, 2.0)),
            "jitter_ms": random.uniform(5, 25),
            "connection_count": random.randint(50, 200),
            # Interface metrics
            "interfaces": [
                {
                    "interface_name": "GigabitEthernet1/0/1",
                    "interface_index": 1,
                    "admin_status": "up",
                    "oper_status": "up", 
                    "utilization_percent": random.uniform(20, 80) if scenario == "high_load" else random.uniform(10, 40),
                    "in_octets": random.randint(1000000, 10000000),
                    "out_octets": random.randint(1000000, 10000000),
                    "in_errors": random.randint(0, 5),
                    "out_errors": random.randint(0, 5)
                },
                {
                    "interface_name": "GigabitEthernet1/0/24",
                    "interface_index": 24,
                    "admin_status": "up",
                    "oper_status": "up",
                    "utilization_percent": random.uniform(15, 60) if scenario == "high_load" else random.uniform(5, 25),
                    "in_octets": random.randint(500000, 5000000),
                    "out_octets": random.randint(500000, 5000000),
                    "in_errors": random.randint(0, 2),
                    "out_errors": random.randint(0, 2)
                }
            ]
        }
    
    def generate_ship_telemetry(self) -> Dict[str, Any]:
        """Generate ship navigation and attitude data"""
        return {
            "timestamp": datetime.now().isoformat(),
            "ship_id": self.ship_id,
            "latitude": 25.7617 + random.uniform(-0.1, 0.1),  # Miami area
            "longitude": -80.1918 + random.uniform(-0.1, 0.1),
            "heading_degrees": random.uniform(0, 360),
            "speed_knots": 12.0 + random.uniform(-2, 8),
            "pitch_degrees": random.uniform(-2, 2),
            "roll_degrees": random.uniform(-3, 3),
            "yaw_degrees": random.uniform(-1, 1),
            "altitude_meters": 5.0 + random.uniform(-2, 5)
        }
        
    async def publish_raw_data_set(self, scenario: str = "normal"):
        """Publish a complete set of raw data for Level 1 correlation"""
        try:
            # Generate all data types for the scenario
            system_data = self.generate_system_metrics(scenario)
            satellite_data = self.generate_satellite_data(scenario) 
            weather_data = self.generate_weather_data(scenario)
            network_data = self.generate_network_data(scenario)
            ship_data = self.generate_ship_telemetry()
            
            # Publish to appropriate NATS subjects for Level 1 correlation
            await self.nats_client.publish("metrics.system.performance", json.dumps(system_data).encode())
            await self.nats_client.publish("telemetry.satellite.rf", json.dumps(satellite_data).encode())
            await self.nats_client.publish("external.weather.conditions", json.dumps(weather_data).encode())
            await self.nats_client.publish("telemetry.network.devices", json.dumps(network_data).encode())
            await self.nats_client.publish("telemetry.ship.navigation", json.dumps(ship_data).encode())
            
            logger.info(f"Published raw data set for scenario: {scenario}")
            
        except Exception as e:
            logger.error(f"Error publishing raw data set: {e}")
    
    async def run_correlation_test_scenarios(self):
        """Run test scenarios to demonstrate two-level correlation"""
        
        scenarios = [
            ("normal", "Normal operations - baseline data"),
            ("high_load", "High system load scenario - CPU/Memory correlation"),
            ("weather_stress", "Weather impact scenario - Satellite/Weather correlation"),
            ("rain_fade", "Heavy rain scenario - Multiple system degradation")
        ]
        
        logger.info("Starting two-level correlation test scenarios")
        
        for scenario, description in scenarios:
            logger.info(f"\n=== Running Scenario: {scenario} ===")
            logger.info(f"Description: {description}")
            
            # Publish 5 data points over 30 seconds for this scenario
            for i in range(5):
                await self.publish_raw_data_set(scenario)
                
                # Wait between publishes to allow processing
                await asyncio.sleep(6)
                
            logger.info(f"Completed scenario: {scenario}")
            
            # Pause between scenarios
            logger.info("Waiting 30 seconds before next scenario...")
            await asyncio.sleep(30)
            
        logger.info("All correlation test scenarios completed!")
    
    async def continuous_test_mode(self, interval_seconds: int = 10):
        """Run continuous test data generation"""
        logger.info(f"Starting continuous test mode (interval: {interval_seconds}s)")
        
        scenario_cycle = ["normal", "normal", "normal", "high_load", "normal", "weather_stress", "normal", "rain_fade"]
        scenario_index = 0
        
        try:
            while True:
                current_scenario = scenario_cycle[scenario_index % len(scenario_cycle)]
                await self.publish_raw_data_set(current_scenario)
                
                scenario_index += 1
                await asyncio.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("Continuous test mode stopped by user")

async def main():
    """Main function to run correlation tests"""
    publisher = TwoLevelCorrelationTestPublisher()
    
    # Connect to NATS
    if not await publisher.connect_nats():
        logger.error("Cannot run tests without NATS connection")
        return
    
    # Choose test mode
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        await publisher.continuous_test_mode()
    else:
        await publisher.run_correlation_test_scenarios()
        
    # Cleanup
    if publisher.nats_client:
        await publisher.nats_client.close()

if __name__ == "__main__":
    if not NATS_AVAILABLE:
        print("Error: NATS client not available")
        print("Install with: pip install nats-py")
        exit(1)
        
    asyncio.run(main())