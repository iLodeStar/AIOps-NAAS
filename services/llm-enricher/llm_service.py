#!/usr/bin/env python3
"""
AIOps NAAS v0.3 - LLM Enricher Service

This service provides AI-based incident insights using LLM and RAG:
- Subscribes to incidents.created from NATS
- Generates root cause analysis using Ollama (phi3:mini)
- Retrieves similar incidents using Qdrant RAG
- Generates remediation suggestions
- Caches responses in ClickHouse
- Publishes enriched incidents to incidents.enriched
- Implements timeout fallback for reliability
- Target latency: <300ms with caching
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from nats.aio.client import Client as NATS

# Import local modules
from ollama_client import OllamaClient
from qdrant_rag import QdrantRAGClient
from llm_cache import LLMCache

# Try to import V3 StructuredLogger
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
    from aiops_core.utils import StructuredLogger, generate_tracking_id
    logger = StructuredLogger(__name__)
    V3_AVAILABLE = True
except ImportError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    V3_AVAILABLE = False


class LLMEnricherService:
    """Main LLM enricher service"""
    
    def __init__(self):
        self.app = FastAPI(title="LLM Enricher Service")
        
        # NATS client
        self.nats_client = None
        
        # Initialize components
        ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'phi3:mini')
        ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '10'))
        
        qdrant_url = os.getenv('QDRANT_URL', 'http://qdrant:6333')
        qdrant_timeout = int(os.getenv('QDRANT_TIMEOUT', '5'))
        
        clickhouse_host = os.getenv('CLICKHOUSE_HOST', 'clickhouse')
        clickhouse_user = os.getenv('CLICKHOUSE_USER', 'default')
        clickhouse_password = os.getenv('CLICKHOUSE_PASSWORD', 'clickhouse123')
        
        self.ollama_client = OllamaClient(
            ollama_url=ollama_url,
            model=ollama_model,
            timeout=ollama_timeout
        )
        
        self.qdrant_client = QdrantRAGClient(
            qdrant_url=qdrant_url,
            timeout=qdrant_timeout
        )
        
        self.cache = LLMCache(
            clickhouse_host=clickhouse_host,
            clickhouse_user=clickhouse_user,
            clickhouse_password=clickhouse_password
        )
        
        # Health and stats
        self.health_status = {
            "nats_connected": False,
            "ollama_available": False,
            "qdrant_available": False,
            "clickhouse_available": False,
            "incidents_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "llm_calls": 0,
            "timeouts": 0,
            "errors": 0
        }
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy" if self.health_status["nats_connected"] else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                **self.health_status
            }
        
        @self.app.get("/stats")
        async def get_stats():
            """Get service statistics"""
            cache_stats = self.cache.get_cache_stats()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "service_stats": self.health_status,
                "cache_stats": cache_stats
            }
        
        @self.app.post("/enrich")
        async def manual_enrich(incident_data: Dict[str, Any]):
            """Manual enrichment endpoint for testing"""
            enriched = await self.enrich_incident(incident_data)
            return enriched
    
    async def connect_nats(self):
        """Connect to NATS and subscribe to incident events"""
        try:
            nats_url = os.getenv('NATS_URL', 'nats://nats:4222')
            logger.info(f"Connecting to NATS at {nats_url}")
            
            self.nats_client = NATS()
            await self.nats_client.connect(nats_url)
            
            # Subscribe to incidents.created
            async def incident_handler(msg):
                await self._handle_incident_event(msg)
            
            await self.nats_client.subscribe("incidents.created", cb=incident_handler)
            logger.info("Connected to NATS and subscribed to incidents.created")
            self.health_status["nats_connected"] = True
            
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            self.health_status["nats_connected"] = False
    
    async def _handle_incident_event(self, msg):
        """Handle incoming incident event from NATS"""
        try:
            incident_data = json.loads(msg.data.decode())
            incident_id = incident_data.get('incident_id', 'unknown')
            tracking_id = incident_data.get('tracking_id', 'unknown')
            
            # Set tracking_id in logger context for V3
            if V3_AVAILABLE and hasattr(logger, 'set_tracking_id'):
                logger.set_tracking_id(tracking_id)
            
            logger.info("processing_incident", incident_id=incident_id, tracking_id=tracking_id)
            self.health_status["incidents_processed"] += 1
            
            # Enrich the incident
            enriched_data = await self.enrich_incident(incident_data)
            
            # Publish enriched incident
            if enriched_data:
                await self._publish_enriched_incident(enriched_data)
            
        except Exception as e:
            logger.error("error_handling_incident", error=e)
            self.health_status["errors"] += 1
    
    async def enrich_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich incident with AI insights
        
        Steps:
        1. Check cache for existing responses
        2. Query Qdrant for similar incidents
        3. Generate root cause analysis via Ollama
        4. Generate remediation suggestions via Ollama
        5. Cache responses
        6. Return enriched data
        """
        start_time = datetime.utcnow()
        incident_id = incident_data.get('incident_id', 'unknown')
        
        enriched = {
            "incident_id": incident_id,
            "enrichment_timestamp": start_time.isoformat(),
            "original_incident": incident_data,
            "ai_insights": {},
            "similar_incidents": [],
            "cache_hit": False,
            "processing_time_ms": 0
        }
        
        try:
            # 1. Check cache for root cause
            cached_root_cause = self.cache.get_cached_response(
                incident_data,
                "root_cause"
            )
            
            if cached_root_cause:
                root_cause = cached_root_cause['response_text']
                enriched["cache_hit"] = True
                self.health_status["cache_hits"] += 1
                logger.info(f"Using cached root cause for {incident_id}")
            else:
                # 2. Generate root cause via LLM
                self.health_status["cache_misses"] += 1
                self.health_status["llm_calls"] += 1
                
                root_cause = self.ollama_client.generate_root_cause_analysis(incident_data)
                
                if root_cause:
                    # Cache the response
                    self.cache.store_response(
                        incident_data,
                        "root_cause",
                        root_cause,
                        metadata={"model": self.ollama_client.model}
                    )
                else:
                    # Fallback if LLM fails
                    root_cause = self._fallback_root_cause(incident_data)
                    self.health_status["timeouts"] += 1
            
            enriched["ai_insights"]["root_cause"] = root_cause
            
            # 3. Search for similar incidents (RAG)
            similar_incidents = self.qdrant_client.search_similar_incidents(
                incident_data,
                limit=3
            )
            enriched["similar_incidents"] = similar_incidents
            
            # 4. Check cache for remediation
            cached_remediation = self.cache.get_cached_response(
                incident_data,
                "remediation"
            )
            
            if cached_remediation:
                remediation = cached_remediation['response_text']
                logger.info(f"Using cached remediation for {incident_id}")
            else:
                # Generate remediation suggestions
                self.health_status["llm_calls"] += 1
                
                remediation = self.ollama_client.generate_remediation_suggestions(
                    incident_data,
                    root_cause
                )
                
                if remediation:
                    # Cache the response
                    self.cache.store_response(
                        incident_data,
                        "remediation",
                        remediation,
                        metadata={"model": self.ollama_client.model}
                    )
                else:
                    # Fallback if LLM fails
                    remediation = self._fallback_remediation(incident_data)
                    self.health_status["timeouts"] += 1
            
            enriched["ai_insights"]["remediation_suggestions"] = remediation
            
            # 5. Store incident in Qdrant for future similarity searches
            self.qdrant_client.store_incident_vector(incident_id, incident_data)
            
            # Calculate processing time
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            enriched["processing_time_ms"] = round(duration_ms, 2)
            
            logger.info(f"Enriched incident {incident_id} in {duration_ms:.2f}ms")
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching incident {incident_id}: {e}")
            self.health_status["errors"] += 1
            
            # Return basic enrichment with error info
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            enriched["processing_time_ms"] = round(duration_ms, 2)
            enriched["error"] = str(e)
            enriched["ai_insights"]["root_cause"] = self._fallback_root_cause(incident_data)
            enriched["ai_insights"]["remediation_suggestions"] = self._fallback_remediation(incident_data)
            
            return enriched
    
    async def _publish_enriched_incident(self, enriched_data: Dict[str, Any]):
        """Publish enriched incident to NATS"""
        try:
            if not self.nats_client or self.nats_client.is_closed:
                logger.warning("NATS not connected, cannot publish enriched incident")
                return
            
            event_json = json.dumps(enriched_data)
            await self.nats_client.publish("incidents.enriched", event_json.encode())
            
            incident_id = enriched_data.get('incident_id', 'unknown')
            logger.info(f"Published enriched incident: {incident_id}")
            
        except Exception as e:
            logger.error(f"Error publishing enriched incident: {e}")
    
    def _fallback_root_cause(self, incident_data: Dict[str, Any]) -> str:
        """Fallback root cause when LLM is unavailable"""
        incident_type = incident_data.get('incident_type', 'unknown')
        severity = incident_data.get('severity', 'unknown')
        service = incident_data.get('service', 'unknown')
        
        return (
            f"Rule-based analysis: {severity.upper()} severity {incident_type} "
            f"detected in {service}. Automatic root cause analysis unavailable. "
            f"Manual investigation recommended."
        )
    
    def _fallback_remediation(self, incident_data: Dict[str, Any]) -> str:
        """Fallback remediation when LLM is unavailable"""
        incident_type = incident_data.get('incident_type', 'unknown')
        severity = incident_data.get('severity', 'unknown')
        
        if severity in ['critical', 'high']:
            return (
                "1. Alert on-call engineer immediately\n"
                "2. Review system logs and metrics\n"
                "3. Consider failover to backup systems if available"
            )
        else:
            return (
                "1. Monitor the situation for escalation\n"
                "2. Review recent system changes\n"
                "3. Schedule maintenance window if needed"
            )
    
    async def health_check_loop(self):
        """Periodic health check of dependencies"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                self.health_status["ollama_available"] = self.ollama_client.health_check()
                self.health_status["qdrant_available"] = self.qdrant_client.health_check()
                self.health_status["clickhouse_available"] = self.cache.health_check()
                
                logger.debug(f"Health check - Ollama: {self.health_status['ollama_available']}, "
                           f"Qdrant: {self.health_status['qdrant_available']}, "
                           f"ClickHouse: {self.health_status['clickhouse_available']}")
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
    
    async def startup(self):
        """Service startup tasks"""
        logger.info("Starting LLM Enricher Service")
        
        # Check initial health of dependencies
        self.health_status["ollama_available"] = self.ollama_client.health_check()
        self.health_status["qdrant_available"] = self.qdrant_client.health_check()
        self.health_status["clickhouse_available"] = self.cache.health_check()
        
        # Ensure Qdrant collection exists
        if self.health_status["qdrant_available"]:
            self.qdrant_client.ensure_collection_exists()
        
        # Connect to NATS
        await self.connect_nats()
        
        # Start health check loop
        asyncio.create_task(self.health_check_loop())
        
        logger.info("LLM Enricher Service started successfully")
    
    async def shutdown(self):
        """Service shutdown tasks"""
        logger.info("Shutting down LLM Enricher Service")
        
        if self.nats_client and not self.nats_client.is_closed:
            await self.nats_client.close()
        
        logger.info("LLM Enricher Service shut down")


# Create service instance
service = LLMEnricherService()


@service.app.on_event("startup")
async def startup_event():
    """FastAPI startup event"""
    await service.startup()


@service.app.on_event("shutdown")
async def shutdown_event():
    """FastAPI shutdown event"""
    await service.shutdown()


if __name__ == "__main__":
    # Run the service
    uvicorn.run(
        service.app,
        host="0.0.0.0",
        port=9090,
        log_level="info"
    )
