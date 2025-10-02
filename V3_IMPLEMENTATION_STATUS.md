# V3 Architecture Implementation Status

## Lead Engineer Review Summary

**Date**: October 2, 2025  
**Current Progress**: 25% Complete (Phase 2/7)  
**Remaining Work**: 75% (estimated 10-15 additional commits)

---

## ✅ What's Complete (Phase 1-2)

### Phase 1: Core Infrastructure
- ✅ **aiops_core Package** (5 files)
  - Pydantic V2 models (BaseMessage, LogMessage, AnomalyDetected, AnomalyEnriched, IncidentCreated)
  - Structured logging with tracking_id
  - Utilities (tracked_operation, compute_suppress_key, extract_error_message)
  - Schema versioning (v3.0)

### Phase 2: Policy System
- ✅ **Segmented Policies** (10 files)
  - Master policy.yaml
  - 9 segment files (ingest, detect, correlate, llm, notify, remediate, retention, privacy, slo)
  - Full RAG configuration
  - Performance budgets defined

### Bonus: Documentation & Ops Console
- ✅ 67KB documentation (validation, diagrams, index)
- ✅ Grafana App Plugin (13 TypeScript files)
- ✅ Backend API extensions for plugin

---

## ❌ Critical Gaps (Phase 3-7 - 75% Remaining)

### Phase 3: Fast Path Services (0% implemented)

**Required Services:**

#### 1. enrichment-service (NEW)
**Status**: ❌ Not created  
**Purpose**: Enrich anomalies with ClickHouse context  
**Input**: `anomaly.detected`  
**Output**: `anomaly.detected.enriched`  

**Requirements**:
- Fast ClickHouse queries (<500ms)
- Device metadata lookup
- Recent incident history
- Operational status
- Tracking ID propagation
- Error preservation

**Files Needed**:
- `services/enrichment-service/enrichment_service.py`
- `services/enrichment-service/requirements.txt`
- `services/enrichment-service/Dockerfile`

#### 2. correlation-service (NEW)
**Status**: ❌ Not created  
**Purpose**: Correlate enriched anomalies into incidents  
**Input**: `anomaly.detected.enriched`  
**Output**: `incidents.created`  

**Requirements**:
- Time-window clustering (5-20 min)
- Deduplication (15 min TTL)
- Suppression (30 min TTL)
- Severity mapping
- Tracking ID aggregation
- Error consolidation

**Files Needed**:
- `services/correlation-service/correlation_service.py`
- `services/correlation-service/requirements.txt`
- `services/correlation-service/Dockerfile`

#### 3. anomaly-detection REFACTOR
**Status**: ❌ Exists but uses OLD contracts  
**Current**: Old dataclass-based models  
**Required**: Use aiops_core V3 models  

**Changes Needed**:
- Replace dataclass with `AnomalyDetected` model
- Add tracking_id generation
- Use StructuredLogger
- Preserve error messages
- Update to publish to `anomaly.detected`

**File to Update**:
- `services/anomaly-detection/anomaly_service.py` (refactor 400+ lines)

#### 4. incident-api V3 ENDPOINTS
**Status**: ❌ Exists but missing V3 extensions  
**Current**: Basic CRUD endpoints  
**Required**: V3 stats and tracing endpoints  

**New Endpoints Needed**:
- `GET /api/v3/stats` - Categorized counts
- `GET /api/v3/stats/severity` - By severity
- `GET /api/v3/stats/type` - By incident type
- `GET /api/v3/trace/{tracking_id}` - Full trace query
- `POST /api/v3/incidents` - Accept V3 models

**Files to Update**:
- `services/incident-api/incident_api.py` (add 200+ lines)

---

### Phase 4: LLM/RAG Integration (0% implemented)

#### 1. llm-enricher Service (NEW)
**Status**: ❌ Not created  
**Purpose**: Async LLM enrichment (Insight Path)  
**Input**: `enrichment.request` (from incidents)  
**Output**: `enrichment.completed`  

**Requirements**:
- Ollama integration (phi3:mini or qwen2.5:3b)
- Qdrant RAG (5 docs, 0.7 similarity)
- LLM caching (45min TTL in ClickHouse)
- 300ms timeout, 1 retry
- Rate limiting (3 concurrent, queue 100)
- Fallback to rule-based

**Files Needed**:
- `services/llm-enricher/llm_enricher_service.py`
- `services/llm-enricher/rag_client.py`
- `services/llm-enricher/llm_client.py`
- `services/llm-enricher/requirements.txt`
- `services/llm-enricher/Dockerfile`

#### 2. Ollama + Qdrant in docker-compose
**Status**: ❌ Not in docker-compose  

**Required**:
- Ollama service with phi3:mini model
- Qdrant service for vector store
- Volume mounts for model persistence
- Health checks
- Dependencies configured

---

### Phase 5: Infrastructure Updates (0% implemented)

#### 1. docker-compose.yml UPDATES
**Status**: ❌ Missing V3 services  

**Required Additions**:
- enrichment-service
- correlation-service
- llm-enricher service
- ollama service
- qdrant service
- vmalert service
- Update dependencies

#### 2. VMAlert Configuration
**Status**: ❌ Not configured  

**Required**:
- Alert rules for Fast Path SLO
- Alert rules for Insight Path SLO
- Queue health monitoring
- Service health checks

**Files Needed**:
- `vmalert/alerts.yml`
- `vmalert/Dockerfile`
- Docker compose integration

---

### Phase 6: Observability & Stats (0% implemented)

#### 1. End-to-End Tracing
**Status**: ⚠️ Models support it, but NO services use it  

**Required**:
- Generate tracking_id at ingestion (Vector config)
- Use StructuredLogger in ALL services
- Store tracking_ids in ClickHouse
- Query endpoint for full trace

**Services to Update**:
- Vector config (add tracking_id generation)
- All Python services (use StructuredLogger)
- incident-api (add trace query endpoint)

#### 2. Stats Collection API
**Status**: ❌ Not implemented  

**Required Endpoints** (in incident-api):
- `GET /api/v3/stats` - Overall counts
- `GET /api/v3/stats/severity` - By severity (critical/high/medium/low)
- `GET /api/v3/stats/type` - By type (network/system/application)
- `GET /api/v3/stats/duplicates` - Deduplication stats
- `GET /api/v3/stats/suppressions` - Suppression stats

**Data Sources**:
- ClickHouse queries aggregating incidents table
- Real-time stats from service endpoints

#### 3. Error Propagation
**Status**: ⚠️ Utility exists, but NO services use it  

**Required**:
- All services use `extract_error_message()`
- Errors stored in `error_msg` field
- ClickHouse persists errors
- Error query endpoints

---

### Phase 7: Cleanup & Testing (0% implemented)

#### 1. Cleanup Old Code
**Status**: ❌ Not started  

**Files to Remove** (~100+ files):
- Old test scripts (50+ files in root)
- Redundant documentation (40+ MD files)
- Old service implementations
- Unused configurations

**Directories to Clean**:
- Root directory test_*.py files
- Root directory *_SUMMARY.md files
- Old docs in root (move to docs/ or delete)

#### 2. New E2E Tests
**Status**: ❌ Not implemented  

**Required Tests**:
- Fast Path E2E (logs → incidents)
- Insight Path E2E (incidents → LLM → enrichment)
- Tracking ID trace test
- Stats API test
- Error propagation test
- Performance benchmarks

**Files Needed**:
- `tests/v3/test_fast_path_e2e.py`
- `tests/v3/test_insight_path_e2e.py`
- `tests/v3/test_tracking_id.py`
- `tests/v3/test_stats_api.py`
- `tests/v3/test_performance.py`

---

## 📊 Detailed Gap Analysis

### Services Using V3 Contracts

| Service | V3 Design | Current | Gap |
|---------|-----------|---------|-----|
| enrichment-service | Required | ❌ Not exists | **CREATE** |
| correlation-service | Required | ❌ Not exists | **CREATE** |
| llm-enricher | Required | ❌ Not exists | **CREATE** |
| anomaly-detection | V3 models | ❌ Old models | **REFACTOR** |
| incident-api | V3 endpoints | ❌ Old endpoints | **EXTEND** |
| enhanced-anomaly-detection | V3 models | ❌ Old models | **REFACTOR** |

**Total**: 0/6 services using V3 (0%)

### Infrastructure Components

| Component | V3 Design | Current | Gap |
|-----------|-----------|---------|-----|
| Ollama | Required | ❌ Not in compose | **ADD** |
| Qdrant | Required | ❌ Not in compose | **ADD** |
| VMAlert | Required | ❌ Not in compose | **ADD** |
| enrichment-service | Required | ❌ Not in compose | **ADD** |
| correlation-service | Required | ❌ Not in compose | **ADD** |
| llm-enricher | Required | ❌ Not in compose | **ADD** |

**Total**: 0/6 infrastructure components (0%)

### Observability Features

| Feature | V3 Design | Current | Gap |
|---------|-----------|---------|-----|
| tracking_id generation | At ingestion | ❌ Not configured | **ADD** |
| StructuredLogger usage | All services | ❌ 0 services | **UPDATE ALL** |
| Stats API | Full categorization | ❌ Not exists | **CREATE** |
| Trace query | By tracking_id | ❌ Not exists | **CREATE** |
| Error persistence | In ClickHouse | ❌ Not operational | **IMPLEMENT** |

**Total**: 0/5 observability features (0%)

### Testing & Cleanup

| Task | V3 Design | Current | Gap |
|------|-----------|---------|-----|
| Old test cleanup | Remove 50+ files | ❌ 0 removed | **CLEANUP** |
| Old docs cleanup | Remove 40+ files | ❌ 0 removed | **CLEANUP** |
| Fast Path E2E test | Required | ❌ Not exists | **CREATE** |
| Insight Path E2E test | Required | ❌ Not exists | **CREATE** |
| Performance benchmarks | Required | ❌ Not exists | **CREATE** |

**Total**: 0/5 cleanup & testing tasks (0%)

---

## 🎯 Implementation Priority

### Critical Path (Must Have for V3)

**Priority 1 - Fast Path Services** (Blocker for everything):
1. Create enrichment-service
2. Create correlation-service
3. Refactor anomaly-detection to V3
4. Update incident-api with V3 endpoints

**Priority 2 - LLM/RAG Integration** (Insight Path):
1. Create llm-enricher service
2. Add Ollama to docker-compose
3. Add Qdrant to docker-compose
4. Integrate RAG pipeline

**Priority 3 - Observability** (Operational requirement):
1. Add tracking_id generation at Vector
2. Update all services to use StructuredLogger
3. Implement stats API
4. Implement trace query endpoint

**Priority 4 - Infrastructure** (Deployment):
1. Update docker-compose with all services
2. Add VMAlert configuration
3. Configure service dependencies

**Priority 5 - Cleanup & Testing** (Quality):
1. Remove old test files
2. Remove old documentation
3. Create E2E tests
4. Performance benchmarks

---

## 📈 Effort Estimates

### By Phase

| Phase | Tasks | Estimated LOC | Estimated Commits | Time |
|-------|-------|---------------|-------------------|------|
| Phase 3 | Fast Path Services | ~2,000 | 2-3 | 4-6 hours |
| Phase 4 | LLM/RAG Integration | ~1,500 | 2-3 | 3-4 hours |
| Phase 5 | Infrastructure | ~500 | 1-2 | 2-3 hours |
| Phase 6 | Observability | ~1,000 | 2-3 | 3-4 hours |
| Phase 7 | Cleanup & Testing | ~1,000 | 2-3 | 3-4 hours |
| **Total** | **All Remaining** | **~6,000** | **10-15** | **15-20 hours** |

### By Priority

| Priority | Description | LOC | Commits | Blocker |
|----------|-------------|-----|---------|---------|
| P1 | Fast Path Services | 2,000 | 3 | ✅ Yes |
| P2 | LLM/RAG | 1,500 | 3 | ⚠️ Partial |
| P3 | Observability | 1,000 | 3 | ⚠️ Partial |
| P4 | Infrastructure | 500 | 2 | ❌ No |
| P5 | Cleanup/Testing | 1,000 | 3 | ❌ No |

---

## ✅ Acceptance Criteria (Phase 3-7)

### Phase 3: Fast Path Services
- [ ] enrichment-service running and processing anomaly.detected
- [ ] correlation-service running and creating incidents
- [ ] anomaly-detection refactored to V3 models
- [ ] incident-api has V3 endpoints
- [ ] All services use tracking_id
- [ ] All services preserve errors

### Phase 4: LLM/RAG Integration
- [ ] llm-enricher service running
- [ ] Ollama container running with phi3:mini
- [ ] Qdrant container running
- [ ] RAG pipeline functional
- [ ] LLM cache in ClickHouse
- [ ] Fallback to rule-based working

### Phase 5: Infrastructure
- [ ] docker-compose has all V3 services
- [ ] VMAlert configured and running
- [ ] All dependencies correct
- [ ] Health checks passing

### Phase 6: Observability
- [ ] tracking_id generated at ingestion
- [ ] All services use StructuredLogger
- [ ] Stats API delivering categorized counts
- [ ] Trace query functional
- [ ] Errors persisted in ClickHouse

### Phase 7: Cleanup & Testing
- [ ] Old test files removed (50+ files)
- [ ] Old docs removed/organized (40+ files)
- [ ] Fast Path E2E test passing
- [ ] Insight Path E2E test passing
- [ ] Performance benchmarks meet SLOs

---

## 🚀 Next Steps

**Immediate** (Next 1-2 commits):
1. Create enrichment-service
2. Create correlation-service

**Short-term** (Next 3-5 commits):
3. Refactor anomaly-detection
4. Update incident-api
5. Create llm-enricher

**Medium-term** (Next 5-7 commits):
6. Add Ollama + Qdrant to docker-compose
7. Implement observability features
8. Add VMAlert configuration

**Final** (Last 3-4 commits):
9. Cleanup old code
10. Create E2E tests
11. Performance validation

---

## 📝 Recommendations

### For Lead Engineer
1. **Review this status document** - Confirm priorities and scope
2. **Approve phased approach** - Or request all-at-once implementation
3. **Clarify must-haves** - Which features are MVP vs nice-to-have
4. **Allocate time** - 15-20 hours estimated for remaining 75%

### For Implementation
1. **Start with P1** - Fast Path services are blocking everything
2. **Incremental commits** - 2-3 services per commit for reviewability
3. **Test as you go** - Manual health checks after each service
4. **Update docker-compose incrementally** - Add services as they're created

### For Testing
1. **Manual testing first** - Health checks and curl commands
2. **E2E tests after services work** - Don't test broken services
3. **Performance benchmarks last** - After full pipeline functional

---

**Status**: Ready for Phase 3 implementation  
**Next Commit**: enrichment-service + correlation-service  
**Target**: 40% complete after next commit (currently 25%)
