#!/usr/bin/env python3
"""
AIOps NAAS v0.2 - Anomaly Detection Service (Simplified)

This service implements streaming anomaly detection with basic algorithms:
- Z-score anomaly detection  
- EWMA (Exponentially Weighted Moving Average)
- Simple MAD (Median Absolute Deviation)
- Basic statistical thresholding

The service:
1. Queries metrics from VictoriaMetrics at regular intervals
2. Applies anomaly detection algorithms 
3. Publishes anomaly events to NATS JetStream for correlation
"""

import asyncio
import logging
import json
import time
import re
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import deque
from fastapi import FastAPI
import uvicorn

import requests
from nats.aio.client import Client as NATS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AnomalyEvent:
    """Anomaly detection event"""
    timestamp: datetime
    metric_name: str
    metric_value: float
    anomaly_score: float
    anomaly_type: str
    detector_name: str
    threshold: float
    metadata: dict
    labels: dict
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "anomaly_score": self.anomaly_score,
            "anomaly_type": self.anomaly_type,
            "detector_name": self.detector_name,
            "threshold": self.threshold,
            "metadata": self.metadata,
            "labels": self.labels
        }

@dataclass
class MetricQuery:
    """VictoriaMetrics query configuration"""
    name: str
    query: str
    threshold: float = 0.5
    enabled: bool = True

class SimpleAnomalyDetectors:
    """Collection of simple anomaly detectors"""
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.metric_history = {}  # metric_name -> deque of values
        self.detectors = {
            'zscore': self._zscore_detector,
            'ewma': self._ewma_detector,
            'mad': self._mad_detector,
            'threshold': self._threshold_detector,
        }
    
    def _get_history(self, metric_name: str) -> deque:
        """Get or create history deque for metric"""
        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = deque(maxlen=self.window_size)
        return self.metric_history[metric_name]
    
    def _zscore_detector(self, metric_name: str, value: float) -> float:
        """Z-score based anomaly detection"""
        history = self._get_history(metric_name)
        
        if len(history) < 10:  # Need minimum history
            return 0.0
            
        values = list(history)
        mean = statistics.mean(values)
        try:
            stdev = statistics.stdev(values)
            if stdev == 0:
                return 0.0
            z_score = abs((value - mean) / stdev)
            return min(z_score / 3.0, 1.0)  # Normalize to 0-1
        except:
            return 0.0
    
    def _ewma_detector(self, metric_name: str, value: float) -> float:
        """EWMA-based anomaly detection"""
        history = self._get_history(metric_name)
        
        if len(history) < 5:
            return 0.0
        
        # Calculate EWMA
        alpha = 0.3  # Smoothing factor
        ewma = value
        for i, val in enumerate(reversed(list(history))):
            ewma = alpha * val + (1 - alpha) * ewma
            
        # Anomaly score based on deviation from EWMA
        if len(history) > 0:
            recent_mean = statistics.mean(list(history)[-10:])
            if recent_mean == 0:
                return 0.0
            deviation = abs(value - ewma) / max(recent_mean, 1.0)
            return min(deviation / 2.0, 1.0)
        return 0.0
    
    def _mad_detector(self, metric_name: str, value: float) -> float:
        """MAD-based anomaly detection"""
        history = self._get_history(metric_name)
        
        if len(history) < 10:
            return 0.0
            
        values = list(history)
        median = statistics.median(values)
        mad = statistics.median([abs(x - median) for x in values])
        
        if mad == 0:
            return 0.0
            
        # Modified z-score using MAD
        modified_z = 0.6745 * (value - median) / mad
        return min(abs(modified_z) / 3.5, 1.0)
    
    def _threshold_detector(self, metric_name: str, value: float) -> float:
        """Simple threshold-based detection"""
        thresholds = {
            'cpu_usage': 85.0,
            'memory_usage': 90.0,
            'disk_usage': 85.0
        }
        
        threshold = thresholds.get(metric_name, 100.0)
        if value > threshold:
            return min((value - threshold) / (100 - threshold), 1.0)
        return 0.0
    
    def update_and_detect(self, metric_name: str, value: float) -> Dict[str, float]:
        """Update detectors with new value and return anomaly scores"""
        history = self._get_history(metric_name)
        
        # Calculate scores before adding new value
        scores = {}
        for detector_name, detector_func in self.detectors.items():
            try:
                score = detector_func(metric_name, value)
                scores[detector_name] = score
            except Exception as e:
                logger.error(f"Error in detector {detector_name} for metric {metric_name}: {e}")
                scores[detector_name] = 0.0
        
        # Add new value to history
        history.append(value)
        
        return scores

class VictoriaMetricsClient:
    """Client for querying VictoriaMetrics"""
    
    def __init__(self, base_url: str = "http://victoria-metrics:8428"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def query_instant(self, query: str) -> List[Dict[str, Any]]:
        """Execute instant query against VictoriaMetrics"""
        try:
            url = f"{self.base_url}/api/v1/query"
            params = {
                'query': query,
                'time': int(time.time())
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] != 'success':
                logger.error(f"VictoriaMetrics query failed: {data}")
                return []
            
            results = []
            for result in data['data']['result']:
                metric = result['metric']
                value = float(result['value'][1])
                results.append({
                    'metric': metric,
                    'value': value,
                    'timestamp': result['value'][0]
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying VictoriaMetrics: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if VictoriaMetrics is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

class AnomalyDetectionService:
    """Main anomaly detection service"""
    
    def __init__(self):
        self.vm_client = VictoriaMetricsClient()
        self.detectors = SimpleAnomalyDetectors()
        self.nats_client = None
        self.health_status = {"healthy": False, "vm_connected": False, "nats_connected": False}
        
        # Metric queries to monitor
        self.metric_queries = [
            MetricQuery(
                name="cpu_usage",
                query="100 - (avg(irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
                threshold=0.7
            ),
            MetricQuery(
                name="memory_usage", 
                query="(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
                threshold=0.6
            ),
            MetricQuery(
                name="disk_usage",
                query="100 - ((node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"}) * 100)",
                threshold=0.8
            )
        ]
    
    async def connect_nats(self):
        """Connect to NATS"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect("nats://nats:4222")
            
            # Subscribe to anomalous logs from Vector
            await self.nats_client.subscribe("logs.anomalous", cb=self.process_anomalous_log)
            
            # Simple connection - no JetStream for now to avoid complexity
            logger.info("Connected to NATS and subscribed to anomalous logs")
            self.health_status["nats_connected"] = True
                
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
            # Don't raise, continue without NATS for now
    
    async def process_anomalous_log(self, msg):
        """Process individual anomalous log messages from Vector"""
        try:
            log_data = json.loads(msg.data.decode())
            
            # Extract tracking information from message
            message = log_data.get('message', '')
            tracking_id = log_data.get('tracking_id')
            
            # Log processing for tracking
            logger.info(f"Processing anomalous log: tracking_id={tracking_id}, message='{message[:100]}...'")
            
            # Create log-based anomaly event
            event = AnomalyEvent(
                timestamp=datetime.now(),
                metric_name="log_anomaly",
                metric_value=1.0,  # Binary: anomaly detected or not
                anomaly_score=0.9 if log_data.get('anomaly_severity') == 'critical' else 0.8,
                anomaly_type="log_pattern",
                detector_name="log_pattern_detector",
                threshold=0.7,
                metadata={
                    "log_message": message,
                    "tracking_id": tracking_id,
                    "log_level": log_data.get('level'),
                    "source_host": log_data.get('host'),
                    "service": log_data.get('service'),
                    "anomaly_severity": log_data.get('anomaly_severity', 'medium'),
                    "original_timestamp": log_data.get('timestamp')
                },
                labels=log_data.get('labels', {})
            )
            
            await self.publish_anomaly(event)
            logger.info(f"Published log anomaly with tracking ID: {tracking_id}")
            
        except Exception as e:
            logger.error(f"Error processing anomalous log: {e}")
    
    async def publish_anomaly(self, event: AnomalyEvent):
        """Publish anomaly event to NATS"""
        try:
            if not self.nats_client or self.nats_client.is_closed:
                logger.warning("NATS not connected, cannot publish anomaly")
                return
            
            event_json = json.dumps(event.to_dict())
            await self.nats_client.publish("anomaly.detected", event_json.encode())
            logger.info(f"Published anomaly: {event.metric_name} = {event.anomaly_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error publishing anomaly event: {e}")
    
    async def process_metrics(self):
        """Process metrics and detect anomalies"""
        logger.info("Processing metrics for anomaly detection...")
        
        for metric_query in self.metric_queries:
            if not metric_query.enabled:
                continue
                
            try:
                results = self.vm_client.query_instant(metric_query.query)
                
                for result in results:
                    value = result['value']
                    metric_labels = result['metric']
                    
                    # Get anomaly scores from all detectors
                    scores = self.detectors.update_and_detect(metric_query.name, value)
                    
                    # Check if any detector found an anomaly above threshold
                    for detector_name, score in scores.items():
                        if score > metric_query.threshold:
                            event = AnomalyEvent(
                                timestamp=datetime.now(),
                                metric_name=metric_query.name,
                                metric_value=value,
                                anomaly_score=score,
                                anomaly_type="statistical",
                                detector_name=detector_name,
                                threshold=metric_query.threshold,
                                metadata={
                                    "query": metric_query.query,
                                    "vm_timestamp": result['timestamp']
                                },
                                labels=metric_labels
                            )
                            
                            await self.publish_anomaly(event)
                            
            except Exception as e:
                logger.error(f"Error processing metric {metric_query.name}: {e}")
    
    async def health_check_loop(self):
        """Periodic health check loop"""
        while True:
            try:
                vm_healthy = self.vm_client.health_check()
                nats_healthy = self.nats_client and not self.nats_client.is_closed
                
                self.health_status["vm_connected"] = vm_healthy
                self.health_status["nats_connected"] = nats_healthy
                self.health_status["healthy"] = vm_healthy and nats_healthy
                
                logger.info(f"Health check - VM: {vm_healthy}, NATS: {nats_healthy}")
                
                if not vm_healthy:
                    logger.warning("VictoriaMetrics is not healthy")
                if not nats_healthy:
                    logger.warning("NATS is not healthy")
                    
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(30)
    
    async def detection_loop(self):
        """Main anomaly detection loop"""
        logger.info("Starting anomaly detection loop...")
        
        while True:
            try:
                await self.process_metrics()
                await asyncio.sleep(10)  # Process every 10 seconds
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                await asyncio.sleep(10)
    
    async def run_background_tasks(self):
        """Run background detection and health check tasks"""
        logger.info("Starting AIOps NAAS Anomaly Detection Service v0.2")
        
        # Connect to NATS
        await self.connect_nats()
        
        # Wait for VictoriaMetrics to be ready
        while not self.vm_client.health_check():
            logger.info("Waiting for VictoriaMetrics to be ready...")
            await asyncio.sleep(5)
        
        self.health_status["vm_connected"] = True
        logger.info("VictoriaMetrics is ready, starting detection loops")
        
        # Start background tasks
        await asyncio.gather(
            self.detection_loop(),
            self.health_check_loop()
        )

# FastAPI app for health checks
app = FastAPI(title="AIOps Anomaly Detection Service")
service = AnomalyDetectionService()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return service.health_status

@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring"""
    return {
        "detector_windows": {k: len(v) for k, v in service.detectors.metric_history.items()},
        "queries": [q.name for q in service.metric_queries if q.enabled]
    }

async def main():
    """Main entry point"""
    # Start background detection tasks
    background_task = asyncio.create_task(service.run_background_tasks())
    
    # Start FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
        if service.nats_client:
            await service.nats_client.close()
    except Exception as e:
        logger.error(f"Service error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())