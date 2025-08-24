#!/usr/bin/env python3
"""
AIOps NAAS v0.4 - Fleet Data Aggregation Service

This service aggregates data from multiple ships to the core ClickHouse + VictoriaMetrics cluster:
- Simulates periodic replication from ship edge systems to core storage
- Processes ship telemetry, incidents, and capacity metrics  
- Provides fleet-wide data foundation for v0.4 features
- Maintains ship location tracking for mapping

The service:
1. Simulates data from multiple ships (ship-01 through ship-05)  
2. Aggregates logs, metrics, and incidents to core storage
3. Tracks ship positions and routes for mapping
4. Provides API endpoints for fleet data queries
5. Publishes fleet events to NATS for other services
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import random

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel, Field
import uvicorn
import nats
from clickhouse_driver import Client as ClickHouseClient
import requests
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ship fleet configuration
FLEET_SHIPS = [
    {"ship_id": "ship-01", "name": "Caribbean Dream", "route": "Caribbean", "capacity": 3000},
    {"ship_id": "ship-02", "name": "Pacific Explorer", "route": "Alaska", "capacity": 2500}, 
    {"ship_id": "ship-03", "name": "Mediterranean Star", "route": "Mediterranean", "capacity": 3500},
    {"ship_id": "ship-04", "name": "Northern Aurora", "route": "Northern Europe", "capacity": 2800},
    {"ship_id": "ship-05", "name": "Southern Cross", "route": "South Pacific", "capacity": 3200}
]

# Pydantic models
class ShipLocation(BaseModel):
    ship_id: str
    name: str 
    latitude: float
    longitude: float
    heading: float
    speed_knots: float
    route: str
    capacity: int
    occupancy: int
    timestamp: datetime

class FleetSummary(BaseModel):
    total_ships: int
    active_ships: int
    total_capacity: int
    total_occupancy: int  
    average_occupancy_rate: float
    ships_by_route: Dict[str, int]
    timestamp: datetime

class FleetIncidentSummary(BaseModel):
    ship_id: str
    incident_count_24h: int
    critical_incidents: int
    link_quality_avg: float
    last_incident_time: Optional[datetime]

@dataclass
class ShipTelemetry:
    ship_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    heading: float
    speed_knots: float
    link_quality: float
    bandwidth_utilization: float
    passenger_count: int
    cpu_usage: float
    memory_usage: float
    storage_usage: float

class FleetAggregationService:
    """Main fleet data aggregation service"""
    
    def __init__(self):
        self.app = FastAPI(title="Fleet Aggregation Service", version="0.4.0")
        self.setup_middleware()
        self.setup_routes()
        
        # Service dependencies  
        self.clickhouse_client: Optional[ClickHouseClient] = None
        self.nats_client: Optional[nats.NATS] = None
        
        # Fleet state tracking
        self.fleet_locations: Dict[str, ShipLocation] = {}
        self.last_aggregation: Optional[datetime] = None
        
        # Ship route waypoints (simplified for demo)
        self.ship_routes = {
            "ship-01": [(25.7617, -80.1918), (18.2208, -66.5901), (12.0508, -61.7518)],  # Caribbean
            "ship-02": [(58.3019, -134.4197), (60.1763, -149.1027), (61.2181, -149.9003)],  # Alaska
            "ship-03": [(41.9028, 12.4964), (40.4168, 3.7038), (36.7213, -4.4216)],  # Mediterranean  
            "ship-04": [(59.9139, 10.7522), (60.3913, 5.3221), (55.6761, 12.5683)],  # Northern Europe
            "ship-05": [(-17.6509, -149.4260), (-22.2711, -159.5264), (-36.8485, 174.7633)]  # South Pacific
        }
        
    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "service": "fleet-aggregation", 
                "version": "0.4.0",
                "timestamp": datetime.now(timezone.utc),
                "dependencies": {
                    "clickhouse": self.clickhouse_client is not None,
                    "nats": self.nats_client is not None and self.nats_client.is_connected
                }
            }
        
        @self.app.get("/fleet/summary", response_model=FleetSummary)
        async def get_fleet_summary():
            """Get current fleet summary statistics"""
            if not self.fleet_locations:
                await self._generate_current_fleet_positions()
            
            active_ships = len([ship for ship in self.fleet_locations.values() 
                              if ship.timestamp > datetime.now(timezone.utc) - timedelta(minutes=10)])
            
            total_capacity = sum(ship.capacity for ship in self.fleet_locations.values())
            total_occupancy = sum(ship.occupancy for ship in self.fleet_locations.values())
            
            # Count ships by route
            ships_by_route = {}
            for ship in self.fleet_locations.values():
                ships_by_route[ship.route] = ships_by_route.get(ship.route, 0) + 1
            
            return FleetSummary(
                total_ships=len(self.fleet_locations),
                active_ships=active_ships,
                total_capacity=total_capacity,
                total_occupancy=total_occupancy,
                average_occupancy_rate=total_occupancy / total_capacity if total_capacity > 0 else 0.0,
                ships_by_route=ships_by_route,
                timestamp=datetime.now(timezone.utc)
            )
        
        @self.app.get("/fleet/locations", response_model=List[ShipLocation]) 
        async def get_fleet_locations():
            """Get current positions of all ships in the fleet"""
            if not self.fleet_locations:
                await self._generate_current_fleet_positions()
            
            return list(self.fleet_locations.values())
        
        @self.app.get("/fleet/incidents", response_model=List[FleetIncidentSummary])
        async def get_fleet_incidents():
            """Get incident summary across the fleet"""
            # This would typically query ClickHouse for real incident data
            # For v0.4 MVP, returning simulated data
            incidents = []
            for ship_config in FLEET_SHIPS:
                ship_id = ship_config["ship_id"] 
                incidents.append(FleetIncidentSummary(
                    ship_id=ship_id,
                    incident_count_24h=random.randint(0, 5),
                    critical_incidents=random.randint(0, 2),
                    link_quality_avg=random.uniform(0.6, 0.95),
                    last_incident_time=datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 24)) 
                        if random.random() > 0.3 else None
                ))
            return incidents
        
        @self.app.post("/fleet/aggregate")
        async def trigger_aggregation():
            """Manually trigger fleet data aggregation"""
            try:
                await self._run_aggregation_cycle()
                return {
                    "status": "success", 
                    "message": "Fleet data aggregation completed",
                    "timestamp": datetime.now(timezone.utc)
                }
            except Exception as e:
                logger.error(f"Fleet aggregation failed: {e}")
                raise HTTPException(status_code=500, detail=f"Aggregation failed: {e}")
    
    async def initialize_dependencies(self):
        """Initialize external service connections"""
        try:
            # Initialize ClickHouse
            self.clickhouse_client = ClickHouseClient(
                host='clickhouse',
                port=9000,
                user='default', 
                password='clickhouse123',
                database='default'
            )
            
            # Test ClickHouse connection
            self.clickhouse_client.execute("SELECT 1")
            logger.info("ClickHouse connection established")
            
            # Initialize ClickHouse schema for fleet data
            await self._setup_fleet_schema()
            
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            # Continue without ClickHouse for now
        
        try:
            # Initialize NATS
            self.nats_client = await nats.connect("nats://nats:4222")
            logger.info("NATS connection established")
            
        except Exception as e:
            logger.error(f"NATS connection failed: {e}")
            # Continue without NATS for now
    
    async def _setup_fleet_schema(self):
        """Setup ClickHouse tables for fleet data"""
        if not self.clickhouse_client:
            return
            
        # Fleet telemetry table
        fleet_telemetry_ddl = """
        CREATE TABLE IF NOT EXISTS fleet.ship_telemetry (
            timestamp DateTime64(3, 'UTC'),
            ship_id String,
            ship_name String, 
            route String,
            latitude Float64,
            longitude Float64,
            heading Float64,
            speed_knots Float64,
            link_quality Float64,
            bandwidth_utilization Float64,
            passenger_count UInt32,
            cpu_usage Float64,
            memory_usage Float64,  
            storage_usage Float64,
            capacity UInt32
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp) 
        ORDER BY (ship_id, timestamp)
        SETTINGS index_granularity = 8192;
        """
        
        # Fleet capacity history table  
        fleet_capacity_ddl = """
        CREATE TABLE IF NOT EXISTS fleet.capacity_history (
            timestamp DateTime64(3, 'UTC'),
            ship_id String,
            route String,
            capacity UInt32,
            occupancy UInt32,
            occupancy_rate Float64,
            booking_rate Float64,
            revenue_per_passenger Float64
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (ship_id, timestamp)
        SETTINGS index_granularity = 8192;
        """
        
        try:
            # Create database if not exists
            self.clickhouse_client.execute("CREATE DATABASE IF NOT EXISTS fleet")
            
            # Create tables
            self.clickhouse_client.execute(fleet_telemetry_ddl)
            self.clickhouse_client.execute(fleet_capacity_ddl) 
            
            logger.info("Fleet ClickHouse schema initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup fleet schema: {e}")
    
    async def _generate_current_fleet_positions(self):
        """Generate current positions for all ships in fleet"""
        current_time = datetime.now(timezone.utc)
        
        for ship_config in FLEET_SHIPS:
            ship_id = ship_config["ship_id"]
            route_waypoints = self.ship_routes.get(ship_id, [(0.0, 0.0)])
            
            # Pick a random waypoint and add some variation
            base_lat, base_lon = random.choice(route_waypoints)
            
            # Add some realistic movement variation (±0.1 degrees)
            lat = base_lat + random.uniform(-0.1, 0.1)
            lon = base_lon + random.uniform(-0.1, 0.1)
            
            self.fleet_locations[ship_id] = ShipLocation(
                ship_id=ship_id,
                name=ship_config["name"],
                latitude=lat,
                longitude=lon, 
                heading=random.uniform(0, 360),
                speed_knots=random.uniform(12, 22),
                route=ship_config["route"],
                capacity=ship_config["capacity"],
                occupancy=int(ship_config["capacity"] * random.uniform(0.7, 0.95)),
                timestamp=current_time
            )
    
    async def _run_aggregation_cycle(self):
        """Run one cycle of fleet data aggregation"""
        logger.info("Starting fleet data aggregation cycle")
        
        # Update fleet positions
        await self._generate_current_fleet_positions()
        
        # Generate telemetry for each ship
        current_time = datetime.now(timezone.utc)
        telemetry_batch = []
        
        for ship_id, location in self.fleet_locations.items():
            ship_config = next(ship for ship in FLEET_SHIPS if ship["ship_id"] == ship_id)
            
            telemetry = ShipTelemetry(
                ship_id=ship_id,
                timestamp=current_time,
                latitude=location.latitude,
                longitude=location.longitude,
                heading=location.heading,
                speed_knots=location.speed_knots,
                link_quality=random.uniform(0.6, 0.95),
                bandwidth_utilization=random.uniform(0.4, 0.85),
                passenger_count=location.occupancy,
                cpu_usage=random.uniform(30, 80),
                memory_usage=random.uniform(40, 85),
                storage_usage=random.uniform(50, 90)
            )
            
            telemetry_batch.append(telemetry)
        
        # Insert telemetry to ClickHouse
        if self.clickhouse_client:
            await self._insert_fleet_telemetry(telemetry_batch)
        
        # Publish fleet update to NATS
        if self.nats_client:
            fleet_summary = {
                "total_ships": len(self.fleet_locations),
                "active_ships": len(self.fleet_locations),
                "timestamp": current_time.isoformat(),
                "ships": [asdict(location) for location in self.fleet_locations.values()]
            }
            
            await self.nats_client.publish("fleet.status", json.dumps(fleet_summary, default=str).encode())
        
        self.last_aggregation = current_time
        logger.info(f"Fleet aggregation cycle completed at {current_time}")
    
    async def _insert_fleet_telemetry(self, telemetry_batch: List[ShipTelemetry]):
        """Insert fleet telemetry batch to ClickHouse"""
        if not self.clickhouse_client or not telemetry_batch:
            return
            
        try:
            # Prepare data for insertion
            data = []
            for telemetry in telemetry_batch:
                ship_config = next(ship for ship in FLEET_SHIPS if ship["ship_id"] == telemetry.ship_id)
                data.append((
                    telemetry.timestamp,
                    telemetry.ship_id,
                    ship_config["name"],
                    ship_config["route"],
                    telemetry.latitude,
                    telemetry.longitude,
                    telemetry.heading,
                    telemetry.speed_knots,
                    telemetry.link_quality,
                    telemetry.bandwidth_utilization,
                    telemetry.passenger_count,
                    telemetry.cpu_usage,
                    telemetry.memory_usage, 
                    telemetry.storage_usage,
                    ship_config["capacity"]
                ))
            
            # Insert batch
            self.clickhouse_client.execute(
                """
                INSERT INTO fleet.ship_telemetry (
                    timestamp, ship_id, ship_name, route, latitude, longitude, heading, speed_knots,
                    link_quality, bandwidth_utilization, passenger_count, cpu_usage, memory_usage,
                    storage_usage, capacity  
                ) VALUES
                """, 
                data
            )
            
            logger.info(f"Inserted {len(data)} telemetry records to ClickHouse")
            
        except Exception as e:
            logger.error(f"Failed to insert fleet telemetry: {e}")
    
    async def start_background_aggregation(self):
        """Start background task for periodic fleet data aggregation"""
        async def aggregation_worker():
            while True:
                try:
                    await self._run_aggregation_cycle()
                    # Run every 2 minutes for testing, would be longer in production
                    await asyncio.sleep(120)
                except Exception as e:
                    logger.error(f"Background aggregation error: {e}")
                    await asyncio.sleep(30)  # Shorter retry on error
        
        # Start the background task
        asyncio.create_task(aggregation_worker())

# Global service instance
service = FleetAggregationService()

@service.app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("Starting Fleet Aggregation Service v0.4.0")
    await service.initialize_dependencies()
    await service.start_background_aggregation()
    logger.info("Fleet Aggregation Service started successfully")

@service.app.on_event("shutdown") 
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Fleet Aggregation Service")
    if service.nats_client:
        await service.nats_client.close()

if __name__ == "__main__":
    uvicorn.run(
        "fleet_aggregation_service:service.app",
        host="0.0.0.0", 
        port=8084,
        log_level="info",
        access_log=True
    )