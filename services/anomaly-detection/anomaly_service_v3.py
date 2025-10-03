#!/usr/bin/env python3
"""
AIOps NAAS v3.0 - Anomaly Detection Service

Refactored to use V3 data contracts with:
- Pydantic V2 models from aiops_core
- Tracking ID generation and propagation
- Structured logging with tracking_id context
- Error message preservation
- Health and stats endpoints
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import deque
from fastapi import FastAPI
import uvicorn

import requests
from nats.aio.client import Client as NATS

# V3 imports from aiops_core
from aiops_core.models import AnomalyDetected, Severity, Domain
from aiops_core.utils import (
    StructuredLogger,
    generate_tracking_id,
    tracked_operation,
    extract_error_message
)

# FastAPI app
app = FastAPI(title="Anomaly Detection V3", version="3.0")

# V3 Structured logger
logger = StructuredLogger(__name__)

class SimpleAnomalyDetectors:
    """Collection of simple anomaly detectors"""
    
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.metric_history = {}  # metric_name -> deque of values
        self.detectors = {
            'zscore': self._zscore_detector,
            'ewma': self._ewma_detector,
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
        
        import statistics
        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        
        if stdev == 0:
            return 0.0
        
        zscore = abs((value - mean) / stdev)
        return min(zscore / 3.0, 1.0)  # Normalize to 0-1
    
    def _ewma_detector(self, metric_name: str, value: float, alpha: float = 0.3) -> float:
        """EWMA based anomaly detection"""
        history = self._get_history(metric_name)
        
        if len(history) < 5:
            return 0.0
        
        # Calculate EWMA
        ewma = value
        for hist_val in reversed(list(history)):
            ewma = alpha * hist_val + (1 - alpha) * ewma
        
        deviation = abs(value - ewma) / (ewma + 1e-6)
        return min(deviation, 1.0)
    
    def _threshold_detector(self, metric_name: str, value: float, threshold: float = 0.8) -> float:
        """Simple threshold based detection"""
        if value > threshold:
            return (value - threshold) / (1.0 - threshold)
        return 0.0
    
    def detect(self, metric_name: str, value: float, detector_type: str = 'zscore') -> float:
        """Run detection and update history"""
        history = self._get_history(metric_name)
        
        # Run detector
        detector = self.detectors.get(detector_type, self._zscore_detector)
        score = detector(metric_name, value)
        
        # Update history
        history.append(value)
        
        return score


class AnomalyDetectionService:
    """V3 Anomaly Detection Service with tracking_id and error propagation"""
    
    def __init__(self):
        self.nats_client = None
        self.detectors = SimpleAnomalyDetectors(window_size=50)
        self.stats = {
            "processed": 0,
            "anomalies": 0,
            "errors": 0
        }
        
        # VictoriaMetrics config
        self.vm_url = "http://victoriametrics:8428"
        self.queries = [
            {"name": "cpu_usage", "query": "node_cpu_seconds_total", "threshold": 0.5},
            {"name": "memory_usage", "query": "node_memory_MemAvailable_bytes", "threshold": 0.6},
            {"name": "disk_io", "query": "node_disk_io_time_seconds_total", "threshold": 0.7},
        ]
    
    async def connect_nats(self):
        """Connect to NATS"""
        tracking_id = generate_tracking_id()
        logger.info("Connecting to NATS...", tracking_id=tracking_id)
        
        self.nats_client = NATS()
        try:
            await self.nats_client.connect("nats://nats:4222")
            logger.info("Connected to NATS successfully", tracking_id=tracking_id)
        except Exception as e:
            error_msg = extract_error_message(e)
            logger.error(f"Failed to connect to NATS: {error_msg}", tracking_id=tracking_id)
            raise
    
    @tracked_operation("query_victoriametrics")
    def query_victoriametrics(self, query: str, tracking_id: str) -> List[Dict]:
        """Query VictoriaMetrics for metrics"""
        try:
            # Query VM (simplified)
            url = f"{self.vm_url}/api/v1/query"
            response = requests.get(url, params={"query": query}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('result', [])
            else:
                logger.warning(f"VM query failed: {response.status_code}", tracking_id=tracking_id)
                return []
                
        except Exception as e:
            error_msg = extract_error_message(e)
            logger.error(f"Error querying VictoriaMetrics: {error_msg}", tracking_id=tracking_id)
            self.stats["errors"] += 1
            return []
    
    async def process_metrics(self):
        """Process metrics and detect anomalies"""
        tracking_id = generate_tracking_id()
        logger.info("Processing metrics batch", tracking_id=tracking_id)
        
        for query_config in self.queries:
            try:
                # Query metrics
                results = self.query_victoriametrics(query_config["query"], tracking_id)
                
                for result in results:
                    metric_name = query_config["name"]
                    value = float(result.get("value", [0, 0])[1])
                    labels = result.get("metric", {})
                    
                    # Detect anomaly
                    score = self.detectors.detect(metric_name, value, detector_type='zscore')
                    
                    self.stats["processed"] += 1
                    
                    # If anomaly detected (score > 0.5)
                    if score > 0.5:
                        await self.publish_anomaly(
                            tracking_id=tracking_id,
                            metric_name=metric_name,
                            value=value,
                            score=score,
                            labels=labels,
                            detector="zscore"
                        )
                        
            except Exception as e:
                error_msg = extract_error_message(e)
                logger.error(f"Error processing metric {query_config['name']}: {error_msg}", 
                           tracking_id=tracking_id)
                self.stats["errors"] += 1
    
    async def publish_anomaly(self, tracking_id: str, metric_name: str, value: float,
                            score: float, labels: Dict, detector: str):
        """Publish anomaly using V3 AnomalyDetected model"""
        try:
            # Create V3 AnomalyDetected event
            anomaly = AnomalyDetected(
                tracking_id=tracking_id,
                ts=datetime.now(),
                msg=f"Anomaly detected in {metric_name}",
                ship_id=labels.get("ship_id", "unknown"),
                domain=self._map_domain(metric_name),
                severity=self._map_severity(score),
                metric=metric_name,
                value=value,
                score=score,
                detector=detector,
                meta={
                    "labels": labels,
                    "threshold": 0.5
                }
            )
            
            # Publish to NATS
            subject = "anomaly.detected"
            payload = anomaly.model_dump_json()
            
            await self.nats_client.publish(subject, payload.encode())
            
            self.stats["anomalies"] += 1
            logger.info(f"Published anomaly: {metric_name} score={score:.2f}", 
                       tracking_id=tracking_id)
            
        except Exception as e:
            error_msg = extract_error_message(e)
            logger.error(f"Error publishing anomaly: {error_msg}", tracking_id=tracking_id)
            self.stats["errors"] += 1
    
    def _map_domain(self, metric_name: str) -> Domain:
        """Map metric name to domain"""
        if "cpu" in metric_name or "memory" in metric_name:
            return Domain.SYSTEM
        elif "network" in metric_name or "interface" in metric_name:
            return Domain.NETWORK
        else:
            return Domain.APPLICATION
    
    def _map_severity(self, score: float) -> Severity:
        """Map anomaly score to severity"""
        if score >= 0.9:
            return Severity.CRITICAL
        elif score >= 0.7:
            return Severity.HIGH
        elif score >= 0.5:
            return Severity.MEDIUM
        else:
            return Severity.LOW
    
    async def run(self):
        """Main service loop"""
        tracking_id = generate_tracking_id()
        logger.info("Starting Anomaly Detection Service V3", tracking_id=tracking_id)
        
        await self.connect_nats()
        
        while True:
            try:
                await self.process_metrics()
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                error_msg = extract_error_message(e)
                logger.error(f"Error in main loop: {error_msg}", tracking_id=tracking_id)
                await asyncio.sleep(5)


# Global service instance
service = AnomalyDetectionService()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "anomaly-detection-v3",
        "version": "3.0",
        "stats": service.stats,
        "nats": {
            "connected": service.nats_client is not None and service.nats_client.is_connected,
            "output": "anomaly.detected"
        }
    }

@app.get("/stats")
async def stats():
    """Statistics endpoint"""
    return {
        "service": "anomaly-detection-v3",
        "stats": service.stats,
        "detectors": list(service.detectors.detectors.keys())
    }

@app.on_event("startup")
async def startup():
    """Start background tasks"""
    asyncio.create_task(service.run())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
