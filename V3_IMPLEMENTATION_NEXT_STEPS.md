# V3 Implementation - Next Steps for Completion

## Current Status (October 2, 2025)

**Progress**: 40% Complete (Phase 3a of 7 completed)  
**Lead Engineer Review**: Addressed with Fast Path services  
**Latest Commit**: a4c456c - Added enrichment-service and correlation-service

---

## ✅ What's Been Delivered (Phases 1-3a)

### Phase 1: Core Infrastructure ✅
- aiops_core package with V3 Pydantic models
- StructuredLogger with tracking_id
- Utility functions (extract_error_message, compute_suppress_key, etc.)

### Phase 2: Policy System ✅
- Master policy.yaml with profile selection
- 9 segmented policy files (ingest, detect, correlate, llm, notify, remediate, retention, privacy, slo)
- Full RAG configuration defined

### Phase 3a: Fast Path Core Services ✅
- **enrichment-service**: Enriches anomalies with ClickHouse context (<500ms)
- **correlation-service**: Correlates anomalies into incidents (<1s)
- Both services use V3 models, tracking_id, error propagation

### Bonus: Documentation & UI ✅
- 67KB comprehensive documentation
- Grafana App Plugin (Operations Console)
- V3_IMPLEMENTATION_STATUS.md tracking document

---

## 🎯 Remaining Work (60% - Phases 3b-7)

### Phase 3b: Refactor Existing Services (High Priority)

#### 1. Refactor anomaly-detection Service
**File**: `services/anomaly-detection/anomaly_service.py`  
**Status**: Uses old dataclass models  
**Required Changes**:

```python
# BEFORE (current):
@dataclass
class AnomalyEvent:
    timestamp: datetime
    metric_name: str
    # ...

# AFTER (V3):
from aiops_core.models import AnomalyDetected
from aiops_core.utils import StructuredLogger, generate_tracking_id

logger = StructuredLogger(__name__)

# Generate tracking_id
tracking_id = generate_tracking_id()

# Create V3 model
anomaly = AnomalyDetected(
    tracking_id=tracking_id,
    ts=datetime.now(),
    ship_id=ship_id,
    domain="system",  # or "network", "application"
    severity="high",
    detector="zscore",
    score=anomaly_score,
    msg=f"Anomaly detected in {metric_name}",
    error_msg=None,  # Preserve any errors
    meta={"metric": metric_name, "value": metric_value, "threshold": threshold}
)

# Publish to NATS
await nats_client.publish("anomaly.detected", anomaly.model_dump_json().encode())
```

**Key Changes**:
- Replace `AnomalyEvent` dataclass with `AnomalyDetected` Pydantic model
- Add `tracking_id` generation using `generate_tracking_id()`
- Use `StructuredLogger` for all logging
- Add error preservation (`error_msg` field)
- Update NATS subject to `anomaly.detected`

**Estimated Effort**: 2-3 hours, ~100 lines changed

#### 2. Update incident-api Service
**File**: `services/incident-api/incident_api.py`  
**Status**: Missing V3 endpoints  
**Required New Endpoints**:

```python
from fastapi import FastAPI, Query
from clickhouse_driver import Client as ClickHouseClient

@app.get("/api/v3/stats")
async def get_stats():
    """Get overall statistics"""
    query = """
        SELECT 
            count() as total_incidents,
            countIf(status='open') as open_incidents,
            countIf(status='resolved') as resolved_incidents,
            countIf(severity='critical') as critical_count,
            countIf(severity='high') as high_count,
            countIf(severity='medium') as medium_count,
            countIf(severity='low') as low_count
        FROM incidents
        WHERE created_at > now() - INTERVAL 24 HOUR
    """
    result = ch_client.execute(query)
    return {
        "total": result[0][0],
        "open": result[0][1],
        "resolved": result[0][2],
        "by_severity": {
            "critical": result[0][3],
            "high": result[0][4],
            "medium": result[0][5],
            "low": result[0][6]
        }
    }

@app.get("/api/v3/stats/type")
async def get_stats_by_type():
    """Get statistics by incident type"""
    query = """
        SELECT 
            incident_type,
            count() as count,
            countIf(severity='critical') as critical,
            countIf(severity='high') as high
        FROM incidents
        WHERE created_at > now() - INTERVAL 24 HOUR
        GROUP BY incident_type
        ORDER BY count DESC
    """
    result = ch_client.execute(query)
    return {
        "by_type": [
            {
                "type": row[0],
                "count": row[1],
                "critical": row[2],
                "high": row[3]
            }
            for row in result
        ]
    }

@app.get("/api/v3/trace/{tracking_id}")
async def trace_request(tracking_id: str):
    """Trace a request through the pipeline"""
    # Query logs, anomalies, and incidents by tracking_id
    logs_query = "SELECT * FROM logs WHERE tracking_id = %(tid)s"
    anomalies_query = "SELECT * FROM anomalies WHERE tracking_id = %(tid)s"
    incidents_query = "SELECT * FROM incidents WHERE meta LIKE %(tid)s"
    
    # Execute queries and return full trace
    # Implementation depends on ClickHouse schema
    return {
        "tracking_id": tracking_id,
        "trace": {
            "logs": [],  # Query results
            "anomalies": [],
            "incidents": []
        }
    }
```

**Key Endpoints to Add**:
- `GET /api/v3/stats` - Overall counts
- `GET /api/v3/stats/severity` - By severity
- `GET /api/v3/stats/type` - By incident type
- `GET /api/v3/trace/{tracking_id}` - Full pipeline trace
- `GET /api/v3/stats/duplicates` - Deduplication stats
- `GET /api/v3/stats/suppressions` - Suppression stats

**Estimated Effort**: 2-3 hours, ~200 lines added

---

### Phase 4: LLM/RAG Integration (Medium Priority)

#### 1. Create llm-enricher Service
**Directory**: `services/llm-enricher/`  
**Purpose**: Async LLM enrichment (Insight Path, <10s)  
**Flow**: `enrichment.request` → LLM → `enrichment.completed`

**Key Components**:
- `llm_enricher_service.py` - Main service
- `llm_client.py` - Ollama integration
- `rag_client.py` - Qdrant integration
- `cache.py` - LLM response caching (45min TTL)

**Features**:
- Ollama model integration (phi3:mini or qwen2.5:3b)
- RAG with Qdrant (5 docs, 0.7 similarity)
- LLM cache in ClickHouse
- 300ms timeout, 1 retry
- Rate limiting (3 concurrent, queue 100)
- Fallback to rule-based

**Estimated Effort**: 4-5 hours, ~400 lines

#### 2. Add Ollama to docker-compose
**File**: `docker-compose.yml`

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: aiops-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    command: serve
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

**Pull Model**:
```bash
docker exec aiops-ollama ollama pull phi3:mini
```

**Estimated Effort**: 1 hour

#### 3. Add Qdrant to docker-compose
**File**: `docker-compose.yml`

```yaml
  qdrant:
    image: qdrant/qdrant:latest
    container_name: aiops-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

**Estimated Effort**: 1 hour

---

### Phase 5: Infrastructure Updates (Medium Priority)

#### 1. Update docker-compose.yml with V3 Services

```yaml
  enrichment-service:
    build: ./services/enrichment-service
    container_name: aiops-enrichment
    ports:
      - "8081:8081"
    environment:
      - NATS_URL=nats://nats:4222
      - CLICKHOUSE_HOST=clickhouse
      - ENRICHMENT_PORT=8081
    depends_on:
      - nats
      - clickhouse
    restart: unless-stopped

  correlation-service:
    build: ./services/correlation-service
    container_name: aiops-correlation
    ports:
      - "8082:8082"
    environment:
      - NATS_URL=nats://nats:4222
      - CORRELATION_PORT=8082
    depends_on:
      - nats
      - enrichment-service
    restart: unless-stopped
```

**All Services to Add**:
- enrichment-service (port 8081)
- correlation-service (port 8082)
- llm-enricher (port 8083)
- ollama (port 11434)
- qdrant (port 6333)
- vmalert (port 8880)

**Estimated Effort**: 2 hours

#### 2. Add VMAlert Configuration
**Directory**: `vmalert/`  
**Files**:
- `vmalert/alerts.yml` - Alert rules
- `vmalert/Dockerfile` - VMAlert container

**Alert Rules**:
- Fast Path SLO: P95 < 1.5s
- Insight Path SLO: P95 < 10s
- Queue health: max 100 lag
- Service health checks

**Estimated Effort**: 2 hours

---

### Phase 6: Observability (High Priority)

#### 1. Add tracking_id Generation at Vector
**File**: `vector/vector.toml`

```toml
[transforms.add_tracking_id]
type = "remap"
inputs = ["source"]
source = '''
.tracking_id = uuid_v4()
.ts = now()
'''
```

**Estimated Effort**: 30 minutes

#### 2. Update All Services to Use StructuredLogger
**Services to Update**:
- enhanced-anomaly-detection
- incident-api
- fleet-aggregation
- All other Python services

**Pattern**:
```python
from aiops_core.utils import StructuredLogger

logger = StructuredLogger(__name__)

logger.info("Processing request", extra={"tracking_id": tracking_id, "ship_id": ship_id})
```

**Estimated Effort**: 3 hours (all services)

---

### Phase 7: Cleanup & Testing (Low Priority)

#### 1. Remove Old Files

**Files to Delete** (~100 files):
```bash
# Old test scripts
rm test_*.py
rm validate_*.py
rm demo_*.py
rm e2e_*.py

# Old summary docs
rm *_SUMMARY.md
rm *_FIX*.md
rm *_REPORT*.md

# Keep only essential docs
mv *.md docs/ || true
```

**Estimated Effort**: 1 hour

#### 2. Create E2E Tests
**Directory**: `tests/v3/`

**Tests Needed**:
- `test_fast_path_e2e.py` - Logs → Incidents
- `test_insight_path_e2e.py` - Incidents → LLM → Enrichment
- `test_tracking_id.py` - Trace through pipeline
- `test_stats_api.py` - Statistics endpoints
- `test_performance.py` - SLO validation

**Estimated Effort**: 4 hours

---

## 📊 Effort Summary

| Phase | Tasks | Estimated Hours | Priority |
|-------|-------|-----------------|----------|
| 3b | Refactor services | 4-6 | ⚠️ High |
| 4 | LLM/RAG | 6-7 | Medium |
| 5 | Infrastructure | 4 | Medium |
| 6 | Observability | 3-4 | ⚠️ High |
| 7 | Cleanup/Testing | 5 | Low |
| **Total** | **All Remaining** | **22-27 hours** | - |

---

## 🚀 Recommended Implementation Order

### Sprint 1 (High Priority - 10 hours)
1. Refactor anomaly-detection to V3 (3 hours)
2. Update incident-api with stats endpoints (3 hours)
3. Add tracking_id generation at Vector (0.5 hours)
4. Update services to use StructuredLogger (3.5 hours)

### Sprint 2 (Medium Priority - 12 hours)
5. Create llm-enricher service (5 hours)
6. Add Ollama + Qdrant to docker-compose (2 hours)
7. Update docker-compose with all V3 services (2 hours)
8. Add VMAlert configuration (2 hours)
9. Integrate RAG pipeline (1 hour)

### Sprint 3 (Cleanup & Testing - 5 hours)
10. Remove old files (1 hour)
11. Create E2E tests (4 hours)

---

## ✅ Acceptance Criteria for V3 Complete

### Must Have (100% Required)
- [ ] All 6 services using V3 models (currently 2/6)
- [ ] tracking_id flows through entire pipeline
- [ ] Error messages preserved and persisted
- [ ] Stats API delivering categorized counts
- [ ] Fast Path SLO: P95 < 1.5s
- [ ] Ollama + Qdrant integrated and functional

### Should Have (80% Required)
- [ ] LLM enricher with RAG operational
- [ ] VMAlert configured with alerts
- [ ] E2E tests passing
- [ ] Old code/tests/docs cleaned up
- [ ] Insight Path SLO: P95 < 10s

### Nice to Have (Optional)
- [ ] Performance benchmarks
- [ ] Advanced correlation algorithms
- [ ] Real-time dashboard updates
- [ ] Mobile-responsive Ops Console

---

## 📞 Questions for Product Owner / Lead Engineer

1. **Scope**: Should we implement all phases, or focus on Phase 3b-4 first (Fast Path + LLM)?
2. **Timeline**: What's the target completion date? (22-27 hours estimated)
3. **Testing**: Manual testing acceptable, or automated E2E tests required?
4. **Cleanup**: Can we defer cleanup to a separate PR, or must be included?
5. **Performance**: Are the SLO targets (Fast Path <1.5s, Insight Path <10s) firm requirements?

---

## 📝 Developer Notes

### Current Blockers
- None - all dependencies available

### Technical Debt
- Old test files should be removed
- Some services use inconsistent logging
- Documentation spread across many files

### Future Enhancements
- Real-time WebSocket updates for Ops Console
- Advanced ML models for anomaly detection
- Multi-tenancy support
- Cross-ship incident correlation

---

**Last Updated**: October 2, 2025  
**Current Commit**: a4c456c  
**Progress**: 40% complete (Phase 3a/7)  
**Next Action**: Implement Phase 3b (refactor anomaly-detection, update incident-api)
