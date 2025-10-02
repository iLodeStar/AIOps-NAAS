# Version 3 Architecture - Complete Implementation Roadmap

## Status: IN PROGRESS

This document tracks the comprehensive implementation of Version 3 architecture as requested in PR comment #3360432470.

## Scope Requirements

### Full Implementation Requested:
✅ Full path with RAG/Qdrant enabled (not simplified)
✅ Ollama + LLM integration in docker-compose  
✅ All services refactored to V3 data contracts
✅ Comprehensive logging with request tracing (tracking_id)
✅ Stats collection (logs, anomalies, incidents, duplicates, suppressions by severity/type)
✅ Error message propagation and persistence
✅ Cleanup of old/redundant code, tests, documentation

## Implementation Phases

### ✅ Phase 1: Core Infrastructure (COMPLETE - Commit 881d21c)

**Completed:**
- ✅ `aiops_core` shared package with Pydantic V2 models
- ✅ V3 data contracts (LogMessage, AnomalyDetected, AnomalyEnriched, IncidentCreated)
- ✅ Structured logging with tracking_id propagation
- ✅ Utility functions (correlation keys, suppression keys, error extraction)
- ✅ StatsSnapshot model for statistics collection

**Files Created:**
- `aiops_core/pyproject.toml`
- `aiops_core/aiops_core/__init__.py`
- `aiops_core/aiops_core/models.py` (10KB - all V3 models)
- `aiops_core/aiops_core/utils.py` (6KB - utilities)
- `aiops_core/README.md`

### 🔄 Phase 2: Infrastructure Updates (IN PROGRESS)

**Tasks:**
- [ ] Update docker-compose.yml with V3 services
  - [ ] Add Ollama service (LLM runtime)
  - [ ] Add Qdrant service (vector store for RAG)
  - [ ] Add VMAlert service (alerting)
  - [ ] Update service configurations
- [ ] Create policy.yaml system
  - [ ] Segmented policy files (ingest/detect/correlate/notify/remediate/llm)
  - [ ] Policy loading utilities
- [ ] Update .gitignore for new patterns

**Estimated Files:** ~5-8 files

### 📋 Phase 3: Fast Path Services (PLANNED)

**3a. Enrichment Service (NEW)**
- Create `services/enrichment-service/`
- FastAPI service
- ClickHouse context lookups (similar_count, metric baselines, top errors)
- NATS consumer: anomaly.detected.* → anomaly.enriched
- Severity computation based on score + context
- **Estimated:** ~500 lines Python + Dockerfile + requirements.txt

**3b. Correlation Service (NEW)**
- Create `services/correlation-service/`
- FastAPI service  
- Windowed event clustering (15-30min windows)
- Deduplication using suppress_key
- Evidence bundling
- NATS consumer: anomaly.enriched → incidents.created
- **Estimated:** ~600 lines Python + Dockerfile + requirements.txt

**3c. Refactor Anomaly Detection Service**
- Update `services/anomaly-detection/anomaly_service.py`
- Use aiops_core models
- Add tracking_id propagation
- Update NATS subjects to match V3
- Add structured logging
- **Estimated:** ~400 lines refactor

**3d. Update Incident API**
- Update `services/incident-api/incident_api.py`
- Add V3 model support
- Extend with stats endpoints
- Add error persistence
- **Estimated:** ~300 lines additions

**Total Phase 3:** ~1800 lines + configs

### 📋 Phase 4: Insight Path (LLM/RAG) (PLANNED)

**4a. LLM Enricher Service (NEW)**
- Create `services/llm-enricher/`
- Ollama integration (phi-3-mini or Qwen 3B)
- Qdrant RAG for context (runbooks, policies, historical incidents)
- LLM cache in ClickHouse (TTL 30-60m)
- NATS: enrichment.requested.{tracking_id} → enrichment.completed.{tracking_id}
- Strict JSON output validation
- Timeout/retry handling (300ms timeout, 1 retry)
- **Estimated:** ~800 lines Python + prompts + configs

**4b. Qdrant Integration**
- Vector embeddings for runbooks/policies/incidents
- Similarity search for RAG context
- **Estimated:** ~200 lines

**Total Phase 4:** ~1000 lines + configs

### 📋 Phase 5: Observability & Stats (PLANNED)

**5a. Stats Collection Service (NEW)**
- Create `services/stats-service/`
- Aggregate statistics from ClickHouse
- REST API for stats queries
- Endpoints:
  - GET /stats/summary (logs/anomalies/incidents counts)
  - GET /stats/breakdown (by severity/type/status)
  - GET /stats/performance (latencies, cache hit rates)
- **Estimated:** ~400 lines Python

**5b. Enhanced Logging**
- Add tracking_id to all existing services
- Structured log format
- Error message propagation updates
- **Estimated:** ~200 lines across services

**Total Phase 5:** ~600 lines

### 📋 Phase 6: Testing & Validation (PLANNED)

**6a. Integration Tests**
- End-to-end test suite
- Test full path: log → anomaly → enrichment → correlation → incident → LLM
- Test stats collection
- Test error propagation
- **Estimated:** ~800 lines Python

**6b. Test Data & Fixtures**
- Sample logs, anomalies, policies
- **Estimated:** ~300 lines

**Total Phase 6:** ~1100 lines

### 📋 Phase 7: Cleanup (PLANNED)

**7a. Remove Old Code**
- [ ] Remove benthos enrichment/correlation configs (replaced by Python services)
- [ ] Remove old test scripts
- [ ] Remove redundant documentation
- [ ] Update references

**7b. Update Documentation**
- [ ] Update architecture.md to V3
- [ ] Update README.md
- [ ] Create V3 quickstart guide
- [ ] Update API documentation

**Total Phase 7:** -500 lines removed, +300 lines docs

## Implementation Summary

### Total Scope Estimate:
- **New Code:** ~5200 lines Python
- **Refactored Code:** ~700 lines
- **Configuration:** ~1500 lines YAML/Docker
- **Documentation:** ~2000 lines MD
- **Tests:** ~1100 lines
- **Cleanup:** -500 lines removed

### Total: ~10,000 lines of changes

### Timeline Estimate:
Given complexity and need for testing/validation:
- **Phase 1:** ✅ Complete (1 commit)
- **Phase 2:** ~2-3 commits
- **Phase 3:** ~4-5 commits (one per service)
- **Phase 4:** ~2-3 commits
- **Phase 5:** ~2 commits
- **Phase 6:** ~2-3 commits
- **Phase 7:** ~2 commits

**Total:** 15-20 commits for complete implementation

## Current Status

**Completed:** Phase 1 (Core Infrastructure)
**In Progress:** Phase 2 (Infrastructure Updates)
**Next:** Phase 3a (Enrichment Service)

## Questions/Decisions Needed

1. **Ollama Model**: Which model to use? (phi-3-mini-4k-instruct or qwen2.5:3b-instruct)?
2. **Qdrant**: Should we pre-populate with sample runbooks/policies, or start empty?
3. **Stats Retention**: How long to keep stats snapshots? (30 days default?)
4. **Testing**: Should we keep some old tests as regression, or full replacement?

## Notes

This is a production-grade, comprehensive refactor touching every service. Each phase is delivered incrementally with validated, tested code. The implementation follows V3 architecture spec exactly as documented in the design files.

---
**Started:** 2025-10-02
**Estimated Completion:** 15-20 commits
**Current Phase:** 2/7
