# LLM Enricher Service

AI-based incident insights using LLM and RAG for the AIOps NAAS platform.

## Overview

This service enriches incidents with AI-generated insights:
- **Root Cause Analysis**: Using Ollama (phi3:mini model)
- **Similar Incidents**: Using Qdrant vector database RAG search
- **Remediation Suggestions**: AI-generated remediation steps
- **Response Caching**: ClickHouse-based caching to reduce latency
- **Timeout Fallback**: Rule-based fallback when LLM is unavailable

## Architecture

```
incidents.created (NATS)
    ↓
LLM Enricher Service
    ├── Check Cache (ClickHouse)
    ├── Generate Root Cause (Ollama)
    ├── Search Similar Incidents (Qdrant)
    ├── Generate Remediation (Ollama)
    └── Store in Cache
    ↓
incidents.enriched (NATS)
```

## Components

### `llm_service.py`
Main service that orchestrates the enrichment process:
- Subscribes to `incidents.created` from NATS
- Coordinates LLM calls, RAG searches, and caching
- Publishes to `incidents.enriched`
- FastAPI endpoints for health checks and stats

### `ollama_client.py`
Ollama LLM integration:
- Connects to Ollama API at `http://ollama:11434`
- Uses `phi3:mini` model by default
- Generates root cause analysis and remediation suggestions
- 10-second timeout with graceful fallback

### `qdrant_rag.py`
Qdrant vector database for RAG:
- Manages incident embeddings in Qdrant
- Similarity search for related incidents
- Stores new incidents for future searches
- Simple deterministic embeddings (placeholder for production models)

### `llm_cache.py`
ClickHouse-based response cache:
- Caches LLM responses to avoid redundant calls
- 24-hour TTL by default
- Cache key based on incident type, severity, and service
- Provides cache statistics and hit rate metrics

## Configuration

Environment variables:

```bash
# NATS
NATS_URL=nats://nats:4222

# Ollama LLM
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=phi3:mini
OLLAMA_TIMEOUT=10

# Qdrant Vector DB
QDRANT_URL=http://qdrant:6333
QDRANT_TIMEOUT=5

# ClickHouse Cache
CLICKHOUSE_HOST=clickhouse
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=clickhouse123
```

## API Endpoints

### Health Check
```bash
GET http://localhost:9090/health
```

Returns service health status and component availability.

### Statistics
```bash
GET http://localhost:9090/stats
```

Returns processing statistics and cache metrics.

### Manual Enrichment (Testing)
```bash
POST http://localhost:9090/enrich
Content-Type: application/json

{
  "incident_id": "inc-001",
  "incident_type": "link_degradation",
  "severity": "high",
  "service": "satellite_comms",
  "ship_id": "ship-001"
}
```

## Performance Targets

- **Target Latency**: <300ms with cache hit
- **LLM Timeout**: 10 seconds maximum
- **Cache TTL**: 24 hours
- **Fallback**: Immediate rule-based response on timeout/error

## NATS Topics

**Subscribes to:**
- `incidents.created` - New incidents from correlation service

**Publishes to:**
- `incidents.enriched` - Enriched incidents with AI insights

## Output Format

```json
{
  "incident_id": "inc-001",
  "enrichment_timestamp": "2025-01-01T12:00:00.000Z",
  "original_incident": { ... },
  "ai_insights": {
    "root_cause": "High latency detected due to satellite link congestion...",
    "remediation_suggestions": "1. Reduce traffic priority...\n2. Monitor link quality...\n3. Consider backup link..."
  },
  "similar_incidents": [
    {
      "incident_id": "inc-045",
      "incident_type": "link_degradation",
      "severity": "high",
      "similarity_score": 0.87,
      "resolution": "Switched to backup link"
    }
  ],
  "cache_hit": false,
  "processing_time_ms": 245.32
}
```

## Testing

Run unit tests:
```bash
cd services/llm-enricher
pip install -r requirements.txt
python3 test_service.py
```

## Deployment

Build and run with Docker Compose:

```bash
# Build the service
docker compose build llm-enricher

# Start the service
docker compose up -d llm-enricher

# View logs
docker compose logs -f llm-enricher

# Check health
curl http://localhost:9090/health
```

## Dependencies

- FastAPI for REST API
- NATS for messaging
- Ollama for LLM inference
- Qdrant for vector similarity search
- ClickHouse for response caching

## Fallback Behavior

When LLM or RAG services are unavailable:

1. **LLM Timeout**: Returns rule-based analysis instead
2. **Qdrant Unavailable**: Returns empty similar incidents list
3. **Cache Unavailable**: Continues without caching (higher latency)

All fallbacks are logged and tracked in health metrics.

## Future Enhancements

- [ ] Use proper embedding models (sentence-transformers)
- [ ] Fine-tuned maritime domain LLM
- [ ] Multi-model ensemble for higher accuracy
- [ ] Feedback loop for model improvement
- [ ] Advanced prompt engineering
- [ ] Cost/token tracking and optimization
