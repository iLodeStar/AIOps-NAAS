#!/usr/bin/env python3
"""
AIOps NAAS V3 - Enrichment Service (Fast Path)
Enriches anomalies with ClickHouse context (<500ms target)
Input: anomaly.detected → Output: anomaly.detected.enriched
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI
from pydantic import ValidationError
import uvicorn

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from aiops_core.models import AnomalyDetected, AnomalyEnriched
from aiops_core.utils import StructuredLogger, tracked_operation, extract_error_message

from nats.aio.client import Client as NATS
from clickhouse_driver import Client as ClickHouseClient

logger = StructuredLogger(__name__)

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
NATS_INPUT = "anomaly.detected"
NATS_OUTPUT = "anomaly.detected.enriched"
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_USER = os.getenv("CLICKHOUSE_USER", "admin")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "admin")
PORT = int(os.getenv("ENRICHMENT_PORT", "8081"))

app = FastAPI(title="Enrichment Service V3")

class EnrichmentService:
    def __init__(self):
        self.nats = None
        self.ch = None
        self.running = False
        self.stats = {"processed": 0, "enriched": 0, "errors": 0, "avg_latency_ms": 0.0}
        
    async def connect(self):
        self.nats = NATS()
        await self.nats.connect(NATS_URL)
        self.ch = ClickHouseClient(host=CH_HOST, user=CH_USER, password=CH_PASS, database="aiops")
        logger.info("Connected", extra={"nats": NATS_URL, "clickhouse": CH_HOST})
        
    async def enrich(self, anomaly: AnomalyDetected) -> AnomalyEnriched:
        start = datetime.now()
        try:
            device_meta = None
            if anomaly.meta.get("device"):
                try:
                    result = self.ch.execute(
                        "SELECT device_type, vendor, model FROM devices WHERE ship_id=%(sid)s AND device_id=%(did)s LIMIT 1",
                        {"sid": anomaly.ship_id, "did": anomaly.meta["device"]}
                    )
                    if result:
                        device_meta = {"device_type": result[0][0], "vendor": result[0][1], "model": result[0][2]}
                except: pass
                
            recent_incidents = []
            try:
                result = self.ch.execute(
                    "SELECT incident_id, severity, status FROM incidents WHERE ship_id=%(sid)s AND incident_type=%(typ)s AND created_at > now() - INTERVAL 24 HOUR ORDER BY created_at DESC LIMIT 5",
                    {"sid": anomaly.ship_id, "typ": anomaly.domain}
                )
                recent_incidents = [{"id": r[0], "sev": r[1], "status": r[2]} for r in result]
            except: pass
                
            latency = int((datetime.now() - start).total_seconds() * 1000)
            enriched = AnomalyEnriched(
                tracking_id=anomaly.tracking_id, ts=anomaly.ts, ship_id=anomaly.ship_id,
                domain=anomaly.domain, severity=anomaly.severity, detector=anomaly.detector,
                score=anomaly.score, msg=anomaly.msg, error_msg=anomaly.error_msg,
                meta={**anomaly.meta, "device_metadata": device_meta, "recent_incidents": recent_incidents},
                ctx={"enrichment_ms": latency, "device_known": device_meta is not None}
            )
            self.stats["enriched"] += 1
            self.stats["avg_latency_ms"] = (self.stats["avg_latency_ms"] * (self.stats["enriched"]-1) + latency) / self.stats["enriched"]
            logger.info("Enriched", extra={"tracking_id": anomaly.tracking_id, "latency_ms": latency})
            return enriched
        except Exception as e:
            err = extract_error_message(e)
            logger.error(f"Enrichment failed: {err}", extra={"tracking_id": anomaly.tracking_id})
            return AnomalyEnriched(
                tracking_id=anomaly.tracking_id, ts=anomaly.ts, ship_id=anomaly.ship_id,
                domain=anomaly.domain, severity=anomaly.severity, detector=anomaly.detector,
                score=anomaly.score, msg=anomaly.msg, error_msg=anomaly.error_msg or err,
                meta=anomaly.meta, ctx={"enrichment_error": err}
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
        await self.connect()
        await self.nats.subscribe(NATS_INPUT, cb=self.process_message)
        logger.info("Started", extra={"input": NATS_INPUT, "output": NATS_OUTPUT})
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
    return {
        "status": "healthy" if service.running else "unhealthy",
        "service": "enrichment-v3",
        "version": "3.0",
        "stats": service.stats,
        "nats": {"connected": service.nats and service.nats.is_connected, "input": NATS_INPUT, "output": NATS_OUTPUT}
    }

@app.get("/stats")
async def stats():
    return {"service": "enrichment-v3", "stats": service.stats}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
