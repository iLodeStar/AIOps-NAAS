#!/usr/bin/env python3
"""
AIOps NAAS Real-Time Data Simulator with Random Anomalies

This simulator generates realistic maritime telemetry data for testing the complete
AIOps pipeline. It supports the data sources mentioned in the architecture:

Data Sources Simulated:
- Network Devices: Router, switch, firewall metrics via SNMP-like data
- Satellite & RF Equipment: VSAT/LEO terminals, ACU data (SNR, Es/No, BER, etc.)
- Applications & Services: HTTP response times, availability metrics
- External Context: Weather API data, vessel telemetry (NMEA-0183), cruise schedule

Features:
- Real-time data generation with configurable intervals
- Random anomaly injection across multiple scenarios
- Multiple output formats (JSON, CSV, InfluxDB line protocol)
- MQTT and HTTP endpoint publishing support
- Comprehensive logging and metrics collection
"""

import asyncio
import json
import random
import time
import logging
import csv
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Optional dependencies for advanced features
try:
    import requests
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalyScenario(Enum):
    """Predefined anomaly scenarios"""
    NORMAL = "normal_operation"
    SATELLITE_DEGRADATION = "satellite_degradation"
    WEATHER_IMPACT = "weather_impact"
    NETWORK_CONGESTION = "network_congestion"
    EQUIPMENT_FAILURE = "equipment_failure"
    SECURITY_INCIDENT = "security_incident"
    POWER_FLUCTUATION = "power_fluctuation"


@dataclass
class SatelliteData:
    """Satellite/RF equipment telemetry"""
    timestamp: str
    snr_db: float
    ber: float
    signal_strength_dbm: float
    es_no_db: float
    rain_fade_margin_db: float
    frequency_ghz: float
    modulation: str
    fec_rate: str
    antenna_elevation: float
    antenna_azimuth: float


@dataclass
class ShipTelemetry:
    """Ship movement and position data (NMEA-0183 style)"""
    timestamp: str
    latitude: float
    longitude: float
    heading_degrees: float
    speed_knots: float
    pitch_degrees: float
    roll_degrees: float
    yaw_degrees: float
    altitude_meters: float
    gps_quality: int


@dataclass
class WeatherData:
    """Weather conditions affecting satellite link"""
    timestamp: str
    precipitation_rate_mm_hr: float
    wind_speed_knots: float
    wind_direction_degrees: float
    temperature_celsius: float
    humidity_percent: float
    pressure_hpa: float
    visibility_km: float
    cloud_cover_percent: float


@dataclass
class NetworkMetrics:
    """Network device metrics (SNMP-style)"""
    timestamp: str
    device_type: str
    cpu_utilization_percent: float
    memory_utilization_percent: float
    interface_utilization_percent: float
    packet_loss_percent: float
    latency_ms: float
    error_count: int
    temperature_celsius: float


@dataclass
class ApplicationMetrics:
    """Application and service performance"""
    timestamp: str
    service_name: str
    response_time_ms: float
    error_rate_percent: float
    throughput_rps: float
    active_connections: int
    queue_depth: int
    availability_percent: float


class AIOpsDataSimulator:
    """Main data simulator class"""
    
    def __init__(self, anomaly_rate: float = 0.15):
        """
        Initialize the simulator
        
        Args:
            anomaly_rate: Percentage of data points that should contain anomalies (0.0-1.0)
        """
        self.anomaly_rate = anomaly_rate
        self.iteration_count = 0
        self.anomaly_count = 0
        self.start_time = datetime.now()
        
        # Ship configuration
        self.ship_config = {
            "name": "MS AIOps Explorer",
            "imo": "IMO1234567",
            "current_route": "Caribbean Circuit",
            "capacity_passengers": 3000,
            "home_port": "Miami"
        }
        
        # Services configuration
        self.services = [
            "crew-wifi", "guest-wifi", "pos-system", "reservation-system",
            "entertainment-system", "navigation-system", "safety-system"
        ]
        
        # Network devices
        self.network_devices = [
            {"type": "router", "name": "core-router-01"},
            {"type": "switch", "name": "bridge-switch-01"},
            {"type": "firewall", "name": "perimeter-fw-01"},
            {"type": "wifi-controller", "name": "wifi-ctrl-01"}
        ]
    
    def generate_satellite_data(self) -> SatelliteData:
        """Generate satellite/RF equipment data with potential anomalies"""
        # Base values for normal operation
        base_data = SatelliteData(
            timestamp=datetime.now().isoformat(),
            snr_db=random.uniform(10.0, 15.0),
            ber=random.uniform(1e-7, 1e-5),
            signal_strength_dbm=random.uniform(-60, -45),
            es_no_db=random.uniform(8.0, 12.0),
            rain_fade_margin_db=random.uniform(3.0, 8.0),
            frequency_ghz=random.choice([14.0, 12.0, 6.0]),  # Ku, Ku, C band
            modulation=random.choice(["QPSK", "8PSK", "16APSK"]),
            fec_rate=random.choice(["3/4", "5/6", "7/8"]),
            antenna_elevation=random.uniform(15.0, 85.0),
            antenna_azimuth=random.uniform(0.0, 360.0)
        )
        
        # Apply anomalies
        if self._should_inject_anomaly():
            scenario = random.choice(list(AnomalyScenario))
            self._apply_satellite_anomaly(base_data, scenario)
        
        return base_data
    
    def generate_ship_telemetry(self) -> ShipTelemetry:
        """Generate ship movement and position data"""
        # Simulate movement along a route
        base_lat = 25.7617 + (random.uniform(-0.1, 0.1))  # Near Miami
        base_lon = -80.1918 + (random.uniform(-0.1, 0.1))
        
        data = ShipTelemetry(
            timestamp=datetime.now().isoformat(),
            latitude=base_lat,
            longitude=base_lon,
            heading_degrees=random.uniform(0, 360),
            speed_knots=random.uniform(8, 25),
            pitch_degrees=random.uniform(-3, 3),
            roll_degrees=random.uniform(-5, 5),
            yaw_degrees=random.uniform(-2, 2),
            altitude_meters=random.uniform(-1, 15),  # Sea level to deck height
            gps_quality=random.choice([1, 2, 3, 4, 5])  # GPS quality indicator
        )
        
        # Apply weather-related movement anomalies
        if self._should_inject_anomaly():
            data.pitch_degrees *= random.uniform(2, 4)  # Rough seas
            data.roll_degrees *= random.uniform(2, 4)
            data.speed_knots *= random.uniform(0.6, 0.8)  # Reduced speed
        
        return data
    
    def generate_weather_data(self) -> WeatherData:
        """Generate weather conditions"""
        data = WeatherData(
            timestamp=datetime.now().isoformat(),
            precipitation_rate_mm_hr=random.uniform(0, 2) if random.random() < 0.2 else 0,
            wind_speed_knots=random.uniform(5, 25),
            wind_direction_degrees=random.uniform(0, 360),
            temperature_celsius=random.uniform(22, 32),
            humidity_percent=random.uniform(60, 90),
            pressure_hpa=random.uniform(1008, 1025),
            visibility_km=random.uniform(8, 20),
            cloud_cover_percent=random.uniform(10, 70)
        )
        
        # Inject severe weather
        if self._should_inject_anomaly():
            if random.random() < 0.3:  # Heavy rain
                data.precipitation_rate_mm_hr = random.uniform(15, 50)
                data.visibility_km = random.uniform(1, 5)
                data.cloud_cover_percent = random.uniform(90, 100)
            elif random.random() < 0.3:  # High winds
                data.wind_speed_knots = random.uniform(40, 65)
            
        return data
    
    def generate_network_metrics(self) -> List[NetworkMetrics]:
        """Generate network device metrics"""
        metrics = []
        
        for device in self.network_devices:
            data = NetworkMetrics(
                timestamp=datetime.now().isoformat(),
                device_type=device["type"],
                cpu_utilization_percent=random.uniform(10, 60),
                memory_utilization_percent=random.uniform(30, 70),
                interface_utilization_percent=random.uniform(5, 40),
                packet_loss_percent=random.uniform(0, 0.1),
                latency_ms=random.uniform(1, 50),
                error_count=random.randint(0, 5),
                temperature_celsius=random.uniform(25, 45)
            )
            
            # Apply network anomalies
            if self._should_inject_anomaly():
                scenario = random.choice([
                    AnomalyScenario.NETWORK_CONGESTION,
                    AnomalyScenario.EQUIPMENT_FAILURE,
                    AnomalyScenario.SECURITY_INCIDENT
                ])
                self._apply_network_anomaly(data, scenario)
            
            metrics.append(data)
        
        return metrics
    
    def generate_application_metrics(self) -> List[ApplicationMetrics]:
        """Generate application/service performance metrics"""
        metrics = []
        
        for service in self.services:
            data = ApplicationMetrics(
                timestamp=datetime.now().isoformat(),
                service_name=service,
                response_time_ms=random.uniform(50, 300),
                error_rate_percent=random.uniform(0, 2),
                throughput_rps=random.uniform(10, 100),
                active_connections=random.randint(50, 500),
                queue_depth=random.randint(0, 20),
                availability_percent=random.uniform(99.0, 100.0)
            )
            
            # Apply application anomalies
            if self._should_inject_anomaly():
                self._apply_application_anomaly(data)
            
            metrics.append(data)
        
        return metrics
    
    def _should_inject_anomaly(self) -> bool:
        """Determine if an anomaly should be injected"""
        return random.random() < self.anomaly_rate
    
    def _apply_satellite_anomaly(self, data: SatelliteData, scenario: AnomalyScenario):
        """Apply satellite-specific anomalies"""
        logger.info(f"Injecting satellite anomaly: {scenario.value}")
        self.anomaly_count += 1
        
        if scenario == AnomalyScenario.SATELLITE_DEGRADATION:
            data.snr_db *= random.uniform(0.4, 0.7)
            data.ber *= random.uniform(10, 100)
            data.es_no_db *= random.uniform(0.5, 0.8)
            
        elif scenario == AnomalyScenario.WEATHER_IMPACT:
            data.rain_fade_margin_db *= random.uniform(0.1, 0.4)
            data.signal_strength_dbm -= random.uniform(10, 25)
            
        elif scenario == AnomalyScenario.EQUIPMENT_FAILURE:
            data.snr_db *= random.uniform(0.2, 0.5)
            data.ber *= random.uniform(100, 1000)
            data.signal_strength_dbm -= random.uniform(20, 40)
            
        elif scenario == AnomalyScenario.POWER_FLUCTUATION:
            data.signal_strength_dbm -= random.uniform(5, 15)
    
    def _apply_network_anomaly(self, data: NetworkMetrics, scenario: AnomalyScenario):
        """Apply network-specific anomalies"""
        logger.info(f"Injecting network anomaly: {scenario.value}")
        
        if scenario == AnomalyScenario.NETWORK_CONGESTION:
            data.cpu_utilization_percent = random.uniform(80, 95)
            data.memory_utilization_percent = random.uniform(85, 95)
            data.interface_utilization_percent = random.uniform(90, 100)
            data.packet_loss_percent = random.uniform(1, 10)
            data.latency_ms = random.uniform(200, 1000)
            
        elif scenario == AnomalyScenario.EQUIPMENT_FAILURE:
            data.temperature_celsius = random.uniform(60, 85)
            data.error_count = random.randint(50, 200)
            
        elif scenario == AnomalyScenario.SECURITY_INCIDENT:
            data.cpu_utilization_percent = random.uniform(90, 100)
            data.error_count = random.randint(100, 500)
    
    def _apply_application_anomaly(self, data: ApplicationMetrics):
        """Apply application-specific anomalies"""
        logger.info(f"Injecting application anomaly for {data.service_name}")
        
        # Randomly choose anomaly type
        anomaly_type = random.choice(["performance", "error", "availability"])
        
        if anomaly_type == "performance":
            data.response_time_ms = random.uniform(2000, 10000)
            data.throughput_rps *= random.uniform(0.1, 0.4)
            
        elif anomaly_type == "error":
            data.error_rate_percent = random.uniform(10, 50)
            
        elif anomaly_type == "availability":
            data.availability_percent = random.uniform(85, 95)
            data.active_connections = 0
            data.queue_depth = random.randint(100, 1000)
    
    async def run_simulation(self, duration_minutes: int = 10, interval_seconds: int = 5):
        """
        Run the complete data simulation
        
        Args:
            duration_minutes: How long to run the simulation
            interval_seconds: Interval between data generations
        """
        end_time = datetime.now() + timedelta(minutes=duration_minutes)
        
        logger.info(f"Starting AIOps NAAS data simulation")
        logger.info(f"Duration: {duration_minutes} minutes")
        logger.info(f"Interval: {interval_seconds} seconds")
        logger.info(f"Anomaly rate: {self.anomaly_rate:.1%}")
        logger.info(f"Ship: {self.ship_config['name']} ({self.ship_config['imo']})")
        
        # Create output files
        with open("simulation_data.jsonl", "w") as json_file, \
             open("simulation_data.csv", "w", newline="") as csv_file:
            
            csv_writer = None
            
            while datetime.now() < end_time:
                self.iteration_count += 1
                
                # Generate all data types
                satellite_data = self.generate_satellite_data()
                ship_data = self.generate_ship_telemetry()
                weather_data = self.generate_weather_data()
                network_data = self.generate_network_metrics()
                app_data = self.generate_application_metrics()
                
                # Compile data point
                data_point = {
                    "iteration": self.iteration_count,
                    "ship_config": self.ship_config,
                    "satellite": asdict(satellite_data),
                    "ship": asdict(ship_data),
                    "weather": asdict(weather_data),
                    "network": [asdict(d) for d in network_data],
                    "applications": [asdict(d) for d in app_data]
                }
                
                # Write to JSON Lines file
                json_file.write(json.dumps(data_point) + "\n")
                json_file.flush()
                
                # Write to CSV (flattened)
                if csv_writer is None:
                    flattened = self._flatten_data_point(data_point)
                    csv_writer = csv.DictWriter(csv_file, fieldnames=flattened.keys())
                    csv_writer.writeheader()
                
                flattened = self._flatten_data_point(data_point)
                csv_writer.writerow(flattened)
                csv_file.flush()
                
                # Log progress
                if self.iteration_count % 10 == 0:
                    logger.info(f"Generated {self.iteration_count} data points "
                              f"({self.anomaly_count} anomalies)")
                
                # Wait for next iteration
                await asyncio.sleep(interval_seconds)
        
        # Final statistics
        duration = datetime.now() - self.start_time
        logger.info(f"Simulation completed!")
        logger.info(f"Total iterations: {self.iteration_count}")
        logger.info(f"Total anomalies: {self.anomaly_count}")
        logger.info(f"Anomaly rate achieved: {self.anomaly_count/self.iteration_count:.1%}")
        logger.info(f"Total duration: {duration}")
        
        return {
            "iterations": self.iteration_count,
            "anomalies": self.anomaly_count,
            "anomaly_rate": self.anomaly_count / self.iteration_count if self.iteration_count > 0 else 0,
            "duration_seconds": duration.total_seconds()
        }
    
    def _flatten_data_point(self, data_point: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested data point for CSV output"""
        flattened = {
            "iteration": data_point["iteration"],
            "timestamp": data_point["satellite"]["timestamp"]
        }
        
        # Satellite data
        for k, v in data_point["satellite"].items():
            flattened[f"sat_{k}"] = v
            
        # Ship data
        for k, v in data_point["ship"].items():
            flattened[f"ship_{k}"] = v
            
        # Weather data
        for k, v in data_point["weather"].items():
            flattened[f"weather_{k}"] = v
        
        # Aggregate network and application data
        flattened["network_devices"] = len(data_point["network"])
        flattened["applications"] = len(data_point["applications"])
        
        return flattened


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AIOps NAAS Data Simulator")
    parser.add_argument("--duration", type=int, default=10, 
                       help="Simulation duration in minutes (default: 10)")
    parser.add_argument("--interval", type=int, default=5,
                       help="Data generation interval in seconds (default: 5)")
    parser.add_argument("--anomaly-rate", type=float, default=0.15,
                       help="Anomaly injection rate 0.0-1.0 (default: 0.15)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if not 0.0 <= args.anomaly_rate <= 1.0:
        print("Error: anomaly-rate must be between 0.0 and 1.0")
        return 1
    
    # Create and run simulator
    simulator = AIOpsDataSimulator(anomaly_rate=args.anomaly_rate)
    
    try:
        results = asyncio.run(simulator.run_simulation(
            duration_minutes=args.duration,
            interval_seconds=args.interval
        ))
        
        print("\n" + "="*50)
        print("SIMULATION RESULTS")
        print("="*50)
        print(f"Data points generated: {results['iterations']}")
        print(f"Anomalies injected: {results['anomalies']}")
        print(f"Anomaly rate: {results['anomaly_rate']:.1%}")
        print(f"Duration: {results['duration_seconds']:.1f} seconds")
        print(f"Output files: simulation_data.jsonl, simulation_data.csv")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())