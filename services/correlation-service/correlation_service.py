#!/usr/bin/env python3
"""
AIOps NAAS V3 - Correlation Service (Fast Path L2)
Correlates enriched anomalies into incidents (<1s target)
Input: anomaly.detected.enriched → Output: incidents.created
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
from fastapi import FastAPI
from pydantic import ValidationError
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops_core.models import AnomalyEnriched, IncidentCreated
from aiops_core.utils import StructuredLogger, tracked_operation, extract_error_message, compute_suppress_key, compute_correlation_keys

from nats.aio.client import Client as NATS

logger = StructuredLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_INPUT = "anomaly.detected.enriched"
NATS_OUTPUT = "incidents.created"
PORT = int(os.getenv("CORRELATION_PORT", "8082"))

# Time windows from policy (correlate.yaml)
TIME_WINDOWS = {"network": 300, "system": 600, "application": 1200, "satellite": 300, "default": 900}
DEDUP_TTL = 900  # 15 min
SUPPRESS_TTL = 1800  # 30 min

app = FastAPI(title="Correlation Service V3")

class CorrelationService:
    def __init__(self):
        self.nats = None
        self.running = False
        self.windows = defaultdict(list)  # ship_id+domain -> [anomalies]
        self.dedup_cache = {}  # suppress_key -> timestamp
        self.stats = {"processed": 0, "incidents_created": 0, "duplicates": 0, "suppressions": 0, "errors": 0}
        
    async def connect(self):
        self.nats = NATS()
        await self.nats.connect(NATS_URL)
        logger.info("Connected", extra={"nats": NATS_URL})
        
    def _cleanup_windows(self):
        """Remove expired anomalies from windows"""
        now = time.time()
        for key, anomalies in list(self.windows.items()):
            domain = key.split("+")[1] if "+" in key else "default"
            window_sec = TIME_WINDOWS.get(domain, TIME_WINDOWS["default"])
            self.windows[key] = [a for a in anomalies if (now - a["ts_unix"]) < window_sec]
            if not self.windows[key]:
                del self.windows[key]
                
        # Cleanup dedup cache
        self.dedup_cache = {k: v for k, v in self.dedup_cache.items() if (now - v) < SUPPRESS_TTL}
        
    def _should_suppress(self, suppress_key: str) -> bool:
        """Check if incident should be suppressed (deduplication)"""
        now = time.time()
        if suppress_key in self.dedup_cache:
            last_seen = self.dedup_cache[suppress_key]
            if (now - last_seen) < DEDUP_TTL:
                self.stats["duplicates"] += 1
                return True
        self.dedup_cache[suppress_key] = now
        return False
        
    async def correlate(self, enriched: AnomalyEnriched) -> bool:
        """Correlate enriched anomaly, return True if incident created"""
        try:
            # Compute suppress key
            suppress_key = compute_suppress_key(enriched.ship_id, enriched.domain, enriched.msg[:50])
            
            if self._should_suppress(suppress_key):
                logger.info("Suppressed duplicate", extra={"tracking_id": enriched.tracking_id, "suppress_key": suppress_key})
                self.stats["suppressions"] += 1
                return False
                
            # Add to window
            window_key = f"{enriched.ship_id}+{enriched.domain}"
            ts_unix = enriched.ts.timestamp() if hasattr(enriched.ts, 'timestamp') else time.time()
            
            self.windows[window_key].append({
                "tracking_id": enriched.tracking_id,
                "ts": enriched.ts,
                "ts_unix": ts_unix,
                "severity": enriched.severity,
                "detector": enriched.detector,
                "score": enriched.score,
                "msg": enriched.msg,
                "error_msg": enriched.error_msg,
                "meta": enriched.meta
            })
            
            # Check if should create incident (threshold: 3 anomalies)
            if len(self.windows[window_key]) >= 3:
                incident = await self._create_incident(enriched.ship_id, enriched.domain, self.windows[window_key])
                self.windows[window_key].clear()  # Reset window
                await self.nats.publish(NATS_OUTPUT, incident.model_dump_json().encode())
                self.stats["incidents_created"] += 1
                logger.info("Incident created", extra={"incident_id": incident.incident_id, "evidence_count": len(incident.evidence)})
                return True
                
            return False
            
        except Exception as e:
            err = extract_error_message(e)
            logger.error(f"Correlation failed: {err}", extra={"tracking_id": enriched.tracking_id})
            return False
            
    async def _create_incident(self, ship_id: str, domain: str, anomalies: List[Dict]) -> IncidentCreated:
        """Create incident from window of anomalies"""
        incident_id = f"INC-{ship_id}-{domain}-{int(time.time())}"
        
        # Determine severity (max from anomalies)
        severities = [a["severity"] for a in anomalies]
        severity = max(severities, key=lambda s: ["low", "medium", "high", "critical"].index(s))
        
        # Aggregate tracking IDs
        tracking_ids = [a["tracking_id"] for a in anomalies]
        
        # Consolidate error messages
        error_msgs = [a["error_msg"] for a in anomalies if a.get("error_msg")]
        
        # Build evidence
        evidence = [
            {
                "tracking_id": a["tracking_id"],
                "ts": a["ts"].isoformat() if hasattr(a["ts"], 'isoformat') else str(a["ts"]),
                "detector": a["detector"],
                "score": a["score"],
                "msg": a["msg"]
            }
            for a in anomalies
        ]
        
        incident = IncidentCreated(
            tracking_id=tracking_ids[0],  # Use first as primary
            ts=datetime.now(),
            incident_id=incident_id,
            incident_type=domain,
            ship_id=ship_id,
            severity=severity,
            status="open",
            summary=f"{len(anomalies)} anomalies detected in {domain}",
            error_msg="; ".join(error_msgs) if error_msgs else None,
            evidence=evidence,
            meta={
                "tracking_ids": tracking_ids,
                "anomaly_count": len(anomalies),
                "detectors": list(set(a["detector"] for a in anomalies)),
                "time_window_sec": TIME_WINDOWS.get(domain, TIME_WINDOWS["default"])
            }
        )
        
        return incident
        
    async def process_message(self, msg):
        self.stats["processed"] += 1
        try:
            data = json.loads(msg.data.decode())
            enriched = AnomalyEnriched(**data)
            with tracked_operation("correlate", logger, tracking_id=enriched.tracking_id):
                await self.correlate(enriched)
        except ValidationError as e:
            self.stats["errors"] += 1
            logger.error(f"Validation error: {e}")
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"Processing error: {extract_error_message(e)}")
            
    async def start(self):
        await self.connect()
        await self.nats.subscribe(NATS_INPUT, cb=self.process_message)
        logger.info("Started", extra={"input": NATS_INPUT, "output": NATS_OUTPUT})
        self.running = True
        
        # Periodic cleanup task
        async def cleanup_loop():
            while self.running:
                await asyncio.sleep(60)
                self._cleanup_windows()
                
        asyncio.create_task(cleanup_loop())
        
        while self.running:
            await asyncio.sleep(1)
            
    async def stop(self):
        self.running = False
        if self.nats:
            await self.nats.close()
        logger.info("Stopped")

service = CorrelationService()

@app.on_event("startup")
async def startup():
    asyncio.create_task(service.start())

@app.on_event("shutdown")
async def shutdown():
    await service.stop()

@app.get("/health")
async def health():
    return {
        "status": "healthy" if service.running else "unhealthy",
        "service": "correlation-v3",
        "version": "3.0",
        "stats": service.stats,
        "windows": {k: len(v) for k, v in service.windows.items()},
        "nats": {"connected": service.nats and service.nats.is_connected, "input": NATS_INPUT, "output": NATS_OUTPUT}
    }

@app.get("/stats")
async def stats():
    return {"service": "correlation-v3", "stats": service.stats}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
