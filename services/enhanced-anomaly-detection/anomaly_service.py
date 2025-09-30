#!/usr/bin/env python3
"""
AIOps NAAS v0.2 - Enhanced Anomaly Detection Service with Level 1 Enrichment Support

This service extends the basic anomaly detection with enriched data processing:
- Processes enriched telemetry events from Level 1 correlation
- Context-aware anomaly thresholds based on operational conditions
- Maritime-specific anomaly detection for satellite, weather, navigation
- Publishes enriched anomalies with full contextual information

The service:
1. Subscribes to enriched data events from Benthos Level 1 correlation
2. Applies context-aware anomaly detection algorithms
3. Publishes enriched anomaly events to NATS for Level 2 correlation
4. Provides health monitoring and metrics
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from fastapi import FastAPI
import uvicorn

from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class EnrichedAnomalyEvent:
    """Enhanced anomaly event with enrichment context"""
    timestamp: datetime
    ship_id: str
    metric_name: str
    metric_value: float
    anomaly_score: float
    anomaly_type: str
    operational_status: str
    enrichment_context: dict
    maritime_context: dict
    correlation_level: str
    context_sources: list

class ContextualAnomalyDetectors:
    """Anomaly detectors that consider enrichment context"""
    
    def __init__(self):
        self.history = {}
        self.baseline_thresholds = {
            'cpu_usage': 0.70,
            'memory_usage': 0.60,
            'disk_usage': 0.80,
            'satellite_snr': 15.0,  # dB
            'satellite_ber': 0.001,
            'network_latency': 200.0,  # ms
            'network_packet_loss': 1.0  # percent
        }
        
    def get_contextual_threshold(self, metric_name: str, operational_status: str, 
                               enrichment_context: dict) -> float:
        """Calculate threshold based on operational context"""
        base_threshold = self.baseline_thresholds.get(metric_name, 0.7)
        
        # Adjust for operational conditions
        if operational_status == 'weather_impacted':
            if 'cpu' in metric_name or 'memory' in metric_name:
                return base_threshold * 0.85  # 15% more sensitive
            elif 'satellite' in metric_name:
                return base_threshold * 0.80  # 20% more sensitive for satellite
                
        elif operational_status == 'degraded_comms':
            if 'network' in metric_name:
                return base_threshold * 1.2  # 20% less sensitive, comms already known bad
            else:
                return base_threshold * 0.90  # Slightly more sensitive for other metrics
                
        elif operational_status == 'system_overloaded':
            if 'cpu' in metric_name or 'memory' in metric_name:
                return base_threshold * 1.1  # Less sensitive, already known to be loaded
                
        # Weather-specific adjustments
        weather_impact = enrichment_context.get('weather_impact', {})
        if weather_impact.get('rain_rate', 0) > 5:  # Heavy rain
            if 'satellite' in metric_name:
                return base_threshold * 0.75  # Much more sensitive during heavy rain
                
        return base_threshold
    
    def detect_anomaly(self, metric_name: str, value: float, operational_status: str,
                      enrichment_context: dict) -> float:
        """Detect anomaly with contextual awareness"""
        threshold = self.get_contextual_threshold(metric_name, operational_status, enrichment_context)
        
        # Simple threshold-based detection with context
        if 'cpu_usage' in metric_name or 'memory_usage' in metric_name or 'disk_usage' in metric_name:
            if value > threshold * 100:  # Convert to percentage
                return min((value - threshold * 100) / (100 - threshold * 100), 1.0)
        elif 'satellite_snr' in metric_name:
            if value < threshold:
                return min((threshold - value) / threshold, 1.0)
        elif 'satellite_ber' in metric_name:
            if value > threshold:
                return min(value / threshold, 1.0)
        elif 'network_latency' in metric_name:
            if value > threshold:
                return min((value - threshold) / threshold, 1.0)
        elif 'network_packet_loss' in metric_name:
            if value > threshold:
                return min(value / (threshold * 10), 1.0)
                
        return 0.0

class EnrichedAnomalyDetectionService:
    """Enhanced anomaly detection service with Level 1 enrichment support"""
    
    def __init__(self):
        self.nats_client = None
        self.detectors = ContextualAnomalyDetectors()
        self.health_status = {
            "healthy": False,
            "nats_connected": False,
            "enriched_events_processed": 0,
            "anomalies_detected": 0,
            "enhanced_anomalies_published": 0,
            "processing_errors": 0
        }
        
        # FastAPI app for health endpoints
        self.app = FastAPI(title="Enhanced Anomaly Detection Service")
        self._setup_routes()
        
        logger.info("Enhanced Anomaly Detection Service initialized")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health():
            return self.health_status
            
        @self.app.get("/stats")
        async def stats():
            return {
                "events_processed": self.health_status["enriched_events_processed"],
                "anomalies_detected": self.health_status["anomalies_detected"],
                "detection_rate": self.health_status["anomalies_detected"] / max(self.health_status["enriched_events_processed"], 1)
            }
    
    async def connect_nats(self):
        """Connect to NATS and subscribe to enriched data"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect("nats://nats:4222")
            self.health_status["nats_connected"] = True
            
            # Subscribe to enriched anomaly events from benthos enrichment
            await self.nats_client.subscribe(
                "anomaly.detected.enriched",
                cb=self._handle_enriched_event,
                queue="enhanced_anomaly_detection"
            )
            
            logger.info("Connected to NATS and subscribed to enriched anomaly stream")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
    
    async def _handle_enriched_event(self, msg):
        """Process enriched anomaly events for context-aware anomaly detection with LLM integration"""
        try:
            event_data = json.loads(msg.data.decode())
            self.health_status["enriched_events_processed"] += 1
            
            logger.info(f"Processing enriched anomaly: {event_data.get('tracking_id', 'unknown')}")
            
            # Extract enrichment data
            enrichment_context = event_data.get('enrichment_context', {})
            maritime_context = enrichment_context.get('maritime_context', {})
            ai_analysis = enrichment_context.get('ai_analysis', {})
            original_anomaly = event_data.get('original_anomaly', {})
            
            # Enhanced anomaly processing with LLM/Ollama integration
            enhanced_analysis = await self._perform_enhanced_analysis_with_llm(event_data)
            
            # Group and aggregate anomalies by time/source/history
            grouping_analysis = await self._group_anomalies_with_context(event_data)
            
            # Create final enriched anomaly event
            final_event = {
                "final_anomaly_id": f"enhanced_{event_data.get('anomaly_id', 'unknown')}",
                "tracking_id": event_data.get('tracking_id'),
                "timestamp": datetime.now().isoformat(),
                
                # Original data preservation
                "original_anomaly": original_anomaly,
                "enrichment_context": enrichment_context,
                
                # Enhanced analysis with LLM
                "enhanced_context": {
                    "llm_analysis": enhanced_analysis,
                    "anomaly_grouping": grouping_analysis,
                    "processing_stage": "level_2_enhanced",
                    "context_accuracy_score": enhanced_analysis.get('confidence', 0.8),
                    "historical_correlation": grouping_analysis.get('historical_patterns', {}),
                    "operational_recommendations": enhanced_analysis.get('recommendations', [])
                },
                
                # Final scoring and classification
                "final_anomaly_score": enhanced_analysis.get('enhanced_score', event_data.get('anomaly_score', 0.5)),
                "risk_level": enhanced_analysis.get('risk_assessment', 'medium'),
                "urgency": enhanced_analysis.get('urgency', 'normal'),
                
                # Ship and system context
                "ship_id": event_data.get('ship_id'),
                "device_id": event_data.get('device_id'),
                "system_impact": enhanced_analysis.get('system_impact', 'localized')
            }
            
            # Publish enhanced anomaly for final correlation
            await self._publish_enhanced_anomaly(final_event)
            
            logger.info(f"Enhanced anomaly analysis complete for {event_data.get('tracking_id')}")
            
        except Exception as e:
            logger.error(f"Error processing enriched event: {e}")
            self.health_status["processing_errors"] += 1
    
    async def _perform_enhanced_analysis_with_llm(self, event_data):
        """Perform advanced anomaly analysis using LLM/Ollama for context and accuracy"""
        try:
            # Prepare prompt for LLM analysis
            analysis_prompt = f"""
            Analyze this maritime anomaly event and provide enhanced context:
            
            Anomaly Details:
            - Tracking ID: {event_data.get('tracking_id')}
            - Ship: {event_data.get('ship_id')}
            - Original Score: {event_data.get('anomaly_score')}
            - Log Message: {event_data.get('log_message', 'N/A')}
            
            Enrichment Context:
            - Maritime Status: {event_data.get('enrichment_context', {}).get('maritime_context', {}).get('operational_status')}
            - Device Context: {event_data.get('enrichment_context', {}).get('device_context', {})}
            - AI Analysis: {event_data.get('enrichment_context', {}).get('ai_analysis', {})}
            
            Provide:
            1. Enhanced anomaly score (0.0-1.0)
            2. Risk assessment (low/medium/high/critical)
            3. System impact analysis
            4. Operational recommendations
            5. Urgency level
            """
            
            # Try LLM/Ollama integration
            try:
                import requests
                
                llm_response = requests.post(
                    "http://ollama:11434/api/generate",
                    json={
                        "model": "llama2",
                        "prompt": analysis_prompt,
                        "stream": False
                    },
                    timeout=10
                )
                
                if llm_response.status_code == 200:
                    llm_data = llm_response.json()
                    analysis_text = llm_data.get('response', '')
                    
                    # Parse LLM response (simplified parsing)
                    enhanced_score = self._extract_score_from_llm_response(analysis_text, event_data.get('anomaly_score', 0.5))
                    risk_level = self._extract_risk_from_llm_response(analysis_text)
                    recommendations = self._extract_recommendations_from_llm_response(analysis_text)
                    
                    return {
                        "llm_analysis": analysis_text,
                        "enhanced_score": enhanced_score,
                        "risk_assessment": risk_level,
                        "recommendations": recommendations,
                        "system_impact": self._assess_system_impact(event_data, enhanced_score),
                        "urgency": self._determine_urgency(enhanced_score, risk_level),
                        "confidence": 0.9,
                        "analysis_method": "llm_enhanced"
                    }
                    
            except Exception as llm_error:
                logger.warning(f"LLM analysis failed, using rule-based fallback: {llm_error}")
            
            # Fallback to enhanced rule-based analysis
            return self._rule_based_enhanced_analysis(event_data)
            
        except Exception as e:
            logger.error(f"Enhanced analysis error: {e}")
            return self._rule_based_enhanced_analysis(event_data)
    
    def _rule_based_enhanced_analysis(self, event_data):
        """Fallback enhanced analysis using sophisticated rules"""
        original_score = event_data.get('anomaly_score', 0.5)
        log_message = event_data.get('log_message', '').lower()
        maritime_context = event_data.get('enrichment_context', {}).get('maritime_context', {})
        
        # Enhanced scoring based on context
        enhanced_score = original_score
        
        # Maritime context boosting
        operational_status = maritime_context.get('operational_status', 'normal_operations')
        if operational_status == 'critical_operations':
            enhanced_score = min(1.0, enhanced_score * 1.3)
        elif operational_status == 'degraded_operations':
            enhanced_score = min(1.0, enhanced_score * 1.1)
        
        # Critical system analysis
        critical_keywords = ['engine', 'navigation', 'communication', 'power', 'safety']
        if any(keyword in log_message for keyword in critical_keywords):
            enhanced_score = min(1.0, enhanced_score * 1.2)
        
        # Risk assessment
        risk_level = 'low'
        if enhanced_score > 0.8:
            risk_level = 'critical'
        elif enhanced_score > 0.6:
            risk_level = 'high'
        elif enhanced_score > 0.4:
            risk_level = 'medium'
        
        return {
            "enhanced_score": enhanced_score,
            "risk_assessment": risk_level,
            "recommendations": self._generate_recommendations(log_message, enhanced_score),
            "system_impact": self._assess_system_impact(event_data, enhanced_score),
            "urgency": self._determine_urgency(enhanced_score, risk_level),
            "confidence": 0.7,
            "analysis_method": "rule_based_enhanced"
        }
    
    async def _group_anomalies_with_context(self, event_data):
        """Group and aggregate anomalies by time/source/history with LLM context"""
        try:
            ship_id = event_data.get('ship_id')
            device_id = event_data.get('device_id')
            
            # Simplified grouping analysis (would integrate with time-series DB in production)
            grouping_data = {
                "temporal_pattern": "isolated_event",  # Could be: recurring, clustered, isolated
                "source_correlation": {
                    "ship_id": ship_id,
                    "device_id": device_id,
                    "related_devices": []  # Would query device registry for related systems
                },
                "historical_patterns": {
                    "similar_events_24h": 0,  # Would query ClickHouse
                    "pattern_type": "new_anomaly"
                },
                "aggregation_confidence": 0.8
            }
            
            return grouping_data
            
        except Exception as e:
            logger.error(f"Grouping analysis error: {e}")
            return {"error": "grouping_failed"}
    
    def _extract_score_from_llm_response(self, response_text, original_score):
        """Extract enhanced score from LLM response"""
        # Simplified extraction (would use more sophisticated NLP in production)
        if 'critical' in response_text.lower():
            return min(1.0, original_score * 1.5)
        elif 'high' in response_text.lower():
            return min(1.0, original_score * 1.3)
        elif 'medium' in response_text.lower():
            return min(1.0, original_score * 1.1)
        return original_score
    
    def _extract_risk_from_llm_response(self, response_text):
        """Extract risk level from LLM response"""
        response_lower = response_text.lower()
        if 'critical' in response_lower:
            return 'critical'
        elif 'high' in response_lower:
            return 'high'
        elif 'medium' in response_lower:
            return 'medium'
        return 'low'
    
    def _extract_recommendations_from_llm_response(self, response_text):
        """Extract recommendations from LLM response"""
        # Simplified extraction
        recommendations = []
        if 'investigate' in response_text.lower():
            recommendations.append('immediate_investigation')
        if 'maintenance' in response_text.lower():
            recommendations.append('schedule_maintenance')
        if 'monitor' in response_text.lower():
            recommendations.append('enhanced_monitoring')
        return recommendations if recommendations else ['standard_monitoring']
    
    def _generate_recommendations(self, log_message, score):
        """Generate recommendations based on rule-based analysis"""
        recommendations = []
        
        if score > 0.8:
            recommendations.extend(['immediate_investigation', 'escalate_to_operations'])
        elif score > 0.6:
            recommendations.extend(['investigate_within_hour', 'notify_technical_team'])
        else:
            recommendations.append('monitor_closely')
        
        # Context-specific recommendations
        if 'database' in log_message:
            recommendations.append('check_database_connectivity')
        elif 'network' in log_message:
            recommendations.append('verify_network_status')
        elif 'engine' in log_message:
            recommendations.append('engine_diagnostics')
        
        return recommendations
    
    def _assess_system_impact(self, event_data, enhanced_score):
        """Assess system impact based on enhanced analysis"""
        if enhanced_score > 0.8:
            return 'system_wide'
        elif enhanced_score > 0.6:
            return 'subsystem_affected'
        else:
            return 'localized'
    
    def _determine_urgency(self, enhanced_score, risk_level):
        """Determine urgency level"""
        if risk_level == 'critical' or enhanced_score > 0.9:
            return 'immediate'
        elif risk_level == 'high' or enhanced_score > 0.7:
            return 'urgent'
        elif risk_level == 'medium':
            return 'normal'
        else:
            return 'low'
    
    async def _publish_enhanced_anomaly(self, final_event):
        """Publish final enhanced anomaly to NATS for correlation"""
        try:
            if not self.nats_client or self.nats_client.is_closed:
                logger.warning("NATS not connected, cannot publish enhanced anomaly")
                return
            
            event_json = json.dumps(final_event, default=str)
            await self.nats_client.publish("anomaly.detected.enriched.final", event_json.encode())
            
            logger.info(f"Published enhanced anomaly: {final_event.get('tracking_id')} with final score {final_event.get('final_anomaly_score')}")
            self.health_status["enhanced_anomalies_published"] += 1
            
        except Exception as e:
            logger.error(f"Error publishing enhanced anomaly: {e}")
            original_data = event_data.get('original_data', {})
            enrichment_context = event_data.get('enrichment_context', {})
            maritime_context = event_data.get('maritime_context', {})
            operational_status = event_data.get('operational_status', 'normal')
            data_source = event_data.get('data_source', 'unknown')
            ship_id = event_data.get('ship_id', 'ship-01')
            
            # Process different types of enriched data
            if data_source == 'system':
                await self._process_system_metrics(original_data, enrichment_context, 
                                                 maritime_context, operational_status, ship_id)
            elif data_source == 'satellite':
                await self._process_satellite_metrics(original_data, enrichment_context,
                                                    maritime_context, operational_status, ship_id)
            elif data_source == 'network':
                await self._process_network_metrics(original_data, enrichment_context,
                                                  maritime_context, operational_status, ship_id)
                
        except Exception as e:
            logger.error(f"Error processing enriched event: {e}")
    
    async def _process_system_metrics(self, data, enrichment_context, maritime_context, 
                                    operational_status, ship_id):
        """Process system metrics with enrichment context"""
        try:
            # System metrics that might be present
            metrics_to_check = {
                'cpu_usage_percent': 'cpu_usage',
                'memory_usage_percent': 'memory_usage',
                'disk_usage_percent': 'disk_usage'
            }
            
            for data_key, metric_name in metrics_to_check.items():
                if data_key in data and data[data_key] > 0:
                    value = float(data[data_key])
                    
                    # Detect anomaly with context
                    anomaly_score = self.detectors.detect_anomaly(
                        metric_name, value, operational_status, enrichment_context
                    )
                    
                    if anomaly_score > 0.1:  # Threshold for publishing
                        await self._publish_enriched_anomaly(
                            ship_id, metric_name, value, anomaly_score,
                            operational_status, enrichment_context, maritime_context,
                            context_sources=['system']
                        )
                        
        except Exception as e:
            logger.error(f"Error processing system metrics: {e}")
    
    async def _process_satellite_metrics(self, data, enrichment_context, maritime_context,
                                       operational_status, ship_id):
        """Process satellite metrics with weather correlation"""
        try:
            # Satellite metrics
            satellite_metrics = {
                'snr_db': 'satellite_snr',
                'ber': 'satellite_ber',
                'signal_strength_dbm': 'satellite_signal'
            }
            
            for data_key, metric_name in satellite_metrics.items():
                if data_key in data:
                    value = float(data[data_key])
                    
                    anomaly_score = self.detectors.detect_anomaly(
                        metric_name, value, operational_status, enrichment_context
                    )
                    
                    if anomaly_score > 0.1:
                        # Add weather correlation to context
                        context_sources = ['satellite']
                        if enrichment_context.get('weather_impact'):
                            context_sources.append('weather')
                            
                        await self._publish_enriched_anomaly(
                            ship_id, metric_name, value, anomaly_score,
                            operational_status, enrichment_context, maritime_context,
                            context_sources=context_sources
                        )
                        
        except Exception as e:
            logger.error(f"Error processing satellite metrics: {e}")
    
    async def _process_network_metrics(self, data, enrichment_context, maritime_context,
                                     operational_status, ship_id):
        """Process network metrics with system load context"""
        try:
            network_metrics = {
                'latency_ms': 'network_latency',
                'packet_loss_percent': 'network_packet_loss',
                'throughput_mbps': 'network_throughput'
            }
            
            for data_key, metric_name in network_metrics.items():
                if data_key in data:
                    value = float(data[data_key])
                    
                    anomaly_score = self.detectors.detect_anomaly(
                        metric_name, value, operational_status, enrichment_context
                    )
                    
                    if anomaly_score > 0.1:
                        context_sources = ['network']
                        if enrichment_context.get('system_load'):
                            context_sources.append('system')
                            
                        await self._publish_enriched_anomaly(
                            ship_id, metric_name, value, anomaly_score,
                            operational_status, enrichment_context, maritime_context,
                            context_sources=context_sources
                        )
                        
        except Exception as e:
            logger.error(f"Error processing network metrics: {e}")
    
    async def _publish_enriched_anomaly(self, ship_id, metric_name, metric_value, anomaly_score,
                                      operational_status, enrichment_context, maritime_context,
                                      context_sources):
        """Publish enriched anomaly event with full contextual information"""
        try:
            enriched_anomaly = {
                "timestamp": datetime.now().isoformat(),
                "ship_id": ship_id,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "anomaly_score": anomaly_score,
                "anomaly_type": "enriched_contextual",
                "detector_name": "contextual_enriched_detector",
                "operational_status": operational_status,
                "enrichment_context": enrichment_context,
                "maritime_context": maritime_context,
                "correlation_level": "level_1_enriched",
                "context_sources": context_sources,
                "labels": {
                    "instance": ship_id,
                    "job": "enhanced_anomaly_detection",
                    "operational_status": operational_status
                },
                "processing_metadata": {
                    "enriched_detection": True,
                    "context_aware_threshold": True,
                    "maritime_context_applied": bool(maritime_context),
                    "weather_considered": 'weather_impact' in enrichment_context,
                    "system_load_considered": 'system_load' in enrichment_context
                }
            }
            
            # Publish to Level 2 correlation (Benthos final correlation stage)
            await self.nats_client.publish("anomaly.detected.enriched.final", json.dumps(enriched_anomaly).encode())
            
            self.health_status["anomalies_detected"] += 1
            
            logger.info(f"Published enriched anomaly: {metric_name}={metric_value} "
                       f"(score={anomaly_score:.3f}, status={operational_status}, "
                       f"contexts={context_sources})")
                       
        except Exception as e:
            logger.error(f"Failed to publish enriched anomaly: {e}")
    
    async def start_service(self):
        """Start the enhanced anomaly detection service"""
        try:
            # Connect to NATS
            await self.connect_nats()
            
            # Update health status
            self.health_status["healthy"] = self.health_status["nats_connected"]
            
            if self.health_status["healthy"]:
                logger.info("Enhanced Anomaly Detection Service started successfully")
                # Keep service running
                while True:
                    await asyncio.sleep(60)  # Heartbeat every minute
                    logger.debug(f"Service heartbeat - Events: {self.health_status['enriched_events_processed']}, "
                               f"Anomalies: {self.health_status['anomalies_detected']}")
            else:
                logger.error("Failed to start service - check NATS connection")
                
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            self.health_status["healthy"] = False

# FastAPI and asyncio integration
app = FastAPI(title="Enhanced Anomaly Detection Service")
service = EnrichedAnomalyDetectionService()
app.mount("/", service.app)

@app.on_event("startup")
async def startup_event():
    """Start the anomaly detection service"""
    asyncio.create_task(service.start_service())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9082)