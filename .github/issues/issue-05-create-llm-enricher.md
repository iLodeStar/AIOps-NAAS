## Objective
Create llm-enricher service for Insight Path AI enrichment using Ollama LLM and Qdrant RAG.

## Service Purpose
Subscribe to `incidents.created`, generate AI insights, retrieve similar incidents, publish enhanced incidents.

## Core Functionality
- Root cause analysis (Ollama phi3:mini)
- Similar incidents (Qdrant RAG)
- Remediation suggestions
- Impact prediction
- LLM response caching in ClickHouse
- Target latency: <300ms (with timeout fallback)

## Acceptance Criteria
- [ ] Service subscribes to `incidents.created` NATS topic
- [ ] Ollama integration functional with phi3:mini model
- [ ] Qdrant RAG retrieves similar incidents
- [ ] LLM responses cached in ClickHouse
- [ ] Publishes `EnrichedIncident` to `incidents.enriched`
- [ ] Timeout fallback (graceful degradation)
- [ ] Latency <300ms target (99th percentile)
- [ ] Health endpoint and metrics
- [ ] Unit tests with mocked LLM/RAG

## Dependencies
- Issue #6 (Ollama service)
- Issue #7 (Qdrant service)
- Issues #1-4 (Fast Path operational)

**Estimated Effort**: 4-5 hours  
**Sprint**: 2 (Week 2)  
**Priority**: High
