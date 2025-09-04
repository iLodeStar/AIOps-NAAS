#!/usr/bin/env python3
"""
AIOps NAAS - Data Flow Visualization Service

This service provides real-time visualization of data flow through the entire 
AIOps pipeline with traceability and performance metrics.

Features:
- Real-time data journey tracking
- Pipeline health monitoring
- Performance metrics visualization
- Data lineage tracking
- Interactive flow diagrams
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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

@dataclass
class DataFlowEvent:
    """Data flow tracking event"""
    event_id: str
    tracking_id: str
    stage: str
    component: str
    timestamp: datetime
    status: str  # 'received', 'processing', 'completed', 'error'
    data_size: int
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata or {}
        }

@dataclass
class PipelineStage:
    """Pipeline stage configuration"""
    name: str
    component: str
    input_sources: List[str]
    output_destinations: List[str]
    expected_throughput: float  # events per second
    expected_latency_ms: float
    health_endpoint: Optional[str] = None

class DataFlowTracker:
    """Tracks data flow through the pipeline"""
    
    def __init__(self):
        self.flow_events = deque(maxlen=10000)  # Recent events
        self.active_traces = {}  # tracking_id -> flow events
        self.stage_metrics = defaultdict(lambda: {
            'events_processed': 0,
            'avg_latency_ms': 0.0,
            'error_count': 0,
            'throughput_per_minute': 0.0,
            'last_activity': None
        })
        
        # Define pipeline stages
        self.pipeline_stages = [
            PipelineStage(
                name="Data Ingestion",
                component="vector",
                input_sources=["syslog_udp", "syslog_tcp", "host_metrics", "snmp", "file_logs"],
                output_destinations=["clickhouse", "nats_anomalous"],
                expected_throughput=100.0,
                expected_latency_ms=50.0,
                health_endpoint="http://vector:8686/health"
            ),
            PipelineStage(
                name="Data Storage",
                component="clickhouse",
                input_sources=["vector"],
                output_destinations=["queries"],
                expected_throughput=100.0,
                expected_latency_ms=20.0,
                health_endpoint="http://clickhouse:8123/ping"
            ),
            PipelineStage(
                name="Anomaly Detection",
                component="anomaly-detection",
                input_sources=["victoria-metrics", "nats_anomalous"],
                output_destinations=["nats_anomalies"],
                expected_throughput=10.0,
                expected_latency_ms=500.0,
                health_endpoint="http://anomaly-detection:8083/health"
            ),
            PipelineStage(
                name="Event Correlation",
                component="benthos",
                input_sources=["nats_anomalies"],
                output_destinations=["nats_incidents"],
                expected_throughput=5.0,
                expected_latency_ms=200.0,
                health_endpoint="http://benthos:4195/ready"
            ),
            PipelineStage(
                name="Incident Management",
                component="incident-api",
                input_sources=["nats_incidents"],
                output_destinations=["clickhouse_incidents"],
                expected_throughput=5.0,
                expected_latency_ms=100.0,
                health_endpoint="http://incident-api:8085/health"
            ),
            PipelineStage(
                name="User Explanation",
                component="incident-explanation",
                input_sources=["clickhouse_incidents"],
                output_destinations=["dashboard"],
                expected_throughput=2.0,
                expected_latency_ms=1000.0,
                health_endpoint="http://incident-explanation:8087/health"
            )
        ]
    
    def add_flow_event(self, event: DataFlowEvent):
        """Add a new flow event"""
        self.flow_events.append(event)
        
        # Update active traces
        if event.tracking_id not in self.active_traces:
            self.active_traces[event.tracking_id] = []
        self.active_traces[event.tracking_id].append(event)
        
        # Update stage metrics
        stage_key = f"{event.stage}_{event.component}"
        metrics = self.stage_metrics[stage_key]
        metrics['events_processed'] += 1
        metrics['last_activity'] = event.timestamp
        
        if event.status == 'error':
            metrics['error_count'] += 1
        
        if event.latency_ms:
            # Update rolling average latency
            current_avg = metrics['avg_latency_ms']
            count = metrics['events_processed']
            metrics['avg_latency_ms'] = ((current_avg * (count - 1)) + event.latency_ms) / count
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get overall pipeline health status"""
        stage_health = {}
        overall_health = "healthy"
        
        for stage in self.pipeline_stages:
            stage_key = f"{stage.name}_{stage.component}"
            metrics = self.stage_metrics[stage_key]
            
            # Check if stage is active (received events in last 5 minutes)
            is_active = (
                metrics['last_activity'] and 
                (datetime.now() - metrics['last_activity']).total_seconds() < 300
            )
            
            # Calculate error rate
            error_rate = (
                metrics['error_count'] / max(metrics['events_processed'], 1)
            ) if metrics['events_processed'] > 0 else 0
            
            # Determine stage health
            stage_status = "healthy"
            if error_rate > 0.1:  # >10% error rate
                stage_status = "degraded"
                overall_health = "degraded"
            elif error_rate > 0.05:  # >5% error rate
                stage_status = "warning"
                if overall_health == "healthy":
                    overall_health = "warning"
            
            stage_health[stage.name] = {
                'status': stage_status,
                'component': stage.component,
                'is_active': is_active,
                'events_processed': metrics['events_processed'],
                'error_count': metrics['error_count'],
                'error_rate': error_rate,
                'avg_latency_ms': metrics['avg_latency_ms'],
                'last_activity': metrics['last_activity'].isoformat() if metrics['last_activity'] else None,
                'expected_throughput': stage.expected_throughput,
                'expected_latency_ms': stage.expected_latency_ms
            }
        
        return {
            'overall_status': overall_health,
            'stages': stage_health,
            'total_active_traces': len(self.active_traces),
            'total_events_tracked': len(self.flow_events)
        }
    
    def get_data_lineage(self, tracking_id: str) -> List[Dict[str, Any]]:
        """Get complete data lineage for a tracking ID"""
        if tracking_id not in self.active_traces:
            return []
        
        events = self.active_traces[tracking_id]
        lineage = []
        
        for event in sorted(events, key=lambda x: x.timestamp):
            lineage.append({
                'stage': event.stage,
                'component': event.component,
                'timestamp': event.timestamp.isoformat(),
                'status': event.status,
                'latency_ms': event.latency_ms,
                'data_size': event.data_size,
                'metadata': event.metadata or {}
            })
        
        return lineage
    
    def get_recent_flows(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent flow events"""
        recent = list(self.flow_events)[-limit:]
        return [event.to_dict() for event in recent]

class DataFlowVisualizationService:
    """Main data flow visualization service"""
    
    def __init__(self):
        self.tracker = DataFlowTracker()
        self.clickhouse_client = ClickHouseClient(host='clickhouse', port=9000, user='default', password='clickhouse123')
        self.nats_client = None
        self.websocket_connections = set()
        
    async def connect_nats(self):
        """Connect to NATS and subscribe to all pipeline events"""
        try:
            self.nats_client = nats.NATS()
            await self.nats_client.connect("nats://nats:4222")
            
            # Subscribe to various pipeline events
            await self.nats_client.subscribe("data.flow.>", cb=self.process_flow_event)
            await self.nats_client.subscribe("anomaly.detected", cb=self.process_anomaly_event)
            await self.nats_client.subscribe("incidents.created", cb=self.process_incident_event)
            
            logger.info("Connected to NATS for data flow tracking")
                
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
    
    async def process_flow_event(self, msg):
        """Process data flow tracking events"""
        try:
            data = json.loads(msg.data.decode())
            
            event = DataFlowEvent(
                event_id=str(uuid.uuid4()),
                tracking_id=data.get('tracking_id', 'unknown'),
                stage=data.get('stage', 'unknown'),
                component=data.get('component', 'unknown'),
                timestamp=datetime.now(),
                status=data.get('status', 'unknown'),
                data_size=data.get('data_size', 0),
                latency_ms=data.get('latency_ms'),
                metadata=data.get('metadata', {})
            )
            
            self.tracker.add_flow_event(event)
            await self.broadcast_to_websockets({'type': 'flow_event', 'data': event.to_dict()})
            
        except Exception as e:
            logger.error(f"Error processing flow event: {e}")
    
    async def process_anomaly_event(self, msg):
        """Process anomaly detection events for flow tracking"""
        try:
            data = json.loads(msg.data.decode())
            
            event = DataFlowEvent(
                event_id=str(uuid.uuid4()),
                tracking_id=data.get('tracking_id', f"anomaly-{uuid.uuid4().hex[:8]}"),
                stage="Anomaly Detection",
                component="anomaly-detection",
                timestamp=datetime.now(),
                status="completed",
                data_size=len(json.dumps(data)),
                latency_ms=data.get('processing_time_ms'),
                metadata={
                    'anomaly_type': data.get('anomaly_type'),
                    'anomaly_score': data.get('anomaly_score'),
                    'metric_name': data.get('metric_name')
                }
            )
            
            self.tracker.add_flow_event(event)
            await self.broadcast_to_websockets({'type': 'anomaly_flow', 'data': event.to_dict()})
            
        except Exception as e:
            logger.error(f"Error processing anomaly event: {e}")
    
    async def process_incident_event(self, msg):
        """Process incident creation events for flow tracking"""
        try:
            data = json.loads(msg.data.decode())
            
            event = DataFlowEvent(
                event_id=str(uuid.uuid4()),
                tracking_id=data.get('correlation_id', f"incident-{uuid.uuid4().hex[:8]}"),
                stage="Incident Creation",
                component="incident-api",
                timestamp=datetime.now(),
                status="completed",
                data_size=len(json.dumps(data)),
                metadata={
                    'incident_type': data.get('incident_type'),
                    'confidence': data.get('confidence'),
                    'ship_id': data.get('ship_id')
                }
            )
            
            self.tracker.add_flow_event(event)
            await self.broadcast_to_websockets({'type': 'incident_flow', 'data': event.to_dict()})
            
        except Exception as e:
            logger.error(f"Error processing incident event: {e}")
    
    async def broadcast_to_websockets(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        if self.websocket_connections:
            message_str = json.dumps(message)
            disconnected = set()
            
            for websocket in self.websocket_connections:
                try:
                    await websocket.send_text(message_str)
                except:
                    disconnected.add(websocket)
            
            # Remove disconnected websockets
            self.websocket_connections -= disconnected
    
    def get_historical_flow_data(self, hours: int = 24) -> Dict[str, Any]:
        """Get historical flow data from ClickHouse"""
        try:
            # Get data ingestion rates
            query = f"""
            SELECT 
                toStartOfHour(timestamp) as hour,
                source,
                COUNT(*) as event_count,
                AVG(length(message)) as avg_message_size
            FROM logs.raw 
            WHERE timestamp >= now() - INTERVAL {hours} HOUR
            GROUP BY hour, source
            ORDER BY hour DESC
            """
            
            results = self.clickhouse_client.execute(query)
            
            historical_data = {
                'ingestion_rates': [],
                'source_breakdown': defaultdict(list),
                'hourly_totals': defaultdict(int)
            }
            
            for row in results:
                hour, source, count, avg_size = row
                historical_data['ingestion_rates'].append({
                    'hour': hour.isoformat(),
                    'source': source,
                    'event_count': count,
                    'avg_message_size': avg_size
                })
                historical_data['source_breakdown'][source].append({
                    'hour': hour.isoformat(),
                    'count': count
                })
                historical_data['hourly_totals'][hour.isoformat()] += count
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error getting historical flow data: {e}")
            return {'ingestion_rates': [], 'source_breakdown': {}, 'hourly_totals': {}}

# FastAPI app
app = FastAPI(title="AIOps Data Flow Visualization", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
service = DataFlowVisualizationService()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await service.connect_nats()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "nats_connected": service.nats_client and not service.nats_client.is_closed,
        "active_websockets": len(service.websocket_connections)
    }

@app.get("/api/pipeline/health")
async def get_pipeline_health():
    """Get overall pipeline health status"""
    return service.tracker.get_pipeline_health()

@app.get("/api/flow/recent")
async def get_recent_flows(limit: int = 100):
    """Get recent flow events"""
    return {
        "events": service.tracker.get_recent_flows(limit),
        "total_tracked": len(service.tracker.flow_events)
    }

@app.get("/api/flow/lineage/{tracking_id}")
async def get_data_lineage(tracking_id: str):
    """Get complete data lineage for a tracking ID"""
    lineage = service.tracker.get_data_lineage(tracking_id)
    if not lineage:
        raise HTTPException(status_code=404, detail="Tracking ID not found")
    
    return {
        "tracking_id": tracking_id,
        "lineage": lineage,
        "total_stages": len(lineage)
    }

@app.get("/api/flow/historical")
async def get_historical_flow(hours: int = 24):
    """Get historical flow data"""
    return service.get_historical_flow_data(hours)

@app.get("/api/stages")
async def get_pipeline_stages():
    """Get pipeline stage configuration"""
    return {
        "stages": [
            {
                "name": stage.name,
                "component": stage.component,
                "input_sources": stage.input_sources,
                "output_destinations": stage.output_destinations,
                "expected_throughput": stage.expected_throughput,
                "expected_latency_ms": stage.expected_latency_ms
            }
            for stage in service.tracker.pipeline_stages
        ]
    }

@app.websocket("/ws/flow")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time flow data"""
    await websocket.accept()
    service.websocket_connections.add(websocket)
    
    try:
        # Send initial pipeline health
        health = service.tracker.get_pipeline_health()
        await websocket.send_text(json.dumps({'type': 'pipeline_health', 'data': health}))
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        service.websocket_connections.discard(websocket)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve data flow visualization dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AIOps Data Flow Visualization</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .card { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .pipeline-stage { display: inline-block; margin: 10px; padding: 15px; border-radius: 8px; min-width: 150px; text-align: center; }
            .stage-healthy { background: #27ae60; color: white; }
            .stage-warning { background: #f39c12; color: white; }
            .stage-degraded { background: #e74c3c; color: white; }
            .stage-inactive { background: #95a5a6; color: white; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
            .metric-card { background: #ecf0f1; padding: 15px; border-radius: 8px; }
            .chart-container { width: 100%; height: 400px; }
            #realTimeData { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 8px; font-family: monospace; max-height: 300px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔄 AIOps Data Flow Visualization</h1>
                <p>Real-time monitoring of data pipeline health and performance</p>
            </div>
            
            <div class="card">
                <h2>Pipeline Overview</h2>
                <div id="pipelineStages"></div>
            </div>
            
            <div class="metrics-grid">
                <div class="card">
                    <h3>Pipeline Health</h3>
                    <div class="metric-card">
                        <strong>Overall Status:</strong> <span id="overallStatus">Loading...</span><br>
                        <strong>Active Traces:</strong> <span id="activeTraces">0</span><br>
                        <strong>Total Events:</strong> <span id="totalEvents">0</span>
                    </div>
                </div>
                
                <div class="card">
                    <h3>Throughput Metrics</h3>
                    <div class="chart-container">
                        <canvas id="throughputChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Real-time Data Flow Events</h2>
                <div id="realTimeData"></div>
            </div>
        </div>

        <script>
            // WebSocket connection for real-time updates
            const ws = new WebSocket(`ws://${window.location.host}/ws/flow`);
            const realTimeData = document.getElementById('realTimeData');
            
            // Chart setup
            const ctx = document.getElementById('throughputChart').getContext('2d');
            const throughputChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Events/minute',
                        data: [],
                        borderColor: '#3498db',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
            
            // WebSocket message handler
            ws.onmessage = function(event) {
                const message = JSON.parse(event.data);
                
                if (message.type === 'pipeline_health') {
                    updatePipelineHealth(message.data);
                } else if (message.type === 'flow_event') {
                    addRealtimeEvent(message.data);
                }
            };
            
            function updatePipelineHealth(data) {
                // Update overall status
                document.getElementById('overallStatus').textContent = data.overall_status.toUpperCase();
                document.getElementById('activeTraces').textContent = data.total_active_traces;
                document.getElementById('totalEvents').textContent = data.total_events_tracked;
                
                // Update pipeline stages
                const stagesContainer = document.getElementById('pipelineStages');
                stagesContainer.innerHTML = '';
                
                Object.entries(data.stages).forEach(([stageName, stageData]) => {
                    const stageDiv = document.createElement('div');
                    stageDiv.className = `pipeline-stage stage-${stageData.status}`;
                    stageDiv.innerHTML = `
                        <strong>${stageName}</strong><br>
                        ${stageData.component}<br>
                        Events: ${stageData.events_processed}<br>
                        Errors: ${stageData.error_count}<br>
                        Latency: ${stageData.avg_latency_ms.toFixed(1)}ms
                    `;
                    stagesContainer.appendChild(stageDiv);
                });
            }
            
            function addRealtimeEvent(eventData) {
                const eventDiv = document.createElement('div');
                eventDiv.innerHTML = `
                    <strong>${new Date(eventData.timestamp).toLocaleTimeString()}</strong> - 
                    ${eventData.stage} (${eventData.component}) - 
                    ${eventData.status.toUpperCase()} - 
                    Tracking: ${eventData.tracking_id}
                `;
                realTimeData.insertBefore(eventDiv, realTimeData.firstChild);
                
                // Keep only last 50 events
                while (realTimeData.children.length > 50) {
                    realTimeData.removeChild(realTimeData.lastChild);
                }
            }
            
            // Fetch initial data
            async function fetchInitialData() {
                try {
                    const response = await fetch('/api/pipeline/health');
                    const data = await response.json();
                    updatePipelineHealth(data);
                } catch (error) {
                    console.error('Error fetching initial data:', error);
                }
            }
            
            // Initialize
            fetchInitialData();
            
            // Refresh data every 30 seconds
            setInterval(fetchInitialData, 30000);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8089)