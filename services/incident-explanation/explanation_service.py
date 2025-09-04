#!/usr/bin/env python3
"""
AIOps NAAS - User-Friendly Incident Explanation Service

This service converts technical incident correlations into plain language 
explanations that non-technical users can understand and act upon.

Features:
- Plain language incident translation
- Historical context integration  
- Predictive insights generation
- Maritime-specific scenario handling
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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

# Pydantic models
class IncidentExplanation(BaseModel):
    incident_id: str
    plain_language_summary: str
    what_happened: str
    why_it_matters: str
    historical_context: str
    recommended_actions: List[str]
    predicted_timeline: str
    confidence_level: str
    maritime_context: Optional[Dict[str, Any]] = None

class HistoricalPattern(BaseModel):
    past_occurrences: int
    common_causes: List[str]
    average_resolution_time: str
    successful_fixes: List[str]
    seasonal_patterns: List[str]

class PredictiveInsight(BaseModel):
    probability_of_escalation: float
    expected_timeline: str
    recommended_preventive_actions: List[str]
    confidence_level: str
    risk_factors: List[str]

@dataclass
class IncidentTranslator:
    """Service for translating technical incidents to user-friendly explanations"""
    
    def __init__(self):
        self.clickhouse_client = None
        self.nats_client = None
        
        # Load translation templates
        self.templates = self._load_templates()
        
    def _load_templates(self) -> Dict[str, Any]:
        """Load incident explanation templates"""
        return {
            "resource_pressure": {
                "summary": "System overload detected - computer working too hard",
                "what_happened": "Your ship's computer is using {cpu_percent}% of its processing power and {memory_percent}% of its memory. This means too many programs are running at once.",
                "why_matters": "When both CPU and memory are high, systems might slow down or stop responding. This could affect navigation, communication, or other critical operations.",
                "common_causes": ["heavy weather increasing satellite usage", "port approach with navigation systems working harder", "crew change data synchronization"],
                "actions": ["Check which programs are using most resources", "Close unnecessary applications", "Restart non-critical services", "Monitor for next 30 minutes"],
                "maritime_specific": True
            },
            "satellite_weather_impact": {
                "summary": "Weather interfering with satellite communication",
                "what_happened": "Heavy weather is affecting your satellite connection. Signal strength is weak ({signal_strength} dBm) and {packet_loss_percent}% of data packets are getting lost.",
                "why_matters": "Poor satellite connection means slower internet, delayed messaging, and potential communication blackouts during critical operations.",
                "common_causes": ["rain fade during storms", "heavy cloud cover", "atmospheric interference"],
                "actions": ["Switch to backup communication if critical", "Delay large file transfers", "Monitor weather radar", "Increase satellite power if available"],
                "maritime_specific": True
            },
            "communication_issues": {
                "summary": "Communication system performance degraded", 
                "what_happened": "Your communication systems are experiencing {latency_ms}ms delays and {error_rate_percent}% error rates. Messages may be delayed or fail to send.",
                "why_matters": "Communication issues can affect coordination with shore, emergency response, and operational efficiency.",
                "common_causes": ["equipment aging", "antenna misalignment", "interference from other devices"],
                "actions": ["Check antenna alignment", "Test backup communication", "Restart communication equipment", "Contact technical support"],
                "maritime_specific": True
            },
            "network_system_correlation": {
                "summary": "Network and system performance both degraded",
                "what_happened": "Both your network connection and computer systems are performing poorly. Network response time is {network_delay}ms and system load is {system_load_percent}%.",
                "why_matters": "When network and systems are both slow, it usually indicates a deeper infrastructure problem that needs immediate attention.",
                "common_causes": ["hardware failure", "power supply issues", "overheating", "software conflicts"],
                "actions": ["Check system temperatures", "Verify power connections", "Restart network equipment", "Monitor system logs"],
                "maritime_specific": True
            },
            "single_anomaly": {
                "summary": "Unusual behavior detected in {metric_name}",
                "what_happened": "The {metric_name} measurement is showing unusual patterns. Current value is {current_value}, which is significantly different from normal.",
                "why_matters": "Unusual patterns often indicate developing problems that could become serious if not addressed.",
                "common_causes": ["equipment drift", "environmental changes", "configuration changes"],
                "actions": ["Monitor closely for changes", "Check related systems", "Review recent configuration changes", "Consider preventive maintenance"],
                "maritime_specific": False
            }
        }
    
    async def translate_incident(self, incident_data: Dict[str, Any]) -> IncidentExplanation:
        """Convert technical incident to user-friendly explanation"""
        try:
            incident_type = incident_data.get('incident_type', 'single_anomaly')
            template = self.templates.get(incident_type, self.templates['single_anomaly'])
            
            # Extract metrics for formatting
            metrics = incident_data.get('correlated_events', [{}])[0]
            
            # Format the explanation using template and actual data
            explanation = self._format_explanation(template, metrics, incident_data)
            
            # Get historical context
            historical_context = await self._get_historical_context(
                incident_type, 
                incident_data.get('ship_id', 'unknown')
            )
            
            # Generate predictive insights
            predictive_insights = await self._generate_predictive_insights(
                incident_data,
                historical_context
            )
            
            return IncidentExplanation(
                incident_id=incident_data.get('incident_id', str(uuid.uuid4())),
                plain_language_summary=explanation['summary'],
                what_happened=explanation['what_happened'],
                why_it_matters=explanation['why_matters'],
                historical_context=explanation['historical_context'],
                recommended_actions=explanation['actions'],
                predicted_timeline=predictive_insights['timeline'],
                confidence_level=predictive_insights['confidence'],
                maritime_context=explanation.get('maritime_context')
            )
            
        except Exception as e:
            logger.error(f"Error translating incident: {e}")
            return self._create_fallback_explanation(incident_data)
    
    def _format_explanation(self, template: Dict[str, Any], metrics: Dict[str, Any], incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format explanation template with actual incident data"""
        
        # Extract common metric values
        cpu_percent = int(metrics.get('value', 0) * 100) if metrics.get('metric_name') == 'cpu_usage' else 'unknown'
        memory_percent = int(metrics.get('value', 0) * 100) if metrics.get('metric_name') == 'memory_usage' else 'unknown'
        
        # Format strings with actual values
        formatted = {
            'summary': template['summary'],
            'what_happened': template['what_happened'].format(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                signal_strength=metrics.get('signal_strength', 'unknown'),
                packet_loss_percent=int(metrics.get('packet_loss', 0) * 100),
                latency_ms=metrics.get('latency', 'unknown'),
                error_rate_percent=int(metrics.get('error_rate', 0) * 100),
                network_delay=metrics.get('network_delay', 'unknown'),
                system_load_percent=int(metrics.get('system_load', 0) * 100),
                metric_name=metrics.get('metric_name', 'system metric'),
                current_value=metrics.get('value', 'unknown')
            ),
            'why_matters': template['why_matters'],
            'actions': template['actions'],
            'maritime_context': template.get('maritime_specific', False)
        }
        
        return formatted
    
    async def _get_historical_context(self, incident_type: str, ship_id: str) -> str:
        """Query ClickHouse for historical incident patterns"""
        try:
            if not self.clickhouse_client:
                return "No historical data available"
                
            query = """
                SELECT 
                    COUNT(*) as occurrences,
                    AVG(resolution_time_minutes) as avg_resolution,
                    groupArray(resolution_action) as successful_actions
                FROM incidents 
                WHERE incident_type = %s 
                  AND ship_id = %s 
                  AND created_at > now() - INTERVAL 30 DAY
                  AND status = 'resolved'
            """
            
            result = self.clickhouse_client.execute(query, [incident_type, ship_id])
            
            if result and result[0][0] > 0:
                occurrences, avg_resolution, actions = result[0]
                return f"This has happened {occurrences} times in the past month. " \
                       f"It typically takes {int(avg_resolution)} minutes to resolve. " \
                       f"Common successful fixes: {', '.join(actions[:3])}."
            else:
                return "This is the first time this type of issue has been detected on your ship."
                
        except Exception as e:
            logger.error(f"Error getting historical context: {e}")
            return "Historical data temporarily unavailable"
    
    async def _generate_predictive_insights(self, incident_data: Dict[str, Any], historical_context: str) -> Dict[str, str]:
        """Generate predictive insights based on incident data and history"""
        try:
            severity = incident_data.get('incident_severity', 'info')
            incident_type = incident_data.get('incident_type', 'unknown')
            
            # Simple rule-based prediction (can be enhanced with ML)
            if severity == 'critical':
                timeline = "1-2 hours if immediate action taken"
                confidence = "high"
            elif severity == 'warning':
                timeline = "2-4 hours with standard response"
                confidence = "medium"
            else:
                timeline = "4-8 hours or may resolve naturally"
                confidence = "low"
            
            # Adjust based on incident type
            if incident_type == 'satellite_weather_impact':
                timeline = "3-4 hours as weather improves"
                confidence = "high"
            elif incident_type == 'resource_pressure':
                timeline = "30 minutes to 2 hours with proper action"
                confidence = "high"
                
            return {
                'timeline': timeline,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating predictive insights: {e}")
            return {'timeline': 'unknown', 'confidence': 'low'}
    
    def _create_fallback_explanation(self, incident_data: Dict[str, Any]) -> IncidentExplanation:
        """Create a basic explanation when translation fails"""
        return IncidentExplanation(
            incident_id=incident_data.get('incident_id', str(uuid.uuid4())),
            plain_language_summary="System issue detected",
            what_happened="An unusual pattern was detected in your systems that requires attention.",
            why_it_matters="System anomalies can indicate developing problems that should be investigated.",
            historical_context="Unable to retrieve historical context at this time.",
            recommended_actions=["Monitor system closely", "Check system logs", "Contact technical support if needed"],
            predicted_timeline="Unknown - monitor for changes",
            confidence_level="low"
        )

# FastAPI application
app = FastAPI(title="AIOps Incident Explanation Service")

# CORS middleware for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global translator instance
translator = IncidentTranslator()

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    try:
        # Initialize ClickHouse connection
        translator.clickhouse_client = ClickHouseClient(host='clickhouse', user='default', password='clickhouse123')
        logger.info("Connected to ClickHouse")
        
        # Initialize NATS connection
        translator.nats_client = await nats.connect("nats://nats:4222")
        logger.info("Connected to NATS")
        
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.post("/explain-incident", response_model=IncidentExplanation)
async def explain_incident(incident_data: Dict[str, Any]):
    """Convert technical incident data to user-friendly explanation"""
    try:
        explanation = await translator.translate_incident(incident_data)
        return explanation
    except Exception as e:
        logger.error(f"Error explaining incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/historical-context/{incident_type}/{ship_id}")
async def get_historical_context(incident_type: str, ship_id: str):
    """Get historical context for specific incident type and ship"""
    try:
        context = await translator._get_historical_context(incident_type, ship_id)
        return {"historical_context": context}
    except Exception as e:
        logger.error(f"Error getting historical context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predictive-insights/{incident_id}")
async def get_predictive_insights(incident_id: str):
    """Generate predictive insights for a specific incident"""
    try:
        # In a real implementation, fetch incident data from ClickHouse
        # For now, return example insights
        return {
            "probability_of_escalation": 0.3,
            "expected_timeline": "2-4 hours",
            "recommended_preventive_actions": [
                "Monitor system metrics closely",
                "Prepare backup systems",
                "Alert crew to potential issues"
            ],
            "confidence_level": "medium"
        }
    except Exception as e:
        logger.error(f"Error getting predictive insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve user-friendly web dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AIOps User-Friendly Operations Center</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .incident { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .critical { border-left: 5px solid #ff4444; }
            .warning { border-left: 5px solid #ffaa00; }
            .info { border-left: 5px solid #0088ff; }
            .section { margin: 10px 0; }
            .actions { background: #f9f9f9; padding: 10px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🚢 Ship Operations Center - User-Friendly View</h1>
        
        <div class="incident critical">
            <h3>🚨 Active Issue: High System Load</h3>
            <div class="section">
                <strong>What's Happening:</strong><br>
                Your ship's computer is working very hard (CPU at 85%) and running low on memory (92%). 
                This usually happens when too many programs are running at once.
            </div>
            <div class="section">
                <strong>Why This Matters:</strong><br>
                When both CPU and memory are high, your systems might slow down or stop responding. 
                This could affect navigation, communication, or other critical operations.
            </div>
            <div class="section">
                <strong>This Happened Before:</strong><br>
                Similar issues occurred 3 times this month, usually during heavy weather or port approach. 
                Average resolution time: 45 minutes.
            </div>
            <div class="actions">
                <strong>Recommended Actions:</strong>
                <ol>
                    <li>Check which programs are using the most resources</li>
                    <li>Close unnecessary applications</li>
                    <li>Consider restarting non-critical services</li>
                    <li>Monitor for the next 30 minutes</li>
                </ol>
            </div>
            <div class="section">
                <strong>Expected Resolution:</strong> 30 minutes to 2 hours with proper action (High confidence)
            </div>
        </div>
        
        <div class="incident warning">
            <h3>🛰️ Communication Notice: Weather Impact</h3>
            <div class="section">
                <strong>What's Happening:</strong><br>
                Heavy weather is interfering with your satellite connection. Signal strength is weak 
                and some data packets are getting lost.
            </div>
            <div class="section">
                <strong>Expected Resolution:</strong> 3-4 hours as weather improves (High confidence)
            </div>
        </div>
        
        <h2>📊 System Health Overview</h2>
        <ul>
            <li>✅ Navigation Systems: Normal</li>
            <li>⚠️ Communication: Weather Impact</li>
            <li>🚨 Computer Systems: High Load</li>
            <li>✅ Power Systems: Normal</li>
        </ul>
        
        <h2>🔮 Predictions</h2>
        <ul>
            <li>System load should decrease within 2 hours based on historical patterns</li>
            <li>Communication will improve as weather system moves through (3-4 hours)</li>
            <li>No other issues predicted for the next 24 hours</li>
        </ul>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8087)