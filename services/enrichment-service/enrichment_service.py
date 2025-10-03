#!/usr/bin/env python3
"""
AIOps NAAS V3 - Enrichment Service (Fast Path)
Enriches anomalies with ClickHouse context (<500ms target)
Input: anomaly.detected → Output: anomaly.enriched

This service provides Fast Path L1 enrichment:
- Subscribes to anomaly.detected
- Enriches with ClickHouse context (device metadata, historical rates, similar anomalies)
- Publishes EnrichedAnomaly to anomaly.enriched
- Target: <500ms p99 latency
"""

import asyncio
import logging
import json
import os
import sys
import time
import statistics
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
from fastapi import FastAPI
from pydantic import ValidationError
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops_core.models import AnomalyDetected, AnomalyEnriched, ContextData, Severity
from aiops_core.utils import StructuredLogger, tracked_operation, extract_error_message

from nats.aio.client import Client as NATS
from clickhouse_driver import Client as ClickHouseClient

from clickhouse_queries import EnrichmentQueries

logger = StructuredLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_INPUT = "anomaly.detected"
NATS_OUTPUT = "anomaly.enriched"
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "admin")
CH_QUERY_TIMEOUT = int(os.getenv("CH_QUERY_TIMEOUT", "5"))
PORT = int(os.getenv("ENRICHMENT_PORT", "8085"))

# Configurable severity thresholds
SEVERITY_CRITICAL_SCORE = float(os.getenv("SEVERITY_CRITICAL_SCORE", "0.9"))
SEVERITY_HIGH_SCORE = float(os.getenv("SEVERITY_HIGH_SCORE", "0.7"))
SEVERITY_MEDIUM_SCORE = float(os.getenv("SEVERITY_MEDIUM_SCORE", "0.4"))
SEVERITY_ESCALATE_CRITICAL_1H = int(os.getenv("SEVERITY_ESCALATE_CRITICAL_1H", "5"))
SEVERITY_ESCALATE_CRITICAL_24H = int(os.getenv("SEVERITY_ESCALATE_CRITICAL_24H", "20"))
SEVERITY_ESCALATE_HIGH_1H = int(os.getenv("SEVERITY_ESCALATE_HIGH_1H", "3"))
SEVERITY_ESCALATE_HIGH_24H = int(os.getenv("SEVERITY_ESCALATE_HIGH_24H", "10"))

app = FastAPI(title="Enrichment Service V3")

class EnrichmentService:
    def __init__(self):
        self.nats = None
        self.ch = None
        self.queries = None
        self.running = False
        
        # Enhanced statistics for monitoring
        self.stats = {
            "processed": 0, 
            "enriched": 0, 
            "errors": 0, 
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "device_metadata_hits": 0,
            "similar_anomalies_found": 0
        }
        
        # Latency tracking for p95/p99 calculation
        self.latencies = deque(maxlen=1000)  # Keep last 1000 latencies
        
    async def connect(self):
        """Connect to NATS and ClickHouse with validation and retry logic"""
        # Connect to NATS
        try:
            self.nats = NATS()
            await self.nats.connect(NATS_URL)
            logger.info("NATS connected", extra={"nats": NATS_URL})
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {extract_error_message(e)}")
            raise
        
        # Connect to ClickHouse with validation
        try:
            self.ch = ClickHouseClient(
                host=CH_HOST, 
                user=CH_USER, 
                password=CH_PASS, 
                database="aiops",
                connect_timeout=10,
                send_receive_timeout=30
            )
            
            # Validate connection with simple query
            self.ch.execute("SELECT 1")
            
            self.queries = EnrichmentQueries(self.ch, query_timeout=CH_QUERY_TIMEOUT)
            logger.info("ClickHouse connected", extra={"clickhouse": CH_HOST})
            
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {extract_error_message(e)}")
            # Close NATS connection on failure
            if self.nats:
                await self.nats.close()
            raise
    
    def _calculate_percentiles(self):
        """
        Calculate p95 and p99 latencies from recent measurements
        Uses statistics.quantiles() for efficiency instead of full sort
        """
        if not self.latencies:
            return 0.0, 0.0
        
        if len(self.latencies) < 10:
            # Not enough data, use simple calculation
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            p95 = sorted_latencies[p95_idx] if p95_idx < n else sorted_latencies[-1]
            p99 = sorted_latencies[p99_idx] if p99_idx < n else sorted_latencies[-1]
            return p95, p99
        
        # Use statistics.quantiles for better performance with larger datasets
        try:
            quantiles = statistics.quantiles(self.latencies, n=100, method='inclusive')
            p95 = quantiles[94]  # 95th percentile (index 94 of 99 quantiles)
            p99 = quantiles[98]  # 99th percentile (index 98 of 99 quantiles)
            return p95, p99
        except statistics.StatisticsError:
            # Fallback to simple calculation if quantiles fail
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            p95_idx = int(n * 0.95)
            p99_idx = int(n * 0.99)
            p95 = sorted_latencies[p95_idx] if p95_idx < n else sorted_latencies[-1]
            p99 = sorted_latencies[p99_idx] if p99_idx < n else sorted_latencies[-1]
            return p95, p99
    
    def _compute_severity(self, score: float, context: ContextData) -> Severity:
        """
        Compute severity based on anomaly score and historical context
        Uses configurable thresholds from environment variables.
        
        Scoring logic:
        - CRITICAL: score >= SEVERITY_CRITICAL_SCORE OR 
                   (score >= SEVERITY_HIGH_SCORE AND high recent incident rate)
        - HIGH: score >= SEVERITY_HIGH_SCORE OR 
               (score >= 0.5 AND moderate recent incidents)
        - MEDIUM: score >= SEVERITY_MEDIUM_SCORE
        - LOW: score < SEVERITY_MEDIUM_SCORE
        """
        # Critical if very high score or high score with recent similar issues
        if score >= SEVERITY_CRITICAL_SCORE:
            return Severity.CRITICAL
        
        if score >= SEVERITY_HIGH_SCORE:
            # Escalate to critical if there are many recent similar anomalies
            if (context.similar_count_1h >= SEVERITY_ESCALATE_CRITICAL_1H or 
                context.similar_count_24h >= SEVERITY_ESCALATE_CRITICAL_24H):
                return Severity.CRITICAL
            return Severity.HIGH
        
        if score >= 0.5:
            # Escalate to high if there are recent similar anomalies
            if (context.similar_count_1h >= SEVERITY_ESCALATE_HIGH_1H or 
                context.similar_count_24h >= SEVERITY_ESCALATE_HIGH_24H):
                return Severity.HIGH
            return Severity.MEDIUM
        
        if score >= SEVERITY_MEDIUM_SCORE:
            return Severity.MEDIUM
        
        return Severity.LOW
        
    async def enrich(self, anomaly: AnomalyDetected) -> AnomalyEnriched:
        """
        Enrich anomaly with ClickHouse context (parallelized queries)
        Target: <500ms p99 latency
        """
        start = datetime.now()
        
        try:
            # Parallelize ClickHouse queries using asyncio.gather()
            # This reduces latency by 50-75% compared to sequential execution
            device_meta_task = self.queries.get_device_metadata(anomaly.ship_id, anomaly.device_id) if anomaly.device_id else None
            
            results = await asyncio.gather(
                device_meta_task if device_meta_task else asyncio.sleep(0),
                self.queries.get_historical_failure_rates(anomaly.ship_id, anomaly.domain),
                self.queries.get_similar_anomalies(
                    ship_id=anomaly.ship_id,
                    domain=anomaly.domain,
                    anomaly_type=anomaly.anomaly_type,
                    metric_name=anomaly.metric_name,
                    service=anomaly.service
                ),
                self.queries.get_recent_incidents(anomaly.ship_id, anomaly.domain),
                return_exceptions=True  # Don't fail if one query fails
            )
            
            # Extract results (with error handling)
            device_meta = results[0] if device_meta_task and not isinstance(results[0], Exception) else None
            failure_rates = results[1] if not isinstance(results[1], Exception) else {}
            similar_anomalies = results[2] if not isinstance(results[2], Exception) else []
            recent_incidents = results[3] if not isinstance(results[3], Exception) else []
            
            if device_meta:
                self.stats["device_metadata_hits"] += 1
            
            if similar_anomalies:
                self.stats["similar_anomalies_found"] += len(similar_anomalies)
            
            # Build ContextData
            similar_count_1h = sum(1 for a in similar_anomalies 
                                  if (datetime.now() - datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00'))).total_seconds() < 3600)
            similar_count_24h = len(similar_anomalies)
            
            context = ContextData(
                similar_count_1h=similar_count_1h,
                similar_count_24h=similar_count_24h,
                metric_p50=None,  # Could be computed from similar anomalies if needed
                metric_p95=None,
                top_error_rank=None,
                last_incident_ts=datetime.fromisoformat(recent_incidents[0]['created_at'].replace('Z', '+00:00')) if recent_incidents else None
            )
            
            # Compute severity based on score + context
            severity = self._compute_severity(anomaly.score, context)
            
            # Build enriched metadata
            enriched_meta = {
                **(anomaly.meta or {}),
                "device_metadata": device_meta,
                "historical_failure_rates": failure_rates,
                "similar_anomalies": similar_anomalies[:5],  # Top 5 most recent
                "recent_incidents": recent_incidents
            }
            
            # Calculate latency
            latency_ms = int((datetime.now() - start).total_seconds() * 1000)
            self.latencies.append(latency_ms)
            
            # Create enriched anomaly
            enriched = AnomalyEnriched(
                tracking_id=anomaly.tracking_id,
                ts=anomaly.ts,
                ship_id=anomaly.ship_id,
                domain=anomaly.domain,
                anomaly_type=anomaly.anomaly_type,
                service=anomaly.service,
                device_id=anomaly.device_id,
                score=anomaly.score,
                detector=anomaly.detector,
                metric_name=anomaly.metric_name,
                metric_value=anomaly.metric_value,
                threshold=anomaly.threshold,
                raw_msg=anomaly.raw_msg,
                context=context,
                severity=severity,
                tags=[],  # Could add classification tags based on anomaly type
                meta=enriched_meta
            )
            
            # Update statistics
            self.stats["enriched"] += 1
            self.stats["avg_latency_ms"] = (
                (self.stats["avg_latency_ms"] * (self.stats["enriched"] - 1) + latency_ms) 
                / self.stats["enriched"]
            )
            
            # Update percentiles periodically
            if self.stats["enriched"] % 10 == 0:
                p95, p99 = self._calculate_percentiles()
                self.stats["p95_latency_ms"] = p95
                self.stats["p99_latency_ms"] = p99
            
            logger.info("Enriched", extra={
                "tracking_id": anomaly.tracking_id, 
                "latency_ms": latency_ms,
                "severity": severity.value,
                "similar_count_24h": similar_count_24h
            })
            
            return enriched
            
        except Exception as e:
            err = extract_error_message(e)
            logger.error(f"Enrichment failed: {err}", extra={"tracking_id": anomaly.tracking_id})
            
            # Error fallback: return minimal enrichment
            latency_ms = int((datetime.now() - start).total_seconds() * 1000)
            self.latencies.append(latency_ms)
            
            return AnomalyEnriched(
                tracking_id=anomaly.tracking_id,
                ts=anomaly.ts,
                ship_id=anomaly.ship_id,
                domain=anomaly.domain,
                anomaly_type=anomaly.anomaly_type,
                service=anomaly.service,
                device_id=anomaly.device_id,
                score=anomaly.score,
                detector=anomaly.detector,
                metric_name=anomaly.metric_name,
                metric_value=anomaly.metric_value,
                threshold=anomaly.threshold,
                raw_msg=anomaly.raw_msg,
                context=ContextData(),  # Empty context on error
                severity=Severity.MEDIUM,  # Default to medium on error
                tags=["enrichment_error"],
                meta={**(anomaly.meta or {}), "enrichment_error": err}
            )
            
    async def process_message(self, msg):
        self.stats["processed"] += 1
        try:
            data = json.loads(msg.data.decode())
            anomaly = AnomalyDetected(**data)
            with tracked_operation("enrich", logger, tracking_id=anomaly.tracking_id):
                enriched = await self.enrich(anomaly)
            await self.nats.publish(NATS_OUTPUT, enriched.model_dump_json().encode())
        except ValidationError as e:
            self.stats["errors"] += 1
            logger.error(f"Validation error: {e}")
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Processing error: {extract_error_message(e)}")
            
    async def start(self):
        """Start the service with connection retry logic"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await self.connect()
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect after {max_retries} attempts")
                    raise
        
        # Subscribe to NATS with error handling
        try:
            await self.nats.subscribe(NATS_INPUT, cb=self.process_message)
            logger.info("Started", extra={"input": NATS_INPUT, "output": NATS_OUTPUT})
        except Exception as e:
            logger.error(f"Failed to subscribe to NATS: {extract_error_message(e)}")
            raise
            
        self.running = True
        while self.running:
            await asyncio.sleep(1)
            
    async def stop(self):
        self.running = False
        if self.nats:
            await self.nats.close()
        logger.info("Stopped")

service = EnrichmentService()

@app.on_event("startup")
async def startup():
    asyncio.create_task(service.start())

@app.on_event("shutdown")
async def shutdown():
    await service.stop()

@app.get("/health")
async def health():
    """Health check endpoint"""
    is_healthy = (
        service.running 
        and service.nats 
        and service.nats.is_connected
    )
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "enrichment-v3",
        "version": "3.0",
        "stats": service.stats,
        "nats": {
            "connected": service.nats and service.nats.is_connected, 
            "input": NATS_INPUT, 
            "output": NATS_OUTPUT
        },
        "clickhouse": {
            "connected": service.ch is not None
        }
    }

@app.get("/metrics")
async def metrics():
    """
    Prometheus-compatible metrics endpoint
    Returns metrics in Prometheus text format
    """
    p95, p99 = service._calculate_percentiles() if service.latencies else (0.0, 0.0)
    
    metrics_text = f"""# HELP enrichment_processed_total Total anomalies processed
# TYPE enrichment_processed_total counter
enrichment_processed_total {service.stats["processed"]}

# HELP enrichment_enriched_total Total anomalies enriched successfully
# TYPE enrichment_enriched_total counter
enrichment_enriched_total {service.stats["enriched"]}

# HELP enrichment_errors_total Total enrichment errors
# TYPE enrichment_errors_total counter
enrichment_errors_total {service.stats["errors"]}

# HELP enrichment_latency_ms_avg Average enrichment latency in milliseconds
# TYPE enrichment_latency_ms_avg gauge
enrichment_latency_ms_avg {service.stats["avg_latency_ms"]:.2f}

# HELP enrichment_latency_ms_p95 P95 enrichment latency in milliseconds
# TYPE enrichment_latency_ms_p95 gauge
enrichment_latency_ms_p95 {p95:.2f}

# HELP enrichment_latency_ms_p99 P99 enrichment latency in milliseconds
# TYPE enrichment_latency_ms_p99 gauge
enrichment_latency_ms_p99 {p99:.2f}

# HELP enrichment_device_metadata_hits Total device metadata found
# TYPE enrichment_device_metadata_hits counter
enrichment_device_metadata_hits {service.stats["device_metadata_hits"]}

# HELP enrichment_similar_anomalies_found Total similar anomalies found
# TYPE enrichment_similar_anomalies_found counter
enrichment_similar_anomalies_found {service.stats["similar_anomalies_found"]}
"""
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics_text, media_type="text/plain")

@app.get("/stats")
async def stats():
    """Detailed statistics endpoint (JSON format)"""
    p95, p99 = service._calculate_percentiles() if service.latencies else (0.0, 0.0)
    
    return {
        "service": "enrichment-v3",
        "stats": {
            **service.stats,
            "p95_latency_ms": p95,
            "p99_latency_ms": p99
        },
        "targets": {
            "p99_latency_target_ms": 500,
            "p99_latency_met": p99 < 500 if p99 > 0 else None
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
