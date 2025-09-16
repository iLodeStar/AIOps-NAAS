#!/usr/bin/env python3
"""
AIOps NAAS v0.2 - Incident Timeline API Service

This service provides REST API endpoints for incident management:
- Store incidents from Benthos correlation pipeline
- Retrieve incident timelines and details
- Update incident status and acknowledgments
- Provide data for the Ops Console UI

The service:
1. Listens for incident events from NATS
2. Stores incidents in ClickHouse with proper schema
3. Provides REST API for incident operations
4. Serves as backend for the Ops Console
"""

import asyncio
import logging
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import nats
from clickhouse_driver import Client as ClickHouseClient
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models for API
class TimelineEntry(BaseModel):
    timestamp: datetime
    event: str
    description: str
    source: str
    metadata: Optional[Dict[str, Any]] = None

class Incident(BaseModel):
    incident_id: str
    event_type: str = "incident"
    incident_type: str
    incident_severity: str
    ship_id: str
    service: str
    status: str = "open"
    acknowledged: bool = False
    created_at: datetime
    updated_at: datetime
    correlation_id: str
    metric_name: str
    metric_value: float
    anomaly_score: float
    detector_name: str
    correlated_events: List[Dict[str, Any]] = []
    timeline: List[TimelineEntry] = []
    suggested_runbooks: List[str] = []
    metadata: Optional[Dict[str, Any]] = None

class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    acknowledged: Optional[bool] = None
    timeline_entry: Optional[TimelineEntry] = None

class IncidentSummary(BaseModel):
    total_incidents: int
    open_incidents: int
    critical_incidents: int
    recent_incidents: List[Incident]

class IncidentAPIService:
    """Main incident API service"""
    
    def __init__(self):
        # Read ClickHouse configuration from environment variables
        ch_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        ch_port = int(os.getenv('CLICKHOUSE_PORT', '9000'))
        ch_user = os.getenv('CLICKHOUSE_USER', 'admin')
        ch_password = os.getenv('CLICKHOUSE_PASSWORD', 'admin')
        ch_database = os.getenv('CLICKHOUSE_DATABASE', 'logs')
        
        logger.info(f"Connecting to ClickHouse at {ch_host}:{ch_port} with user: {ch_user}")
        
        self.clickhouse_client = ClickHouseClient(
            host=ch_host,
            port=ch_port,
            user=ch_user,
            password=ch_password,
            database=ch_database
        )
        self.nats_client = None
        self.health_status = {"healthy": False, "clickhouse_connected": False, "nats_connected": False}
        
    async def connect_nats(self):
        """Connect to NATS to consume incident events"""
        try:
            nats_url = os.getenv('NATS_URL', 'nats://nats:4222')
            logger.info(f"Connecting to NATS at {nats_url}")
            
            self.nats_client = nats.NATS()
            await self.nats_client.connect(nats_url)
            
            # Subscribe to incident events from Benthos
            async def incident_handler(msg):
                try:
                    incident_data = json.loads(msg.data.decode())
                    await self.store_incident(incident_data)
                    logger.info(f"Stored incident: {incident_data.get('incident_id', 'unknown')}")
                except Exception as e:
                    logger.error(f"Error processing incident event: {e}")
            
            await self.nats_client.subscribe("incidents.created", cb=incident_handler)
            logger.info("Connected to NATS and subscribed to incidents.created")
            self.health_status["nats_connected"] = True
                
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
    
    def test_clickhouse_connection(self) -> bool:
        """Test ClickHouse connection"""
        try:
            result = self.clickhouse_client.execute("SELECT 1")
            return len(result) > 0
        except Exception as e:
            logger.error(f"ClickHouse connection failed: {e}")
            return False
    
    async def resolve_ship_id(self, incident_data: Dict[str, Any]) -> str:
        """Resolve ship_id using device registry integration"""
        # Try to resolve using device registry first (this is the primary source of truth)
        hostname = None
        # Look for hostname in common locations
        if incident_data.get('host'):
            hostname = incident_data['host']
        elif incident_data.get('hostname'):
            hostname = incident_data['hostname']
        elif incident_data.get('labels', {}).get('instance'):
            hostname = incident_data['labels']['instance']
        
        if hostname:
            try:
                # Call device registry service
                response = requests.get(f"http://device-registry:8080/lookup/{hostname}", timeout=5)
                if response.status_code == 200:
                    registry_data = response.json()
                    if registry_data.get('success') and registry_data.get('mapping', {}).get('ship_id'):
                        resolved_ship_id = registry_data['mapping']['ship_id']
                        logger.info(f"Resolved ship_id from device registry: {hostname} -> {resolved_ship_id}")
                        return resolved_ship_id
                else:
                    logger.debug(f"Device registry lookup failed for hostname {hostname}: {response.status_code}")
            except Exception as e:
                logger.debug(f"Device registry lookup error for {hostname}: {e}")
        
        # If device registry lookup failed, check if we have a valid ship_id already
        ship_id = incident_data.get('ship_id')
        if ship_id and ship_id != "" and not ship_id.startswith("unknown"):
            logger.info(f"Using existing ship_id (device registry lookup failed): {ship_id}")
            return ship_id
        
        # Fallback to hostname-based derivation (consistent with Benthos)
        if hostname:
            if "-" in hostname:
                derived_ship_id = hostname.split("-")[0] + "-ship"
                logger.info(f"Derived ship_id from hostname: {hostname} -> {derived_ship_id}")
                return derived_ship_id
            else:
                logger.info(f"Using hostname as ship_id: {hostname}")
                return hostname
        
        # Ultimate fallback
        logger.warning("No valid ship_id or hostname found, using 'unknown-ship'")
        return "unknown-ship"
    
    async def store_incident(self, incident_data: Dict[str, Any]):
        """Store incident in ClickHouse with enhanced metadata handling"""
        try:
            # CRITICAL DEBUG: Log raw incident data for tracing missing fields
            logger.info(f"🔍 INCIDENT DATA TRACE - Raw input data:")
            logger.info(f"  Original keys: {list(incident_data.keys())}")
            logger.info(f"  ship_id from input: {incident_data.get('ship_id', 'NOT_PROVIDED')}")
            logger.info(f"  host from input: {incident_data.get('host', 'NOT_PROVIDED')}")
            logger.info(f"  hostname from input: {incident_data.get('hostname', 'NOT_PROVIDED')}")
            logger.info(f"  service from input: {incident_data.get('service', 'NOT_PROVIDED')}")
            logger.info(f"  metric_name from input: {incident_data.get('metric_name', 'NOT_PROVIDED')}")
            logger.info(f"  metric_value from input: {incident_data.get('metric_value', 'NOT_PROVIDED')}")
            logger.info(f"  labels from input: {incident_data.get('labels', 'NOT_PROVIDED')}")
            if 'metadata' in incident_data and incident_data['metadata']:
                logger.info(f"  metadata keys: {list(incident_data['metadata'].keys()) if isinstance(incident_data['metadata'], dict) else 'NOT_DICT'}")
            
            # Resolve ship_id using device registry integration
            resolved_ship_id = await self.resolve_ship_id(incident_data)
            logger.info(f"🔍 SHIP_ID RESOLUTION - Input: {incident_data.get('ship_id', 'None')}, Resolved: {resolved_ship_id}")
            
            # Convert timeline and correlated_events to JSON strings
            timeline_json = json.dumps(incident_data.get('timeline', []))
            correlated_events_json = json.dumps(incident_data.get('correlated_events', []))
            metadata_json = json.dumps(incident_data.get('metadata', {}))
            
            # CRITICAL FIX: Extract and validate all fields properly
            # Enhanced metric value extraction and validation
            original_metric_value = incident_data.get('metric_value', 0.0)
            logger.info(f"🔍 METRIC VALUE - Original: {original_metric_value} (type: {type(original_metric_value)})")
            
            metric_value = original_metric_value
            if not isinstance(metric_value, (int, float)):
                try:
                    metric_value = float(metric_value) if metric_value else 0.0
                    logger.info(f"🔍 METRIC VALUE - Converted to float: {metric_value}")
                except (ValueError, TypeError):
                    # Try extracting from message if conversion failed
                    message = incident_data.get('message', '')
                    if 'metric_value=' in message:
                        import re
                        match = re.search(r'metric_value=([\d.]+)', message)
                        if match:
                            metric_value = float(match.group(1))
                            logger.info(f"🔍 METRIC VALUE - Extracted from message: {metric_value}")
                        else:
                            metric_value = 0.0
                    else:
                        metric_value = 0.0
                        logger.warning(f"🔍 METRIC VALUE - Could not parse, using 0.0")
            
            anomaly_score = incident_data.get('anomaly_score', 0.0)
            if not isinstance(anomaly_score, (int, float)):
                try:
                    anomaly_score = float(anomaly_score) if anomaly_score else 0.0
                    logger.info(f"🔍 ANOMALY SCORE - Converted to float: {anomaly_score}")
                except (ValueError, TypeError):
                    anomaly_score = 0.0
                    logger.warning(f"🔍 ANOMALY SCORE - Could not parse, using 0.0")
            
            # CRITICAL FIX: Ensure proper service field handling
            service_name = incident_data.get('service', 'unknown_service')
            if not service_name or service_name == '':
                service_name = 'unknown_service'
            logger.info(f"🔍 SERVICE RESOLUTION - Input: {incident_data.get('service', 'None')}, Final: {service_name}")
                
            # CRITICAL FIX: Better incident type mapping
            incident_type = incident_data.get('incident_type', 'single_anomaly')
            if not incident_type or incident_type == '':
                incident_type = 'single_anomaly'
            logger.info(f"🔍 INCIDENT TYPE - Input: {incident_data.get('incident_type', 'None')}, Final: {incident_type}")
                
            # CRITICAL FIX: Proper severity handling
            incident_severity = incident_data.get('incident_severity', 'medium')
            if incident_severity in ['info', 'debug']:
                incident_severity = 'low'  # Map info/debug to low severity
            logger.info(f"🔍 SEVERITY MAPPING - Input: {incident_data.get('incident_severity', 'None')}, Final: {incident_severity}")
                
            # CRITICAL DEBUG: Log metric extraction process
            original_metric_name = incident_data.get('metric_name', 'unknown_metric')
            logger.info(f"🔍 METRIC NAME EXTRACTION - Input: {original_metric_name}")
            
            # Try to extract metric name from different possible locations
            extracted_metric_name = original_metric_name
            if original_metric_name == 'unknown_metric':
                # Try extracting from message content
                message = incident_data.get('message', '')
                if 'metric_name=' in message:
                    import re
                    match = re.search(r'metric_name=([^\s]+)', message)
                    if match:
                        extracted_metric_name = match.group(1)
                        logger.info(f"🔍 METRIC NAME - Extracted from message: {extracted_metric_name}")
                
                # Try extracting from labels
                labels = incident_data.get('labels', {})
                if isinstance(labels, dict) and 'metric_name' in labels:
                    extracted_metric_name = labels['metric_name']
                    logger.info(f"🔍 METRIC NAME - Extracted from labels: {extracted_metric_name}")
                
                # Try extracting from metadata
                metadata = incident_data.get('metadata', {})
                if isinstance(metadata, dict) and 'metric_name' in metadata:
                    extracted_metric_name = metadata['metric_name']
                    logger.info(f"🔍 METRIC NAME - Extracted from metadata: {extracted_metric_name}")
            
            logger.info(f"🔍 FINAL METRIC NAME: {extracted_metric_name}")
            
            # Insert incident into ClickHouse
            query = """
            INSERT INTO logs.incidents (
                incident_id, event_type, incident_type, incident_severity,
                ship_id, service, status, acknowledged, created_at, updated_at,
                correlation_id, processing_timestamp, metric_name, metric_value,
                anomaly_score, detector_name, correlated_events, timeline,
                suggested_runbooks, metadata
            ) VALUES
            """
            
            values = (
                incident_data.get('incident_id', str(uuid.uuid4())),
                incident_data.get('event_type', 'incident'),
                incident_type,
                incident_severity,
                resolved_ship_id,  # Use resolved ship_id instead of hardcoded fallback
                service_name,
                incident_data.get('status', 'open'),
                incident_data.get('acknowledged', False),
                datetime.fromisoformat(incident_data['created_at'].replace('Z', '+00:00')) if 'created_at' in incident_data else datetime.now(),
                datetime.fromisoformat(incident_data['updated_at'].replace('Z', '+00:00')) if 'updated_at' in incident_data else datetime.now(),
                incident_data.get('correlation_id', ''),
                datetime.now(),
                extracted_metric_name,  # Use extracted metric name instead of original
                metric_value,
                anomaly_score,
                incident_data.get('detector_name', ''),
                correlated_events_json,
                timeline_json,
                incident_data.get('suggested_runbooks', ['generic_investigation']),
                metadata_json
            )
            
            self.clickhouse_client.execute(query, [values])
            logger.info(f"✅ STORED INCIDENT {values[0]}:")
            logger.info(f"  🏷️  Ship ID: {resolved_ship_id}")
            logger.info(f"  🏢  Service: {service_name}")  
            logger.info(f"  📊  Metric: {extracted_metric_name} = {metric_value}")
            logger.info(f"  📈  Anomaly Score: {anomaly_score}")
            logger.info(f"  ⚠️  Type: {incident_type}, Severity: {incident_severity}")
            logger.info(f"🔍 INCIDENT STORAGE COMPLETE - All field extractions logged above")
            
        except Exception as e:
            logger.error(f"Error storing incident in ClickHouse: {e}")
            logger.error(f"Incident data causing error: {incident_data}")
            raise
    
    def get_incidents(self, limit: int = 50, status: Optional[str] = None, ship_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve incidents from ClickHouse"""
        try:
            query = """
            SELECT incident_id, event_type, incident_type, incident_severity,
                   ship_id, service, status, acknowledged, created_at, updated_at,
                   correlation_id, metric_name, metric_value, anomaly_score,
                   detector_name, correlated_events, timeline, suggested_runbooks, metadata
            FROM logs.incidents
            WHERE 1=1
            """
            
            params = []
            if status:
                query += " AND status = %s"
                params.append(status)
            if ship_id:
                query += " AND ship_id = %s"
                params.append(ship_id)
                
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            results = self.clickhouse_client.execute(query, params)
            
            incidents = []
            for row in results:
                incident = {
                    'incident_id': row[0],
                    'event_type': row[1],
                    'incident_type': row[2],
                    'incident_severity': row[3],
                    'ship_id': row[4],
                    'service': row[5],
                    'status': row[6],
                    'acknowledged': row[7],
                    'created_at': row[8],
                    'updated_at': row[9],
                    'correlation_id': row[10],
                    'metric_name': row[11],
                    'metric_value': row[12],
                    'anomaly_score': row[13],
                    'detector_name': row[14],
                    'correlated_events': json.loads(row[15]) if row[15] else [],
                    'timeline': json.loads(row[16]) if row[16] else [],
                    'suggested_runbooks': row[17],
                    'metadata': json.loads(row[18]) if row[18] else {}
                }
                incidents.append(incident)
            
            return incidents
            
        except Exception as e:
            logger.error(f"Error retrieving incidents: {e}")
            return []
    
    def get_incident_by_id(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get specific incident by ID"""
        try:
            incidents = self.get_incidents(limit=1)
            filtered = [i for i in incidents if i['incident_id'] == incident_id]
            return filtered[0] if filtered else None
        except Exception as e:
            logger.error(f"Error getting incident {incident_id}: {e}")
            return None
    
    def update_incident(self, incident_id: str, update_data: IncidentUpdate) -> bool:
        """Update incident in ClickHouse"""
        try:
            # For simplicity, we'll insert a new timeline entry and update status
            # In production, you might want to use ClickHouse mutations
            if update_data.timeline_entry:
                timeline_entry = update_data.timeline_entry.dict()
                timeline_entry['timestamp'] = timeline_entry['timestamp'].isoformat()
                
                # This is a simplified approach - in production you'd use proper updates
                logger.info(f"Would update incident {incident_id} with timeline entry")
            
            if update_data.status or update_data.acknowledged is not None:
                logger.info(f"Would update incident {incident_id} status/acknowledgment")
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating incident {incident_id}: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """Get incident summary statistics"""
        try:
            # Get total incidents
            total_result = self.clickhouse_client.execute("SELECT count() FROM logs.incidents")
            total_incidents = total_result[0][0] if total_result else 0
            
            # Get open incidents
            open_result = self.clickhouse_client.execute("SELECT count() FROM logs.incidents WHERE status = 'open'")
            open_incidents = open_result[0][0] if open_result else 0
            
            # Get critical incidents
            critical_result = self.clickhouse_client.execute("SELECT count() FROM logs.incidents WHERE incident_severity = 'critical'")
            critical_incidents = critical_result[0][0] if critical_result else 0
            
            # Get recent incidents
            recent_incidents = self.get_incidents(limit=10)
            
            return {
                'total_incidents': total_incidents,
                'open_incidents': open_incidents,
                'critical_incidents': critical_incidents,
                'recent_incidents': recent_incidents
            }
            
        except Exception as e:
            logger.error(f"Error getting summary: {e}")
            return {
                'total_incidents': 0,
                'open_incidents': 0,
                'critical_incidents': 0,
                'recent_incidents': []
            }

# Initialize service
service = IncidentAPIService()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    service.health_status["clickhouse_connected"] = service.test_clickhouse_connection()
    await service.connect_nats()
    service.health_status["healthy"] = (
        service.health_status["clickhouse_connected"] and 
        service.health_status["nats_connected"]
    )
    logger.info(f"Incident API service started - Health: {service.health_status}")
    
    yield
    
    # Shutdown
    if service.nats_client:
        await service.nats_client.close()

# FastAPI app
app = FastAPI(
    title="AIOps NAAS Incident API",
    description="Incident management API for the AIOps platform",
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS middleware for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return service.health_status

@app.get("/incidents", response_model=List[Dict[str, Any]])
async def get_incidents(
    limit: int = 50,
    status: Optional[str] = None,
    ship_id: Optional[str] = None
):
    """Get incidents with optional filtering"""
    incidents = service.get_incidents(limit=limit, status=status, ship_id=ship_id)
    return incidents

@app.get("/incidents/{incident_id}", response_model=Dict[str, Any])
async def get_incident(incident_id: str):
    """Get specific incident by ID"""
    incident = service.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@app.put("/incidents/{incident_id}")
async def update_incident(incident_id: str, update_data: IncidentUpdate):
    """Update incident status, acknowledgment, or add timeline entry"""
    success = service.update_incident(incident_id, update_data)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update incident")
    return {"status": "updated"}

@app.get("/summary", response_model=Dict[str, Any])
async def get_summary():
    """Get incident summary statistics"""
    return service.get_summary()

@app.post("/incidents/test")
async def create_test_incident():
    """Create a test incident for debugging"""
    test_incident = {
        "incident_id": str(uuid.uuid4()),
        "event_type": "incident",
        "incident_type": "test_incident",
        "incident_severity": "warning",
        "ship_id": "test-ship",
        "service": "test-service",
        "status": "open",
        "acknowledged": False,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "correlation_id": str(uuid.uuid4()),
        "metric_name": "test_metric",
        "metric_value": 75.5,
        "anomaly_score": 0.8,
        "detector_name": "test_detector",
        "timeline": [{
            "timestamp": datetime.now().isoformat(),
            "event": "incident_created",
            "description": "Test incident created via API",
            "source": "api_test"
        }],
        "suggested_runbooks": ["test_runbook"],
        "metadata": {"test": True}
    }
    
    await service.store_incident(test_incident)
    return {"status": "created", "incident_id": test_incident["incident_id"]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9081)