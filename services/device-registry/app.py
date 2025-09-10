#!/usr/bin/env python3
"""
Device Registry & Mapping Service
Maintains hostname → ship_id mappings and device inventory for AIOps NAAS platform
"""

import os
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn


# Pydantic models for API
class Ship(BaseModel):
    ship_id: str = Field(..., description="Unique ship identifier")
    name: str = Field(..., description="Human-readable ship name")
    fleet_id: Optional[str] = Field(None, description="Fleet identifier")
    location: Optional[str] = Field(None, description="Current location")
    status: str = Field(default="active", description="Ship status")


class Device(BaseModel):
    device_id: str = Field(..., description="Auto-generated device identifier")
    hostname: str = Field(..., description="System hostname or IP address")
    ship_id: str = Field(..., description="Associated ship identifier")
    device_type: str = Field(..., description="Device category")
    vendor: Optional[str] = Field(None, description="Device vendor/manufacturer")
    model: Optional[str] = Field(None, description="Device model")
    location: Optional[str] = Field(None, description="Physical location on ship")
    capabilities: Optional[List[str]] = Field(default=[], description="Device capabilities")


class HostnameMapping(BaseModel):
    hostname: str = Field(..., description="System hostname or IP address")
    ship_id: str = Field(..., description="Mapped ship identifier")
    device_id: str = Field(..., description="Associated device identifier")
    device_type: str = Field(..., description="Device type classification")
    last_seen: datetime = Field(default_factory=datetime.utcnow, description="Last activity timestamp")


class RegistrationRequest(BaseModel):
    hostname: str = Field(..., description="Primary hostname or IP to register")
    ship_id: str = Field(..., description="Ship to associate with")
    device_type: str = Field(..., description="Type of device")
    vendor: Optional[str] = Field(None, description="Device vendor")
    model: Optional[str] = Field(None, description="Device model")
    location: Optional[str] = Field(None, description="Location on ship")
    additional_identifiers: Optional[List[str]] = Field(default=[], description="Additional hostnames/IPs for this device")


# Database management
class DeviceRegistryDB:
    def __init__(self, db_path: str = "/app/data/device_registry.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            # Ships table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ships (
                    ship_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    fleet_id TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Devices table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    hostname TEXT UNIQUE NOT NULL,
                    ship_id TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    vendor TEXT,
                    model TEXT,
                    location TEXT,
                    capabilities TEXT, -- JSON array as string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ship_id) REFERENCES ships (ship_id)
                )
            """)
            
            # Hostname mappings table for quick lookups
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hostname_mappings (
                    hostname TEXT PRIMARY KEY,
                    ship_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    device_type TEXT NOT NULL,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ship_id) REFERENCES ships (ship_id),
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            """)
            
            # Indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_ship_id ON devices (ship_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hostname_mappings_ship_id ON hostname_mappings (ship_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_type ON devices (device_type)")
            
            conn.commit()

    def create_ship(self, ship: Ship) -> bool:
        """Create a new ship record"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO ships (ship_id, name, fleet_id, location, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (ship.ship_id, ship.name, ship.fleet_id, ship.location, ship.status))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def register_device(self, hostname: str, ship_id: str, device_type: str,
                       vendor: Optional[str] = None, model: Optional[str] = None,
                       location: Optional[str] = None, additional_identifiers: Optional[List[str]] = None) -> Optional[str]:
        """Register a new device and create hostname mapping(s)"""
        device_id = f"dev_{uuid.uuid4().hex[:12]}"
        
        try:
            with self.get_connection() as conn:
                # Insert device
                conn.execute("""
                    INSERT INTO devices (device_id, hostname, ship_id, device_type, vendor, model, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (device_id, hostname, ship_id, device_type, vendor, model, location))
                
                # Insert primary hostname mapping
                conn.execute("""
                    INSERT OR REPLACE INTO hostname_mappings (hostname, ship_id, device_id, device_type, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                """, (hostname, ship_id, device_id, device_type, datetime.utcnow()))
                
                # Insert additional identifier mappings (e.g., IP addresses)
                if additional_identifiers:
                    for identifier in additional_identifiers:
                        if identifier and identifier != hostname:  # Avoid duplicates
                            conn.execute("""
                                INSERT OR REPLACE INTO hostname_mappings (hostname, ship_id, device_id, device_type, last_seen)
                                VALUES (?, ?, ?, ?, ?)
                            """, (identifier, ship_id, device_id, device_type, datetime.utcnow()))
                
                conn.commit()
                return device_id
        except sqlite3.IntegrityError:
            return None

    def lookup_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Lookup ship_id and device info by hostname or IP address"""
        with self.get_connection() as conn:
            # First try exact match
            result = conn.execute("""
                SELECT hm.ship_id, hm.device_id, hm.device_type, 
                       d.vendor, d.model, d.location, s.name as ship_name,
                       hm.hostname as matched_identifier
                FROM hostname_mappings hm
                JOIN devices d ON hm.device_id = d.device_id
                JOIN ships s ON hm.ship_id = s.ship_id
                WHERE hm.hostname = ?
            """, (hostname,)).fetchone()
            
            # If no exact match and input looks like IP, try to find by device hostname pattern
            if not result and self._is_ip_address(hostname):
                # Try to find devices where hostname contains this IP or similar pattern
                result = conn.execute("""
                    SELECT hm.ship_id, hm.device_id, hm.device_type, 
                           d.vendor, d.model, d.location, s.name as ship_name,
                           hm.hostname as matched_identifier
                    FROM hostname_mappings hm
                    JOIN devices d ON hm.device_id = d.device_id
                    JOIN ships s ON hm.ship_id = s.ship_id
                    WHERE hm.hostname LIKE ? OR d.hostname LIKE ?
                    LIMIT 1
                """, (f"%{hostname}%", f"%{hostname}%")).fetchone()
            
            if result:
                return dict(result)
            return None

    def _is_ip_address(self, hostname: str) -> bool:
        """Check if the hostname string looks like an IP address"""
        try:
            import ipaddress
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def update_last_seen(self, hostname: str):
        """Update last_seen timestamp for hostname"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE hostname_mappings 
                SET last_seen = ?
                WHERE hostname = ?
            """, (datetime.utcnow(), hostname))
            conn.commit()

    def list_ships(self) -> List[Dict[str, Any]]:
        """List all ships"""
        with self.get_connection() as conn:
            results = conn.execute("SELECT * FROM ships ORDER BY ship_id").fetchall()
            return [dict(row) for row in results]

    def list_devices(self, ship_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List devices, optionally filtered by ship_id"""
        with self.get_connection() as conn:
            if ship_id:
                results = conn.execute("""
                    SELECT d.*, s.name as ship_name 
                    FROM devices d
                    JOIN ships s ON d.ship_id = s.ship_id
                    WHERE d.ship_id = ?
                    ORDER BY d.device_type, d.hostname
                """, (ship_id,)).fetchall()
            else:
                results = conn.execute("""
                    SELECT d.*, s.name as ship_name 
                    FROM devices d
                    JOIN ships s ON d.ship_id = s.ship_id
                    ORDER BY d.ship_id, d.device_type, d.hostname
                """, ).fetchall()
            
            # Enrich with all identifiers for each device
            devices = []
            for row in results:
                device = dict(row)
                # Get all identifiers for this device
                identifiers = conn.execute("""
                    SELECT hostname FROM hostname_mappings WHERE device_id = ?
                """, (device['device_id'],)).fetchall()
                device['all_identifiers'] = [id_row['hostname'] for id_row in identifiers]
                devices.append(device)
            
            return devices

    def get_device_identifiers(self, device_id: str) -> List[str]:
        """Get all identifiers (hostnames/IPs) for a device"""
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT hostname FROM hostname_mappings WHERE device_id = ?
            """, (device_id,)).fetchall()
            return [row['hostname'] for row in results]


# FastAPI app
app = FastAPI(
    title="Device Registry & Mapping Service",
    description="Manages hostname → ship_id mappings and device inventory for AIOps NAAS",
    version="1.0.0"
)

# Database instance
db = DeviceRegistryDB()


# Dependency to get database
def get_db():
    return db


# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "device-registry", "timestamp": datetime.utcnow()}


@app.post("/ships", response_model=Dict[str, Any])
async def create_ship(ship: Ship, db: DeviceRegistryDB = Depends(get_db)):
    """Create a new ship"""
    if db.create_ship(ship):
        return {"success": True, "ship_id": ship.ship_id, "message": "Ship created successfully"}
    else:
        raise HTTPException(status_code=400, detail="Ship ID already exists")


@app.get("/ships", response_model=List[Dict[str, Any]])
async def list_ships(db: DeviceRegistryDB = Depends(get_db)):
    """List all ships"""
    return db.list_ships()


@app.post("/devices/register", response_model=Dict[str, Any])
async def register_device(request: RegistrationRequest, db: DeviceRegistryDB = Depends(get_db)):
    """Register a new device with hostname mapping and optional additional identifiers"""
    device_id = db.register_device(
        hostname=request.hostname,
        ship_id=request.ship_id,
        device_type=request.device_type,
        vendor=request.vendor,
        model=request.model,
        location=request.location,
        additional_identifiers=request.additional_identifiers
    )
    
    if device_id:
        identifiers_registered = [request.hostname] + (request.additional_identifiers or [])
        return {
            "success": True,
            "device_id": device_id,
            "hostname": request.hostname,
            "ship_id": request.ship_id,
            "identifiers_registered": identifiers_registered,
            "message": f"Device registered successfully with {len(identifiers_registered)} identifier(s)"
        }
    else:
        raise HTTPException(status_code=400, detail="One or more identifiers already exist or ship_id not found")


@app.get("/devices", response_model=List[Dict[str, Any]])
async def list_devices(ship_id: Optional[str] = None, db: DeviceRegistryDB = Depends(get_db)):
    """List devices, optionally filtered by ship_id"""
    return db.list_devices(ship_id)


@app.get("/lookup/{hostname}", response_model=Dict[str, Any])
async def lookup_hostname(hostname: str, db: DeviceRegistryDB = Depends(get_db)):
    """Lookup ship_id and device info by hostname"""
    result = db.lookup_hostname(hostname)
    if result:
        # Update last_seen timestamp
        db.update_last_seen(hostname)
        return {
            "success": True,
            "hostname": hostname,
            "mapping": result
        }
    else:
        raise HTTPException(status_code=404, detail="Hostname not found in registry")


@app.post("/lookup/{hostname}/update-last-seen")
async def update_last_seen(hostname: str, db: DeviceRegistryDB = Depends(get_db)):
    """Update last_seen timestamp for hostname"""
    result = db.lookup_hostname(hostname)
    if result:
        db.update_last_seen(hostname)
        return {"success": True, "hostname": hostname, "last_seen": datetime.utcnow()}
    else:
        raise HTTPException(status_code=404, detail="Hostname not found in registry")


@app.get("/devices/{device_id}/identifiers", response_model=Dict[str, Any])
async def get_device_identifiers(device_id: str, db: DeviceRegistryDB = Depends(get_db)):
    """Get all identifiers (hostnames/IPs) for a device"""
    identifiers = db.get_device_identifiers(device_id)
    if identifiers:
        return {
            "success": True,
            "device_id": device_id,
            "identifiers": identifiers,
            "count": len(identifiers)
        }
    else:
        raise HTTPException(status_code=404, detail="Device not found")


@app.get("/stats", response_model=Dict[str, Any])
async def get_stats(db: DeviceRegistryDB = Depends(get_db)):
    """Get registry statistics"""
    ships = db.list_ships()
    devices = db.list_devices()
    
    device_types = {}
    ship_device_counts = {}
    
    for device in devices:
        device_type = device['device_type']
        ship_id = device['ship_id']
        
        device_types[device_type] = device_types.get(device_type, 0) + 1
        ship_device_counts[ship_id] = ship_device_counts.get(ship_id, 0) + 1
    
    return {
        "total_ships": len(ships),
        "total_devices": len(devices),
        "device_types": device_types,
        "ship_device_counts": ship_device_counts,
        "timestamp": datetime.utcnow()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)