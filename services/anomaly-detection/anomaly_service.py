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
from clickhouse_driver import Client as ClickHouseDriverClient

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

class ClickHouseClient:
    """ClickHouse client for historical data analysis"""
    
    def __init__(self):
        import os
        clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        clickhouse_user = os.getenv('CLICKHOUSE_USER', 'default')
        clickhouse_password = os.getenv('CLICKHOUSE_PASSWORD', 'clickhouse123')
        self.client = ClickHouseDriverClient(host=clickhouse_host, port=9000, user=clickhouse_user, password=clickhouse_password)
        
    def get_historical_baselines(self, metric_name: str, days: int = 7) -> Dict[str, float]:
        """Get historical baseline metrics for comparison"""
        try:
            query = f"""
            SELECT 
                AVG(toFloat64OrZero(extractAll(message, '[0-9]+\\.?[0-9]*')[1])) as avg_value,
                quantile(0.5)(toFloat64OrZero(extractAll(message, '[0-9]+\\.?[0-9]*')[1])) as median_value,
                quantile(0.95)(toFloat64OrZero(extractAll(message, '[0-9]+\\.?[0-9]*')[1])) as p95_value,
                quantile(0.99)(toFloat64OrZero(extractAll(message, '[0-9]+\\.?[0-9]*')[1])) as p99_value,
                COUNT(*) as sample_count
            FROM logs.raw 
            WHERE source = 'host_metrics'
              AND message LIKE '%{metric_name}%'
              AND timestamp >= now() - INTERVAL {days} DAY
              AND timestamp < now() - INTERVAL 1 HOUR
            """
            
            result = self.client.execute(query)
            if result and result[0][4] > 0:  # sample_count > 0
                return {
                    'avg': float(result[0][0]) if result[0][0] is not None else 0.0,
                    'median': float(result[0][1]) if result[0][1] is not None else 0.0,
                    'p95': float(result[0][2]) if result[0][2] is not None else 0.0,
                    'p99': float(result[0][3]) if result[0][3] is not None else 0.0,
                    'sample_count': int(result[0][4])
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error getting historical baselines for {metric_name}: {e}")
            return {}
    
    def get_correlation_patterns(self, current_anomaly: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find historical patterns that correlate with current anomaly"""
        try:
            # Look for similar anomaly patterns in the past
            query = f"""
            SELECT 
                message,
                host,
                service,
                timestamp,
                COUNT(*) OVER (PARTITION BY toStartOfHour(timestamp)) as hourly_count
            FROM logs.raw 
            WHERE source IN ('syslog', 'host_metrics', 'snmp')
              AND (
                message ILIKE '%error%' OR 
                message ILIKE '%critical%' OR 
                message ILIKE '%fail%' OR
                (source = 'host_metrics' AND message LIKE '%{current_anomaly.get("metric_name", "")}%')
              )
              AND timestamp >= now() - INTERVAL 30 DAY
              AND timestamp <= now() - INTERVAL 1 HOUR
            ORDER BY timestamp DESC
            LIMIT 100
            """
            
            results = self.client.execute(query)
            patterns = []
            
            for row in results:
                patterns.append({
                    'message': row[0],
                    'host': row[1], 
                    'service': row[2],
                    'timestamp': row[3].isoformat() if row[3] else None,
                    'hourly_count': row[4]
                })
                
            return patterns
            
        except Exception as e:
            logger.error(f"Error getting correlation patterns: {e}")
            return []
    
    def get_incident_resolution_history(self, anomaly_type: str) -> List[Dict[str, Any]]:
        """Get historical incident resolutions for similar anomalies"""
        try:
            query = f"""
            SELECT 
                incident_id,
                incident_type,
                description,
                resolution_actions,
                resolution_time_minutes,
                success_rate,
                created_at
            FROM incidents 
            WHERE incident_type ILIKE '%{anomaly_type}%'
              AND status = 'resolved'
              AND created_at >= now() - INTERVAL 90 DAY
            ORDER BY created_at DESC
            LIMIT 50
            """
            
            results = self.client.execute(query)
            resolutions = []
            
            for row in results:
                resolutions.append({
                    'incident_id': row[0],
                    'incident_type': row[1],
                    'description': row[2],
                    'resolution_actions': row[3],
                    'resolution_time_minutes': row[4],
                    'success_rate': row[5],
                    'created_at': row[6].isoformat() if row[6] else None
                })
                
            return resolutions
            
        except Exception as e:
            logger.error(f"Error getting incident resolution history: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check ClickHouse connectivity"""
        try:
            self.client.execute("SELECT 1")
            return True
        except:
            return False

class DeviceRegistryClient:
    """Client for querying the Device Registry service for ship_id/device_id mappings"""
    
    def __init__(self, base_url: str = "http://device-registry:8080"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self._cache = {}  # Simple in-memory cache for lookups
        self._cache_ttl = 300  # 5 minute cache TTL
    
    def _get_cache_key(self, hostname: str) -> str:
        """Generate cache key for hostname lookup"""
        return f"registry_{hostname}"
    
    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry or 'timestamp' not in cache_entry:
            return False
        return (time.time() - cache_entry['timestamp']) < self._cache_ttl
    
    def lookup_hostname(self, hostname: str) -> Optional[Dict[str, Any]]:
        """Lookup ship_id and device info by hostname or IP address with caching"""
        if not hostname or hostname in ['unknown', 'localhost', '']:
            return None
            
        cache_key = self._get_cache_key(hostname)
        
        # Check cache first
        if cache_key in self._cache and self._is_cache_valid(self._cache[cache_key]):
            logger.debug(f"Registry cache hit for hostname: {hostname}")
            return self._cache[cache_key]['data']
        
        try:
            # Query the device registry
            response = self.session.get(
                f"{self.base_url}/lookup/{hostname}", 
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                mapping = result.get('mapping')
                
                if mapping:
                    # Cache the successful lookup
                    self._cache[cache_key] = {
                        'data': mapping,
                        'timestamp': time.time()
                    }
                    
                    logger.debug(f"Registry lookup success for {hostname}: {mapping['ship_id']}")
                    return mapping
                    
            elif response.status_code == 404:
                logger.debug(f"Hostname {hostname} not found in registry")
                return None
            else:
                logger.warning(f"Registry lookup failed for {hostname}: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Registry lookup error for {hostname}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected registry lookup error for {hostname}: {e}")
            return None
    
    def health_check(self) -> bool:
        """Check if Device Registry service is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

class AnomalyDetectionService:
    """Main anomaly detection service with historical analysis"""
    
    def __init__(self):
        self.vm_client = VictoriaMetricsClient()
        self.clickhouse_client = ClickHouseClient()
        self.device_registry_client = DeviceRegistryClient()
        self.detectors = SimpleAnomalyDetectors()
        self.nats_client = None
        self.health_status = {"healthy": False, "vm_connected": False, "nats_connected": False, "clickhouse_connected": False, "registry_connected": False}
        
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
            log_level = log_data.get('level', '').upper()
            anomaly_severity = log_data.get('anomaly_severity', 'low').lower()
            
            # CRITICAL FIX: Only process ERROR, CRITICAL, WARNING logs - skip INFO/DEBUG
            if log_level in ['INFO', 'DEBUG', 'TRACE'] and anomaly_severity in ['info', 'low', 'debug']:
                logger.debug(f"Skipping non-critical log: level={log_level}, severity={anomaly_severity}, tracking_id={tracking_id}")
                return
            
            # CRITICAL FIX: Additional filtering for normal operational messages
            if self._is_normal_operational_message(message):
                logger.debug(f"Skipping normal operational message: {message[:50]}...")
                return
            
            # Log processing for tracking (only for actual anomalies)
            logger.info(f"Processing anomalous log: tracking_id={tracking_id}, level={log_level}, severity={anomaly_severity}, message='{message[:100]}...'")
            
            # CRITICAL FIX: Set appropriate anomaly score based on severity
            anomaly_score = self._calculate_anomaly_score(log_level, anomaly_severity)
            
            # Create log-based anomaly event
            event = AnomalyEvent(
                timestamp=datetime.now(),
                metric_name="log_anomaly",
                metric_value=1.0,  # Binary: anomaly detected or not
                anomaly_score=anomaly_score,
                anomaly_type="log_pattern",
                detector_name="log_pattern_detector",
                threshold=0.7,
                metadata={
                    "log_message": message,
                    "tracking_id": tracking_id,
                    "log_level": log_level,
                    "source_host": log_data.get('host'),
                    "service": log_data.get('service'),
                    "anomaly_severity": anomaly_severity,
                    "original_timestamp": log_data.get('timestamp'),
                    # CRITICAL FIX: Add ship_id, device_id extraction
                    "ship_id": self._extract_ship_id(log_data),
                    "device_id": self._extract_device_id(log_data)
                },
                labels=log_data.get('labels', {})
            )
            
            await self.publish_anomaly(event)
            logger.info(f"Published log anomaly with tracking ID: {tracking_id}, score: {anomaly_score}")
            
        except Exception as e:
            logger.error(f"Error processing anomalous log: {e}")
    
    def _is_normal_operational_message(self, message: str) -> bool:
        """Check if message is a normal operational log that shouldn't create incidents"""
        normal_patterns = [
            r'Metric: .+ = \d+',  # Normal metric reports
            r'Health check',
            r'Status: OK',
            r'Connection established',
            r'Startup complete',
            r'Heartbeat',
            r'Process started',
            r'Configuration loaded'
        ]
        
        for pattern in normal_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    def _calculate_anomaly_score(self, log_level: str, anomaly_severity: str) -> float:
        """Calculate appropriate anomaly score based on log level and severity"""
        if log_level in ['FATAL', 'CRITICAL'] or anomaly_severity == 'critical':
            return 0.95
        elif log_level == 'ERROR' or anomaly_severity in ['high', 'error']:
            return 0.85
        elif log_level in ['WARN', 'WARNING'] or anomaly_severity in ['medium', 'warning']:
            return 0.75
        else:
            return 0.6
    
    def _extract_ship_id(self, log_data: dict) -> str:
        """Extract ship_id from log data with device registry lookup and intelligent fallbacks"""
        # Try direct ship_id field first
        if log_data.get('ship_id'):
            return log_data['ship_id']
        
        # Try device registry lookup using hostname
        host = log_data.get('host', '')
        if host and host != 'unknown':
            registry_result = self.device_registry_client.lookup_hostname(host)
            if registry_result and registry_result.get('ship_id'):
                logger.debug(f"Registry lookup success for host {host}: {registry_result['ship_id']}")
                return registry_result['ship_id']
        
        # Try device registry lookup using IP address from metadata
        source_host = log_data.get('metadata', {}).get('source_host', '') if isinstance(log_data.get('metadata'), dict) else ''
        if source_host and source_host != host and source_host != 'unknown':
            registry_result = self.device_registry_client.lookup_hostname(source_host)
            if registry_result and registry_result.get('ship_id'):
                logger.debug(f"Registry lookup success for source_host {source_host}: {registry_result['ship_id']}")
                return registry_result['ship_id']
        
        # Try to derive from hostname as fallback (existing logic)
        if host and '-' in host:
            # e.g., "ubuntu-system-01" -> "ubuntu-ship" 
            derived_ship = host.split('-')[0] + '-ship'
            logger.debug(f"Derived ship_id from hostname {host}: {derived_ship}")
            return derived_ship
        elif host and host != 'unknown':
            derived_ship = host + '-ship'
            logger.debug(f"Derived ship_id from hostname {host}: {derived_ship}")
            return derived_ship
        
        # Try labels as another fallback
        labels = log_data.get('labels', {})
        if labels.get('ship_id'):
            return labels['ship_id']
        
        logger.warning(f"Could not resolve ship_id for log data with host={host}, source_host={source_host}")
        return 'unknown-ship'
    
    def _extract_device_id(self, log_data: dict) -> str:
        """Extract device_id from log data with device registry lookup"""
        # Try direct device_id field
        if log_data.get('device_id'):
            return log_data['device_id']
        
        # Try device registry lookup using hostname
        host = log_data.get('host', '')
        if host and host != 'unknown':
            registry_result = self.device_registry_client.lookup_hostname(host)
            if registry_result and registry_result.get('device_id'):
                logger.debug(f"Registry device_id lookup success for host {host}: {registry_result['device_id']}")
                return registry_result['device_id']
        
        # Try device registry lookup using IP address from metadata
        source_host = log_data.get('metadata', {}).get('source_host', '') if isinstance(log_data.get('metadata'), dict) else ''
        if source_host and source_host != host and source_host != 'unknown':
            registry_result = self.device_registry_client.lookup_hostname(source_host)
            if registry_result and registry_result.get('device_id'):
                logger.debug(f"Registry device_id lookup success for source_host {source_host}: {registry_result['device_id']}")
                return registry_result['device_id']
        
        # Fallback to hostname if registry lookup failed
        if host and host != 'unknown':
            logger.debug(f"Using hostname as device_id fallback: {host}")
            return host
        
        # Try service name
        service = log_data.get('service', '')
        if service and service != 'unknown':
            logger.debug(f"Using service name as device_id fallback: {service}")
            return service
        
        logger.warning(f"Could not resolve device_id for log data with host={host}, source_host={source_host}")
        return 'unknown-device'
    
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
        """Process metrics with historical baseline analysis"""
        logger.info("Processing metrics for anomaly detection...")
        
        for metric_query in self.metric_queries:
            if not metric_query.enabled:
                continue
                
            try:
                # Get current metrics
                results = self.vm_client.query_instant(metric_query.query)
                
                # Get historical baselines for comparison
                baselines = self.clickhouse_client.get_historical_baselines(metric_query.name)
                
                for result in results:
                    value = result['value']
                    metric_labels = result['metric']
                    
                    # Enhanced anomaly detection with historical context
                    scores = self.detectors.update_and_detect(metric_query.name, value)
                    
                    # Historical baseline comparison
                    historical_anomaly_score = 0.0
                    if baselines and 'p95' in baselines:
                        if value > baselines['p95']:
                            historical_anomaly_score = min((value - baselines['p95']) / (baselines['p99'] - baselines['p95'] + 0.001), 1.0)
                    
                    # Combine statistical and historical scores
                    max_statistical_score = max(scores.values()) if scores else 0.0
                    combined_score = max(max_statistical_score, historical_anomaly_score)
                    
                    # Check if any detection method found an anomaly above threshold
                    if combined_score > metric_query.threshold:
                        # Get correlation patterns and resolution history
                        correlation_patterns = self.clickhouse_client.get_correlation_patterns({
                            'metric_name': metric_query.name,
                            'value': value,
                            'timestamp': datetime.now()
                        })
                        
                        resolution_history = self.clickhouse_client.get_incident_resolution_history(metric_query.name)
                        
                        # Create enhanced anomaly event
                        event = AnomalyEvent(
                            timestamp=datetime.now(),
                            metric_name=metric_query.name,
                            metric_value=value,
                            anomaly_score=combined_score,
                            anomaly_type="statistical_with_baseline",
                            detector_name="enhanced_detector",
                            threshold=metric_query.threshold,
                            metadata={
                                "query": metric_query.query,
                                "vm_timestamp": result['timestamp'],
                                "statistical_scores": scores,
                                "historical_baselines": baselines,
                                "historical_anomaly_score": historical_anomaly_score,
                                "combined_score": combined_score,
                                "correlation_patterns_count": len(correlation_patterns),
                                "resolution_history_count": len(resolution_history),
                                "similar_incidents": resolution_history[:3]  # Top 3 similar incidents
                            },
                            labels=metric_labels
                        )
                        
                        await self.publish_anomaly(event)
                        logger.info(f"Published enhanced anomaly: {metric_query.name} = {combined_score:.3f} (statistical: {max_statistical_score:.3f}, historical: {historical_anomaly_score:.3f})")
                        
            except Exception as e:
                logger.error(f"Error processing metric {metric_query.name}: {e}")
    
    async def health_check_loop(self):
        """Periodic health check loop with ClickHouse and Device Registry"""
        while True:
            try:
                vm_healthy = self.vm_client.health_check()
                clickhouse_healthy = self.clickhouse_client.health_check()
                registry_healthy = self.device_registry_client.health_check()
                nats_healthy = self.nats_client and not self.nats_client.is_closed
                
                self.health_status["vm_connected"] = vm_healthy
                self.health_status["clickhouse_connected"] = clickhouse_healthy
                self.health_status["registry_connected"] = registry_healthy
                self.health_status["nats_connected"] = nats_healthy
                self.health_status["healthy"] = vm_healthy and clickhouse_healthy and nats_healthy and registry_healthy
                
                logger.info(f"Health check - VM: {vm_healthy}, ClickHouse: {clickhouse_healthy}, Registry: {registry_healthy}, NATS: {nats_healthy}")
                
                if not vm_healthy:
                    logger.warning("VictoriaMetrics is not healthy")
                if not clickhouse_healthy:
                    logger.warning("ClickHouse is not healthy")
                if not registry_healthy:
                    logger.warning("Device Registry is not healthy")
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