#!/usr/bin/env python3
"""
AIOps NAAS V3 - Correlation Service
Correlates enriched anomalies into incidents with deduplication and time-windowing
Input: anomaly.enriched → Output: incidents.created
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops_core.models import (
    AnomalyEnriched, 
    IncidentCreated, 
    Domain, 
    Severity,
    IncidentStatus,
    ScopeEntry,
    TimelineEntry,
    Evidence
)
from aiops_core.utils import (
    StructuredLogger, 
    tracked_operation, 
    extract_error_message, 
    compute_suppress_key, 
    compute_correlation_keys,
    generate_tracking_id
)

from nats.aio.client import Client as NATS

# Import our correlation modules
from deduplication import DeduplicationCache
from windowing import TimeWindowManager

logger = StructuredLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_INPUT = os.getenv("NATS_INPUT", "anomaly.enriched")
NATS_OUTPUT = "incidents.created"
PORT = int(os.getenv("CORRELATION_PORT", "8082"))

# Configuration
DEDUP_TTL = int(os.getenv("DEDUP_TTL", "900"))  # 15 min default
CORRELATION_THRESHOLD = int(os.getenv("CORRELATION_THRESHOLD", "3"))  # 3 anomalies to trigger incident
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))  # Circuit breaker threshold
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))  # Requests per minute
RATE_LIMIT_WINDOW = 60  # seconds

class RateLimiter:
    """Simple in-memory rate limiter for HTTP endpoints"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for client"""
        now = time.time()
        client_requests = self.requests[client_id]
        
        # Remove expired requests
        while client_requests and client_requests[0] < now - self.window_seconds:
            client_requests.popleft()
        
        # Check if under limit
        if len(client_requests) >= self.max_requests:
            return False
        
        # Add new request
        client_requests.append(now)
        return True


class CircuitBreaker:
    """Circuit breaker for NATS connection failures"""
    
    def __init__(self, max_failures: int = 5, timeout_seconds: int = 60):
        self.max_failures = max_failures
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.max_failures:
            self.state = "open"
            logger.error(
                "Circuit breaker opened",
                failure_count=self.failure_count,
                max_failures=self.max_failures
            )
    
    def can_attempt(self) -> bool:
        """Check if operation can be attempted"""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            # Check if timeout has passed
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "half_open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        # half_open state - allow one attempt
        return True


class CorrelationService:
    """
    Main correlation service with deduplication and time-windowing
    """
    
    def __init__(self):
        self.nats = None
        self.running = False
        
        # Initialize modules
        self.dedup_cache = DeduplicationCache(ttl_seconds=DEDUP_TTL)
        self.window_manager = TimeWindowManager(correlation_threshold=CORRELATION_THRESHOLD)
        
        # Performance tracking - use deque for automatic bounds
        self.latency_samples = deque(maxlen=1000)  # Automatically maintains max size
        
        # Circuit breaker for NATS connection
        self.circuit_breaker = CircuitBreaker(max_failures=MAX_RECONNECT_ATTEMPTS)
        
        # Statistics
        self.stats = {
            "processed": 0,
            "incidents_created": 0,
            "duplicates_suppressed": 0,
            "errors": 0,
            "last_processing_time_ms": 0.0,
            "avg_latency_ms": 0.0,
            "nats_failures": 0,
            "circuit_breaker_state": "closed"
        }
        
    async def connect(self):
        """Connect to NATS with circuit breaker"""
        if not self.circuit_breaker.can_attempt():
            logger.warning("Circuit breaker is open, skipping NATS connection attempt")
            return False
        
        try:
            self.nats = NATS()
            await self.nats.connect(NATS_URL)
            logger.info("Connected to NATS", nats_url=NATS_URL)
            self.circuit_breaker.record_success()
            return True
        except Exception as e:
            self.circuit_breaker.record_failure()
            self.stats["nats_failures"] += 1
            self.stats["circuit_breaker_state"] = self.circuit_breaker.state
            logger.error(f"Failed to connect to NATS: {e}", error=e)
            return False
        
    def _track_latency(self, latency_ms: float):
        """Track processing latency for metrics"""
        self.latency_samples.append(latency_ms)
        
        # Update average (deque automatically maintains max size)
        if self.latency_samples:
            self.stats["avg_latency_ms"] = sum(self.latency_samples) / len(self.latency_samples)
    
    def _get_p99_latency(self) -> float:
        """Calculate p99 latency from samples"""
        if not self.latency_samples:
            return 0.0
        
        sorted_samples = sorted(self.latency_samples)
        p99_index = int(len(sorted_samples) * 0.99)
        return sorted_samples[p99_index] if p99_index < len(sorted_samples) else sorted_samples[-1]
        
    async def correlate(self, enriched: AnomalyEnriched) -> bool:
        """
        Correlate enriched anomaly and create incident if threshold reached
        
        Args:
            enriched: Enriched anomaly event
            
        Returns:
            True if incident created, False otherwise
        """
        start_time = time.time()
        
        try:
            # Step 1: Add to time window (no dedup check - let anomalies correlate)
            anomalies = self.window_manager.add_anomaly(enriched)
            
            # Step 2: If window threshold reached, check deduplication before creating incident
            if anomalies:
                # Compute suppress key for this potential incident
                suppress_key = self.dedup_cache.compute_suppress_key(enriched)
                
                # Check if we've recently created an incident with this signature
                should_suppress, _ = self.dedup_cache.should_suppress(enriched)
                
                if should_suppress:
                    self.stats["duplicates_suppressed"] += 1
                    logger.info(
                        "Suppressed duplicate incident",
                        tracking_id=enriched.tracking_id,
                        suppress_key=suppress_key,
                        anomaly_count=len(anomalies)
                    )
                    return False
                
                # Not a duplicate - create incident
                incident = await self._create_incident(enriched, anomalies, suppress_key)
                
                # Publish incident to NATS with retry logic
                await self._publish_incident(incident)
                
                self.stats["incidents_created"] += 1
                
                logger.info(
                    "Incident created",
                    incident_id=incident.incident_id,
                    evidence_count=len(incident.evidence),
                    severity=incident.severity.value,
                    tracking_id=enriched.tracking_id
                )
                
                return True
            
            return False
            
        except Exception as e:
            err = extract_error_message(e)
            logger.error(
                f"Correlation failed: {err}",
                tracking_id=enriched.tracking_id,
                error=e
            )
            self.stats["errors"] += 1
            return False
            
        finally:
            # Track latency
            latency_ms = (time.time() - start_time) * 1000
            self._track_latency(latency_ms)
            self.stats["last_processing_time_ms"] = latency_ms
    
    async def _publish_incident(self, incident: IncidentCreated, max_retries: int = 3):
        """
        Publish incident to NATS with exponential backoff retry
        
        Args:
            incident: Incident to publish
            max_retries: Maximum number of retry attempts (default: 3)
            
        Raises:
            Exception: If all retries exhausted
        """
        for attempt in range(max_retries):
            try:
                await self.nats.publish(
                    NATS_OUTPUT, 
                    incident.model_dump_json().encode()
                )
                
                if attempt > 0:
                    logger.info(
                        "Incident published after retry",
                        incident_id=incident.incident_id,
                        attempt=attempt + 1
                    )
                
                return  # Success
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff: 0.1s, 0.2s, 0.4s
                    backoff_seconds = 0.1 * (2 ** attempt)
                    logger.warning(
                        f"NATS publish failed, retrying in {backoff_seconds}s",
                        incident_id=incident.incident_id,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    await asyncio.sleep(backoff_seconds)
                else:
                    # All retries exhausted
                    logger.error(
                        "NATS publish failed after all retries",
                        incident_id=incident.incident_id,
                        max_retries=max_retries,
                        error=str(e)
                    )
                    self.stats["errors"] += 1
                    raise
            
    async def _create_incident(
        self, 
        primary_anomaly: AnomalyEnriched,
        anomalies: List[Dict], 
        suppress_key: str
    ) -> IncidentCreated:
        """
        Create incident from correlated anomalies
        
        Args:
            primary_anomaly: The most recent anomaly that triggered the incident
            anomalies: List of correlated anomalies in the time window
            suppress_key: Suppression key for deduplication
            
        Returns:
            IncidentCreated event
        """
        # Generate incident ID
        incident_id = f"INC-{primary_anomaly.ship_id}-{int(time.time())}"
        
        # Determine severity (max from all anomalies)
        severity_order = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
        max_severity = Severity.LOW
        for anomaly in anomalies:
            anomaly_severity = anomaly["severity"]
            # Handle both Severity enum and string values
            if isinstance(anomaly_severity, str):
                try:
                    anomaly_severity = Severity(anomaly_severity.lower())
                except ValueError:
                    continue
            
            if severity_order.index(anomaly_severity) > severity_order.index(max_severity):
                max_severity = anomaly_severity
        
        # Build scope: affected devices/services
        scope = []
        seen_devices = set()
        for anomaly in anomalies:
            device_id = anomaly.get("device_id") or "unknown"
            service = anomaly["service"]
            scope_key = f"{device_id}:{service}"
            
            if scope_key not in seen_devices:
                scope.append(ScopeEntry(
                    device_id=device_id,
                    service=service
                ))
                seen_devices.add(scope_key)
        
        # Compute correlation keys for grouping
        domain_str = primary_anomaly.domain.value if hasattr(primary_anomaly.domain, 'value') else str(primary_anomaly.domain)
        corr_keys = compute_correlation_keys(
            incident_type=primary_anomaly.anomaly_type,
            device_id=primary_anomaly.device_id,
            service=primary_anomaly.service,
            ship_id=primary_anomaly.ship_id,
            domain=domain_str
        )
        
        # Build timeline
        timeline = [
            TimelineEntry(
                ts=datetime.utcnow(),
                event="incident_created",
                description=f"Incident created from {len(anomalies)} correlated anomalies",
                source="correlation-service"
            )
        ]
        
        # Build evidence references
        evidence = []
        for i, anomaly in enumerate(anomalies):
            # Create ClickHouse reference for evidence
            tracking_id = anomaly["tracking_id"]
            evidence_ref = f"clickhouse://logs.anomalies/tracking_id={tracking_id}"
            
            # Build summary from anomaly details
            summary_parts = [
                f"[{anomaly['detector']}]",
                f"score={anomaly['score']:.2f}",
                f"service={anomaly['service']}"
            ]
            
            if anomaly.get("raw_msg"):
                msg_preview = anomaly["raw_msg"][:100]
                summary_parts.append(f"msg={msg_preview}")
            
            evidence.append(Evidence(
                ref=evidence_ref,
                summary=" ".join(summary_parts),
                weight=anomaly["score"]
            ))
        
        # Create incident
        incident = IncidentCreated(
            tracking_id=primary_anomaly.tracking_id,
            ts=datetime.utcnow(),
            ship_id=primary_anomaly.ship_id,
            incident_id=incident_id,
            incident_type=primary_anomaly.anomaly_type,
            severity=max_severity,
            scope=scope,
            corr_keys=corr_keys,
            suppress_key=suppress_key,
            timeline=timeline,
            evidence=evidence,
            status=IncidentStatus.OPEN
        )
        
        return incident
        
    async def process_message(self, msg):
        """Process incoming NATS message"""
        self.stats["processed"] += 1
        
        try:
            data = json.loads(msg.data.decode())
            enriched = AnomalyEnriched(**data)
            
            logger.set_tracking_id(enriched.tracking_id)
            
            with tracked_operation(logger, "correlate", tracking_id=enriched.tracking_id):
                await self.correlate(enriched)
                
        except ValidationError as e:
            self.stats["errors"] += 1
            logger.error(f"Validation error: {e}", error=e)
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Processing error: {extract_error_message(e)}", error=e)
            
    async def start(self):
        """Start correlation service"""
        await self.connect()
        
        # Subscribe to input topic
        await self.nats.subscribe(NATS_INPUT, cb=self.process_message)
        
        logger.info(
            "Correlation service started",
            input_topic=NATS_INPUT,
            output_topic=NATS_OUTPUT,
            dedup_ttl=DEDUP_TTL,
            correlation_threshold=CORRELATION_THRESHOLD
        )
        
        self.running = True
        
        # Start periodic cleanup task
        async def cleanup_loop():
            while self.running:
                await asyncio.sleep(60)  # Run every minute
                
                # Cleanup expired windows and dedup cache
                self.window_manager.cleanup_expired_windows()
                self.dedup_cache.cleanup_expired()
        
        asyncio.create_task(cleanup_loop())
        
        # Keep service running
        while self.running:
            await asyncio.sleep(1)
            
    async def stop(self):
        """Stop correlation service"""
        self.running = False
        
        if self.nats and hasattr(self.nats, '_transport') and self.nats._transport:
            try:
                await self.nats.close()
            except Exception as e:
                logger.warning(f"Error closing NATS connection: {e}")
        
        logger.info("Correlation service stopped")


service = CorrelationService()
rate_limiter = RateLimiter(max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    logger.info("Starting Correlation Service V3")
    asyncio.create_task(service.start())
    yield
    # Shutdown
    logger.info("Shutting down Correlation Service V3")
    await service.stop()


app = FastAPI(title="Correlation Service V3", lifespan=lifespan)


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for HTTP endpoints"""
    # Get client identifier (IP address)
    client_id = request.client.host if request.client else "unknown"
    
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    # Check rate limit
    if not rate_limiter.is_allowed(client_id):
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Maximum {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds",
                "client": client_id
            }
        )
    
    return await call_next(request)


# Add middleware
app.middleware("http")(rate_limit_middleware)


@app.get("/health")
async def health():
    """
    Health check endpoint
    Returns service health status and basic stats
    """
    return {
        "status": "healthy" if service.running and service.circuit_breaker.state == "closed" else "degraded" if service.circuit_breaker.state == "half_open" else "unhealthy",
        "service": "correlation-service-v3",
        "version": "3.0",
        "nats": {
            "connected": service.nats and service.nats.is_connected if service.nats else False,
            "input_topic": NATS_INPUT,
            "output_topic": NATS_OUTPUT,
            "circuit_breaker": service.circuit_breaker.state,
            "failures": service.stats.get("nats_failures", 0)
        },
        "stats": {
            "processed": service.stats["processed"],
            "incidents_created": service.stats["incidents_created"],
            "duplicates_suppressed": service.stats["duplicates_suppressed"],
            "errors": service.stats["errors"]
        },
        "config": {
            "dedup_ttl_seconds": DEDUP_TTL,
            "correlation_threshold": CORRELATION_THRESHOLD,
            "rate_limit": f"{RATE_LIMIT_REQUESTS} req/{RATE_LIMIT_WINDOW}s",
            "max_reconnect_attempts": MAX_RECONNECT_ATTEMPTS
        }
    }


@app.get("/metrics")
async def metrics():
    """
    Metrics endpoint with latency tracking
    Returns detailed performance and operational metrics
    """
    p99_latency = service._get_p99_latency()
    
    return {
        "service": "correlation-service-v3",
        "timestamp": datetime.utcnow().isoformat(),
        
        # Processing metrics
        "processing": {
            "total_processed": service.stats["processed"],
            "incidents_created": service.stats["incidents_created"],
            "duplicates_suppressed": service.stats["duplicates_suppressed"],
            "errors": service.stats["errors"],
            "error_rate": (
                service.stats["errors"] / service.stats["processed"] 
                if service.stats["processed"] > 0 else 0.0
            )
        },
        
        # Latency metrics
        "latency": {
            "last_processing_ms": round(service.stats["last_processing_time_ms"], 2),
            "avg_latency_ms": round(service.stats["avg_latency_ms"], 2),
            "p99_latency_ms": round(p99_latency, 2),
            "samples": len(service.latency_samples)
        },
        
        # Deduplication metrics
        "deduplication": service.dedup_cache.get_stats(),
        
        # Windowing metrics
        "windowing": service.window_manager.get_stats(),
        
        # Active windows info
        "active_windows": service.window_manager.get_window_info()
    }


@app.get("/stats")
async def stats():
    """Legacy stats endpoint for backward compatibility"""
    return {
        "service": "correlation-service-v3",
        "stats": service.stats,
        "dedup_stats": service.dedup_cache.get_stats(),
        "window_stats": service.window_manager.get_stats()
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

