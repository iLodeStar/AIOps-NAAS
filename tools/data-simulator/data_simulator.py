#!/usr/bin/env python3
"""
AIOps NAAS Data Simulator

Generates realistic satellite link telemetry, weather data, and ship navigation data
for testing the AIOps platform. Supports configuration via YAML files and can simulate
various anomaly scenarios.

Usage:
    python3 data_simulator.py --config configs/vendor-integrations.yaml
    python3 data_simulator.py --duration 600 --anomalies --output-format nats
"""

import asyncio
import argparse
import json
import logging
import random
import time
import yaml
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import math
import sys
from pathlib import Path

try:
    from nats.aio.client import Client as NATS
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    print("Warning: NATS not available. Install with: pip install nats-py")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ModemKPIs:
    """Satellite modem Key Performance Indicators"""
    timestamp: datetime
    snr_db: float
    es_no_db: float 
    ber: float
    signal_strength_dbm: float
    rain_fade_margin_db: float
    frequency_offset_hz: float
    elevation_angle_deg: float
    azimuth_angle_deg: float

@dataclass
class WeatherData:
    """Weather conditions affecting satellite link"""
    timestamp: datetime
    precipitation_mm_hr: float
    wind_speed_knots: float
    wind_direction_deg: float
    temperature_c: float
    humidity_percent: float
    visibility_km: float
    cloud_cover_percent: float

@dataclass
class ShipTelemetry:
    """Ship navigation and position data"""
    timestamp: datetime
    latitude: float
    longitude: float
    heading_deg: float
    speed_knots: float
    pitch_deg: float
    roll_deg: float
    course_over_ground_deg: float

class DataSimulator:
    """Main data simulator class"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.nats_client = None
        self.running = False
        self.message_count = 0
        self.anomaly_active = False
        self.anomaly_end_time = None
        
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        default_config = {
            'simulation': {
                'base_distributions': {
                    'modem': {
                        'snr_db': {'mean': 15.0, 'std_dev': 3.0, 'min_value': 5.0, 'max_value': 25.0},
                        'ber': {'base': 1e-6, 'variation_factor': 10.0},
                        'signal_strength_dbm': {'mean': -75.0, 'std_dev': 5.0}
                    },
                    'weather': {
                        'precipitation_mm_hr': {'mean': 0.5, 'std_dev': 2.0, 'max_value': 50.0},
                        'wind_speed_knots': {'mean': 15.0, 'std_dev': 8.0, 'max_value': 60.0}
                    }
                },
                'anomalies': {
                    'probability': 0.1,
                    'types': ['rain_fade', 'equipment_degradation', 'interference', 'weather_storm'],
                    'severity_distribution': {'low': 0.6, 'medium': 0.3, 'high': 0.1}
                },
                'publishing': {
                    'interval_seconds': 5,
                    'jitter_percent': 20,
                    'subjects': [
                        'telemetry.modem.kpis',
                        'telemetry.weather.current', 
                        'telemetry.ship.navigation'
                    ]
                }
            }
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    loaded_config = yaml.safe_load(f)
                    # Merge with defaults
                    if 'simulation' in loaded_config:
                        default_config['simulation'].update(loaded_config['simulation'])
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
                logger.info("Using default configuration")
        else:
            logger.info("Using default configuration")
            
        return default_config
    
    async def connect_nats(self, nats_url: str = "nats://localhost:4222"):
        """Connect to NATS message bus"""
        if not NATS_AVAILABLE:
            logger.warning("NATS not available - messages will be logged only")
            return
            
        try:
            self.nats_client = NATS()
            await self.nats_client.connect(nats_url)
            logger.info(f"Connected to NATS at {nats_url}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.nats_client = None
    
    def _generate_modem_data(self) -> ModemKPIs:
        """Generate realistic modem KPI data"""
        config = self.config['simulation']['base_distributions']['modem']
        
        # Base values with normal distribution
        snr = random.gauss(config['snr_db']['mean'], config['snr_db']['std_dev'])
        snr = max(config['snr_db']['min_value'], min(config['snr_db']['max_value'], snr))
        
        # ES/No typically 3-5 dB higher than SNR for QPSK
        es_no = snr + random.gauss(4.0, 0.5)
        
        # BER correlates inversely with SNR
        ber_config = config['ber']
        ber_base = float(ber_config['base'])  # Ensure it's a float
        if snr < 8:
            ber = ber_base * random.uniform(100, 1000)  # High BER for poor SNR
        elif snr < 12:
            ber = ber_base * random.uniform(10, 100)
        else:
            ber = ber_base * random.uniform(0.1, 10)
            
        signal_strength = random.gauss(
            config['signal_strength_dbm']['mean'],
            config['signal_strength_dbm']['std_dev']
        )
        
        # Apply anomalies if active
        if self.anomaly_active:
            snr *= 0.6  # Degrade SNR during anomaly
            ber *= 10   # Increase BER
            signal_strength -= 10  # Reduce signal strength
        
        return ModemKPIs(
            timestamp=datetime.now(),
            snr_db=round(snr, 1),
            es_no_db=round(es_no, 1),
            ber=max(1e-9, ber),  # Minimum BER floor
            signal_strength_dbm=round(signal_strength, 1),
            rain_fade_margin_db=round(random.uniform(2.0, 8.0), 1),
            frequency_offset_hz=random.randint(-500, 500),
            elevation_angle_deg=round(random.uniform(20, 80), 1),
            azimuth_angle_deg=round(random.uniform(0, 360), 1)
        )
    
    def _generate_weather_data(self) -> WeatherData:
        """Generate realistic weather data"""
        config = self.config['simulation']['base_distributions']['weather']
        
        precip = max(0, random.gauss(
            config['precipitation_mm_hr']['mean'],
            config['precipitation_mm_hr']['std_dev']
        ))
        precip = min(config['precipitation_mm_hr']['max_value'], precip)
        
        wind_speed = max(0, random.gauss(
            config['wind_speed_knots']['mean'], 
            config['wind_speed_knots']['std_dev']
        ))
        wind_speed = min(config['wind_speed_knots']['max_value'], wind_speed)
        
        # Apply weather anomaly (storm)
        if self.anomaly_active and random.random() < 0.3:
            precip *= 5  # Heavy rain during storm
            wind_speed *= 2  # High winds
        
        return WeatherData(
            timestamp=datetime.now(),
            precipitation_mm_hr=round(precip, 1),
            wind_speed_knots=round(wind_speed, 1),
            wind_direction_deg=random.randint(0, 360),
            temperature_c=round(random.uniform(15, 35), 1),
            humidity_percent=random.randint(40, 90),
            visibility_km=round(random.uniform(5, 50), 1),
            cloud_cover_percent=random.randint(0, 100)
        )
    
    def _generate_ship_data(self) -> ShipTelemetry:
        """Generate realistic ship telemetry data"""
        # Simulate a ship on a route (e.g., Miami to Caribbean)
        base_lat = 25.7617  # Miami area
        base_lon = -80.1918
        
        # Add small movements to simulate ship progress
        time_offset = time.time() / 1000  # Slow movement
        lat_offset = math.sin(time_offset) * 0.1
        lon_offset = math.cos(time_offset) * 0.1
        
        return ShipTelemetry(
            timestamp=datetime.now(),
            latitude=round(base_lat + lat_offset, 6),
            longitude=round(base_lon + lon_offset, 6),
            heading_deg=round(random.uniform(180, 200), 1),  # Generally southward
            speed_knots=round(random.uniform(15, 25), 1),
            pitch_deg=round(random.gauss(0, 2), 1),  # Small pitch movements
            roll_deg=round(random.gauss(0, 3), 1),   # Small roll movements
            course_over_ground_deg=round(random.uniform(175, 205), 1)
        )
    
    def _check_anomaly_trigger(self):
        """Check if an anomaly should be triggered"""
        anomaly_config = self.config['simulation']['anomalies']
        
        if not self.anomaly_active and random.random() < anomaly_config['probability'] / 100:
            # Start new anomaly
            self.anomaly_active = True
            duration = random.randint(30, 180)  # 30 seconds to 3 minutes
            self.anomaly_end_time = datetime.now() + timedelta(seconds=duration)
            
            anomaly_type = random.choice(anomaly_config['types'])
            logger.info(f"Starting {anomaly_type} anomaly for {duration} seconds")
            
        elif self.anomaly_active and datetime.now() > self.anomaly_end_time:
            # End current anomaly
            self.anomaly_active = False
            self.anomaly_end_time = None
            logger.info("Anomaly ended")
    
    async def _publish_message(self, subject: str, data: Dict[str, Any]):
        """Publish message to NATS or log if NATS unavailable"""
        message = json.dumps(data, default=str, indent=2)
        
        if self.nats_client:
            try:
                await self.nats_client.publish(subject, message.encode())
                self.message_count += 1
            except Exception as e:
                logger.error(f"Failed to publish to {subject}: {e}")
        else:
            # Log message if NATS unavailable
            logger.info(f"[{subject}] {message}")
    
    async def run_simulation(self, duration_seconds: int = 600, enable_anomalies: bool = False):
        """Run the data simulation for specified duration"""
        logger.info(f"Starting simulation for {duration_seconds} seconds (anomalies: {enable_anomalies})")
        
        self.running = True
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        
        interval_config = self.config['simulation']['publishing']
        base_interval = interval_config['interval_seconds']
        jitter_percent = interval_config['jitter_percent']
        
        try:
            while self.running and datetime.now() < end_time:
                # Check for anomalies if enabled
                if enable_anomalies:
                    self._check_anomaly_trigger()
                
                # Generate and publish data
                modem_data = self._generate_modem_data()
                weather_data = self._generate_weather_data()
                ship_data = self._generate_ship_data()
                
                # Publish to configured subjects
                subjects = interval_config['subjects']
                await self._publish_message(subjects[0], asdict(modem_data))
                await self._publish_message(subjects[1], asdict(weather_data))
                await self._publish_message(subjects[2], asdict(ship_data))
                
                # Additional subjects for link health predictions
                if random.random() < 0.1:  # 10% chance of prediction message
                    prediction = {
                        'timestamp': datetime.now(),
                        'ship_id': 'ship-01',
                        'predicted_quality_score': random.uniform(0.3, 0.95),
                        'degradation_risk_level': random.choice(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
                        'lead_time_minutes': random.randint(5, 30)
                    }
                    await self._publish_message('link.health.prediction', prediction)
                
                # Randomly generate alerts
                if self.anomaly_active and random.random() < 0.3:
                    alert = {
                        'timestamp': datetime.now(),
                        'ship_id': 'ship-01',
                        'alert_type': 'link_degradation',
                        'severity': random.choice(['WARNING', 'CRITICAL']),
                        'description': 'Satellite link quality degraded',
                        'snr_db': modem_data.snr_db,
                        'ber': modem_data.ber
                    }
                    await self._publish_message('link.health.alert', alert)
                
                # Calculate next interval with jitter
                jitter = random.uniform(-jitter_percent/100, jitter_percent/100)
                sleep_time = base_interval * (1 + jitter)
                await asyncio.sleep(sleep_time)
                
                # Log progress every minute
                if self.message_count % (60 // base_interval * 3) == 0:  # ~3 types per interval
                    elapsed = datetime.now() - start_time
                    remaining = end_time - datetime.now()
                    logger.info(f"Elapsed: {elapsed.total_seconds():.0f}s, "
                              f"Remaining: {remaining.total_seconds():.0f}s, "
                              f"Messages: {self.message_count}, "
                              f"Anomaly: {self.anomaly_active}")
                    
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            self.running = False
            logger.info(f"Simulation completed. Total messages sent: {self.message_count}")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.nats_client:
            await self.nats_client.close()
            logger.info("NATS connection closed")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="AIOps NAAS Data Simulator")
    parser.add_argument("--config", help="Path to YAML configuration file")
    parser.add_argument("--duration", type=int, default=600, help="Simulation duration in seconds (default: 600)")
    parser.add_argument("--anomalies", action="store_true", help="Enable random anomaly generation")
    parser.add_argument("--nats-url", default="nats://localhost:4222", help="NATS server URL")
    parser.add_argument("--log-level", default="INFO", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and run simulator
    simulator = DataSimulator(args.config)
    
    # Connect to NATS if available
    await simulator.connect_nats(args.nats_url)
    
    try:
        await simulator.run_simulation(args.duration, args.anomalies)
    finally:
        await simulator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())