# AIOps NAAS Issue Report - V3 Architecture Implementation Completion

**Issue ID**: ISSUE-20251003-142429-V3-COMPLETION  
**Date**: 2025-10-03T14:24:29Z  
**Reporter**: Lead Engineer  
**Related PR**: #156, #157  
**Priority**: Critical  
**Status**: Open  
**Type**: Epic - Implementation Completion

---

## Issue Summary

Complete the remaining 40% of Version 3 Architecture implementation following PR #156 merge. This includes critical service refactoring, LLM/RAG integration, observability enhancements, and comprehensive testing to achieve a fully functional V3 AIOps platform.

---

## Context and Background

### PR #156 Status
PR #156 successfully delivered 60% of the V3 architecture foundation:
- ✅ **Phase 1-2 Complete**: Core infrastructure (`aiops_core` package with V3 Pydantic models)
- ✅ **Policy System Complete**: Segmented policies with RAG configuration (9 policy files)
- ✅ **Documentation Complete**: 67KB of comprehensive documentation
- ✅ **Grafana Plugin Skeleton**: Operations Console structure created

### What's Missing (40% - CRITICAL)
- ❌ **Phase 3b**: Service refactoring to V3 models (4 services)
- ❌ **Phase 4**: LLM/RAG service implementation (Ollama + Qdrant + llm-enricher)
- ❌ **Phase 5**: Infrastructure updates (docker-compose, VMAlert, tracking_id)
- ❌ **Phase 6**: Observability (StructuredLogger adoption, error propagation)
- ❌ **Phase 7**: Cleanup and end-to-end testing

**Current State**: System is non-functional for V3 workflows. All services still use old V2 contracts.

---

## Test Case Information

- **Test Case ID**: TC-V3-001
- **Test Case Name**: V3 Architecture End-to-End Implementation
- **Test Phase**: Full System Integration
- **Dependencies**: PR #156 merged foundation
- **Validation**: E2E tests for Fast Path and Insight Path

---

## Issue Description

The V3 architecture implementation is incomplete and requires immediate completion of critical services and infrastructure components to make the system operational. Without these components, the V3 data models and policy framework delivered in PR #156 cannot function.

### Expected Behavior

**Fast Path Pipeline** (Target: <100ms):
1. Log ingestion → Vector with tracking_id generation
2. Anomaly detection → Uses `AnomalyDetected` V3 model
3. Enrichment service → Adds context from ClickHouse
4. Correlation service → Forms incidents with deduplication
5. Incident API → Stores and exposes via `/api/v3/*` endpoints

**Insight Path Pipeline** (Target: <5s):
1. LLM enricher → Receives from Fast Path
2. Ollama integration → Generates AI insights
3. Qdrant RAG → Retrieves historical context
4. Enhanced incident → Published with AI enrichment
5. Incident API → Exposes enriched data

### Actual Behavior

- Services use old dataclass models instead of V3 Pydantic models
- No enrichment or correlation services exist
- LLM/RAG infrastructure not deployed
- tracking_id not generated at ingestion
- StructuredLogger not adopted by any service
- No V3 API endpoints available
- System cannot process V3 workflows

### Impact Assessment

**Severity Justification**: CRITICAL
- System is non-functional for V3 architecture
- 40% of implementation effort remains
- Blocks all v1.0 milestone features
- Technical debt increases with delay

**Service Impact**:
- **Primary**: All services affected (anomaly-detection, incident-api, missing enrichment/correlation/llm-enricher)
- **Secondary**: Infrastructure (Vector, docker-compose, VMAlert)
- **Data Flow Impact**: V3 pipeline completely non-functional
- **User Impact**: No AI/ML capabilities, no advanced incident correlation

**Business Impact**:
- **Functionality Lost**: AI-driven insights, predictive analytics, automated enrichment
- **Data Loss Risk**: No - existing data safe, but V3 features unavailable
- **Security Impact**: None - security model unchanged

---

## Pending Items - Detailed Breakdown

### 🔴 CRITICAL PRIORITY (Blockers - 12-16 hours)

#### 1. Refactor anomaly-detection Service (2-3 hours)
**File**: `services/anomaly-detection/anomaly_service.py`

**Current State**:
- Uses old dataclass models
- No tracking_id support
- No StructuredLogger

**Required Changes**:
```python
# Change from old dataclass to V3 Pydantic model
from aiops_core.models import AnomalyDetected, LogEntry
from aiops_core.utils import StructuredLogger

# Update anomaly detection logic to:
# 1. Accept LogEntry V3 model
# 2. Generate AnomalyDetected V3 model
# 3. Preserve tracking_id throughout
# 4. Use StructuredLogger for all logging
```

**Acceptance Criteria**:
- [ ] Service uses `AnomalyDetected` from aiops_core
- [ ] tracking_id preserved from log entry
- [ ] All logging uses StructuredLogger
- [ ] Unit tests updated for V3 models
- [ ] Service health check passes

**Estimated Lines Changed**: ~100-150 lines

---

#### 2. Create enrichment-service (4-5 hours)
**New Service**: `services/enrichment-service/`

**Purpose**: Fast Path L1 enrichment with ClickHouse context lookups

**Directory Structure**:
```
services/enrichment-service/
├── Dockerfile
├── requirements.txt
├── enrichment_service.py
├── clickhouse_queries.py
└── config.yaml
```

**Core Functionality**:
```python
from aiops_core.models import AnomalyDetected, EnrichedAnomaly
from aiops_core.utils import StructuredLogger

# 1. Subscribe to NATS topic: anomaly.detected
# 2. Enrich with ClickHouse context:
#    - Historical failure rates
#    - Device metadata
#    - Recent similar anomalies
# 3. Create EnrichedAnomaly model
# 4. Publish to: anomaly.enriched
# 5. Target latency: <30ms
```

**ClickHouse Queries**:
- Device metadata lookup by device_id
- Historical anomaly count (24h window)
- Similar anomaly search (7d window)
- Service health metrics

**Acceptance Criteria**:
- [ ] Service subscribes to `anomaly.detected` NATS topic
- [ ] ClickHouse context queries functional
- [ ] Publishes `EnrichedAnomaly` to `anomaly.enriched`
- [ ] Latency <30ms (99th percentile)
- [ ] Error handling with fallback to basic enrichment
- [ ] Health endpoint at `/health`
- [ ] Metrics endpoint at `/metrics`

**Estimated Lines**: ~500 lines

---

#### 3. Create correlation-service (4-5 hours)
**New Service**: `services/correlation-service/`

**Purpose**: Fast Path incident formation with deduplication and time-windowing

**Directory Structure**:
```
services/correlation-service/
├── Dockerfile
├── requirements.txt
├── correlation_service.py
├── deduplication.py
├── windowing.py
└── config.yaml
```

**Core Functionality**:
```python
from aiops_core.models import EnrichedAnomaly, Incident
from aiops_core.utils import StructuredLogger

# 1. Subscribe to NATS topic: anomaly.enriched
# 2. Apply correlation logic:
#    - Time-window clustering (5min default)
#    - Deduplication by signature
#    - Severity aggregation
#    - Root cause identification
# 3. Form Incident model
# 4. Publish to: incidents.created
# 5. Target latency: <50ms
```

**Correlation Algorithms**:
- Time-based windowing (configurable: 1m-30m)
- Fingerprint-based deduplication
- Related anomaly grouping
- Suppression rules from policy system

**Acceptance Criteria**:
- [ ] Service subscribes to `anomaly.enriched` NATS topic
- [ ] Deduplication logic prevents duplicate incidents
- [ ] Time-windowing clusters related anomalies
- [ ] Publishes `Incident` to `incidents.created`
- [ ] Latency <50ms (99th percentile)
- [ ] Suppression rules applied from policy
- [ ] Health endpoint at `/health`
- [ ] Metrics endpoint at `/metrics`

**Estimated Lines**: ~600 lines

---

#### 4. Update incident-api with V3 Endpoints (2-3 hours)
**File**: `services/incident-api/incident_api.py`

**Current State**:
- Basic CRUD operations only
- No V3 endpoints
- No stats or tracing APIs

**Required V3 Endpoints**:

```python
# Statistics API
@app.get("/api/v3/stats")
async def get_stats(time_range: str = "1h"):
    """
    Return incident statistics:
    - Total incidents (by severity, status, category)
    - Processing metrics (fast path, insight path)
    - SLO compliance (latency percentiles)
    """

# Trace API
@app.get("/api/v3/trace/{tracking_id}")
async def trace_request(tracking_id: str):
    """
    End-to-end trace for a tracking_id:
    - Log ingestion timestamp
    - Anomaly detection timestamp
    - Enrichment timestamp
    - Correlation timestamp
    - LLM enrichment timestamp (if applicable)
    - Total latency breakdown
    """

# Incident CRUD with V3 models
@app.post("/api/v3/incidents")
async def create_incident(incident: Incident):
    """Accept V3 Incident model"""

@app.get("/api/v3/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Return V3 Incident model"""
```

**Acceptance Criteria**:
- [ ] `/api/v3/stats` returns categorized incident counts
- [ ] `/api/v3/trace/{tracking_id}` returns full pipeline trace
- [ ] All endpoints use V3 Pydantic models
- [ ] ClickHouse queries optimized for stats
- [ ] API documentation updated (OpenAPI/Swagger)
- [ ] Unit tests for new endpoints

**Estimated Lines Added**: ~200 lines

---

### 🟠 HIGH PRIORITY (AI/ML Capabilities - 6-7 hours)

#### 5. Create llm-enricher Service (4-5 hours)
**New Service**: `services/llm-enricher/`

**Purpose**: Insight Path AI enrichment with Ollama LLM and Qdrant RAG

**Directory Structure**:
```
services/llm-enricher/
├── Dockerfile
├── requirements.txt
├── llm_service.py
├── ollama_client.py
├── qdrant_rag.py
├── llm_cache.py
└── config.yaml
```

**Core Functionality**:
```python
from aiops_core.models import Incident, EnrichedIncident
from aiops_core.utils import StructuredLogger

# 1. Subscribe to NATS topic: incidents.created
# 2. Generate AI insights:
#    - Root cause analysis (Ollama phi3:mini)
#    - Similar incidents (Qdrant RAG)
#    - Remediation suggestions
#    - Impact prediction
# 3. Cache LLM responses in ClickHouse
# 4. Publish EnrichedIncident to: incidents.enriched
# 5. Target latency: <300ms (with timeout fallback)
```

**LLM Integration**:
```python
# Ollama client with timeout
async def generate_insight(incident: Incident) -> str:
    prompt = f"""
    Analyze this maritime incident:
    - Type: {incident.category}
    - Severity: {incident.severity}
    - Affected: {incident.affected_services}
    - Context: {incident.context}
    
    Provide:
    1. Root cause analysis
    2. Impact assessment
    3. Recommended actions
    """
    
    response = await ollama_client.generate(
        model="phi3:mini",
        prompt=prompt,
        timeout=300  # 300ms max
    )
    return response
```

**RAG Pipeline**:
```python
# Qdrant similarity search
async def find_similar_incidents(incident: Incident) -> list:
    # 1. Embed incident description
    embedding = await embed_text(incident.description)
    
    # 2. Search Qdrant
    similar = await qdrant_client.search(
        collection="incidents",
        query_vector=embedding,
        limit=5
    )
    
    # 3. Return historical context
    return [s.payload for s in similar]
```

**Acceptance Criteria**:
- [ ] Service subscribes to `incidents.created` NATS topic
- [ ] Ollama integration functional with phi3:mini model
- [ ] Qdrant RAG retrieves similar incidents
- [ ] LLM responses cached in ClickHouse
- [ ] Publishes `EnrichedIncident` to `incidents.enriched`
- [ ] Timeout fallback (graceful degradation)
- [ ] Latency <300ms target (99th percentile)
- [ ] Health endpoint at `/health`
- [ ] Metrics for LLM latency and cache hit rate

**Estimated Lines**: ~800 lines

---

#### 6. Add Ollama to docker-compose (1 hour)

**Current State**: `docker-compose.v3.yml` exists but not integrated

**Required Changes**:
```yaml
# Add to docker-compose.yml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: aiops-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_MODELS=/root/.ollama/models
    networks:
      - aiops
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama_data:
```

**Initialization Script**:
```bash
# scripts/init_ollama.sh
#!/bin/bash
# Wait for Ollama to be ready
until curl -f http://localhost:11434/api/tags; do
  sleep 2
done

# Pull phi3:mini model
docker exec aiops-ollama ollama pull phi3:mini

echo "Ollama initialized with phi3:mini model"
```

**Acceptance Criteria**:
- [ ] Ollama service added to docker-compose.yml
- [ ] phi3:mini model pulled and ready
- [ ] Health check passing
- [ ] API accessible at http://localhost:11434
- [ ] Initialization script created and tested

---

#### 7. Add Qdrant to docker-compose (1 hour)

**Required Changes**:
```yaml
# Add to docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: aiops-qdrant
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    networks:
      - aiops
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  qdrant_data:
```

**Collection Initialization**:
```python
# scripts/init_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)

# Create incidents collection
client.create_collection(
    collection_name="incidents",
    vectors_config=VectorParams(
        size=384,  # all-MiniLM-L6-v2 embedding size
        distance=Distance.COSINE
    )
)

print("Qdrant initialized with incidents collection")
```

**Acceptance Criteria**:
- [ ] Qdrant service added to docker-compose.yml
- [ ] Collection "incidents" created
- [ ] Health check passing
- [ ] HTTP API accessible at http://localhost:6333
- [ ] gRPC API accessible at localhost:6334
- [ ] Initialization script created and tested

---

### 🟡 MEDIUM PRIORITY (Infrastructure - 7.5 hours)

#### 8. Update docker-compose.yml with All V3 Services (2 hours)

**Current State**: V3 services not in main docker-compose.yml

**Required Services**:
```yaml
services:
  # New V3 Services
  enrichment-service:
    build: ./services/enrichment-service
    container_name: aiops-enrichment
    depends_on:
      - nats
      - clickhouse
    environment:
      - NATS_URL=nats://nats:4222
      - CLICKHOUSE_HOST=clickhouse
    networks:
      - aiops

  correlation-service:
    build: ./services/correlation-service
    container_name: aiops-correlation
    depends_on:
      - nats
      - enrichment-service
    environment:
      - NATS_URL=nats://nats:4222
    networks:
      - aiops

  llm-enricher:
    build: ./services/llm-enricher
    container_name: aiops-llm-enricher
    depends_on:
      - nats
      - ollama
      - qdrant
      - clickhouse
    environment:
      - NATS_URL=nats://nats:4222
      - OLLAMA_URL=http://ollama:11434
      - QDRANT_URL=http://qdrant:6333
      - CLICKHOUSE_HOST=clickhouse
    networks:
      - aiops

  # Merge from docker-compose.v3.yml
  ollama:
    # (from task #6)
  
  qdrant:
    # (from task #7)
```

**Dependency Graph**:
```
Vector → anomaly-detection → enrichment-service → correlation-service → incident-api
                                                         ↓
                                                   llm-enricher (async)
                                                         ↓
                                                   incident-api (enriched)
```

**Acceptance Criteria**:
- [ ] All V3 services added to docker-compose.yml
- [ ] Dependencies correctly configured
- [ ] Environment variables set
- [ ] Health checks defined for all services
- [ ] `docker-compose up` starts all services successfully
- [ ] Service startup order correct

---

#### 9. Add VMAlert Configuration (2 hours)

**Purpose**: SLO monitoring for Fast Path and Insight Path

**Directory**: `vmalert/`

**Configuration Files**:
```yaml
# vmalert/alerts.yml
groups:
  - name: aiops_slo_fast_path
    interval: 30s
    rules:
      - alert: FastPathLatencyHigh
        expr: |
          histogram_quantile(0.99, 
            sum(rate(aiops_fast_path_latency_seconds_bucket[5m])) by (le)
          ) > 0.1
        for: 5m
        labels:
          severity: critical
          path: fast
        annotations:
          summary: "Fast Path 99th percentile latency exceeds 100ms SLO"
          description: "Current latency: {{ $value }}s"

      - alert: FastPathErrorRate
        expr: |
          sum(rate(aiops_fast_path_errors_total[5m])) 
          / sum(rate(aiops_fast_path_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: high
          path: fast
        annotations:
          summary: "Fast Path error rate exceeds 1% threshold"

  - name: aiops_slo_insight_path
    interval: 30s
    rules:
      - alert: InsightPathLatencyHigh
        expr: |
          histogram_quantile(0.99,
            sum(rate(aiops_insight_path_latency_seconds_bucket[5m])) by (le)
          ) > 5.0
        for: 5m
        labels:
          severity: warning
          path: insight
        annotations:
          summary: "Insight Path 99th percentile latency exceeds 5s SLO"

      - alert: LLMServiceDown
        expr: up{job="llm-enricher"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "LLM enrichment service is down"
```

**VMAlert Docker Service**:
```yaml
# Add to docker-compose.yml
services:
  vmalert:
    image: victoriametrics/vmalert:latest
    container_name: aiops-vmalert
    command:
      - '-rule=/etc/vmalert/alerts.yml'
      - '-datasource.url=http://victoriametrics:8428'
      - '-notifier.url=http://alertmanager:9093'
      - '-external.url=http://localhost:8880'
    ports:
      - "8880:8880"
    volumes:
      - ./vmalert/alerts.yml:/etc/vmalert/alerts.yml:ro
    depends_on:
      - victoriametrics
    networks:
      - aiops
```

**Acceptance Criteria**:
- [ ] VMAlert service configured in docker-compose
- [ ] Fast Path SLO alerts defined (latency, error rate)
- [ ] Insight Path SLO alerts defined (latency, service health)
- [ ] Alert rules validated with promtool
- [ ] VMAlert UI accessible at http://localhost:8880

---

#### 10. Add tracking_id Generation at Vector (30 minutes)

**File**: `vector/vector.toml`

**Current State**: No tracking_id in logs

**Required Changes**:
```toml
# Add to Vector configuration
[transforms.add_tracking_id]
type = "remap"
inputs = ["syslog"]
source = '''
  .tracking_id = uuid_v4()
  .ingestion_timestamp = now()
'''

# Update pipeline
[sinks.to_clickhouse]
inputs = ["add_tracking_id"]  # Changed from ["syslog"]

[sinks.to_nats_anomaly]
inputs = ["add_tracking_id"]  # Changed from ["syslog"]
```

**Verification Query**:
```sql
-- ClickHouse query to verify tracking_id
SELECT tracking_id, COUNT(*) 
FROM logs.raw 
WHERE ingestion_timestamp > now() - INTERVAL 1 HOUR
GROUP BY tracking_id
LIMIT 10;
```

**Acceptance Criteria**:
- [ ] tracking_id generated for all incoming logs
- [ ] UUIDv4 format validated
- [ ] ingestion_timestamp added
- [ ] ClickHouse stores tracking_id
- [ ] NATS messages include tracking_id
- [ ] No performance degradation (latency <5ms added)

---

#### 11. Update All Services to StructuredLogger (3 hours)

**Affected Services**:
- `services/anomaly-detection/`
- `services/incident-api/`
- `services/enrichment-service/` (new)
- `services/correlation-service/` (new)
- `services/llm-enricher/` (new)
- All other Python services

**Migration Pattern**:
```python
# Before
import logging
logger = logging.getLogger(__name__)

logger.info("Processing anomaly")
logger.error(f"Failed to process: {error}")

# After
from aiops_core.utils import StructuredLogger

logger = StructuredLogger.get_logger(
    name=__name__,
    service="anomaly-detection",
    version="3.0.0"
)

logger.info(
    "processing_anomaly",
    tracking_id=tracking_id,
    severity=anomaly.severity
)

logger.error(
    "processing_failed",
    tracking_id=tracking_id,
    error_msg=str(error),
    error_type=type(error).__name__
)
```

**StructuredLogger Benefits**:
- Automatic tracking_id propagation
- Structured JSON output
- Correlation-friendly format
- Performance metrics
- Error categorization

**Acceptance Criteria**:
- [ ] All services use StructuredLogger
- [ ] Legacy logging.getLogger removed
- [ ] All log statements include tracking_id
- [ ] JSON log format validated
- [ ] ClickHouse logs table updated if needed
- [ ] Grafana dashboards can parse structured logs

**Estimated Changes**: ~50-100 lines per service

---

### 🟢 LOW PRIORITY (Quality & Cleanup - 7 hours)

#### 12. Cleanup Old Files (1 hour)

**Files to Remove** (~100+ files):

**Old Test Files** (50+):
```bash
# Root directory test files
rm test_benthos_*.py
rm test_integration*.py
rm test_issue_*.py
rm test_v0*.py
rm validate_*.py
rm demo_*.py
```

**Old Documentation** (40+):
```bash
# Redundant summary files
rm *_FIX_SUMMARY.md
rm *_ISSUE_REPORT*.md
rm INCIDENT_DATA_*.md
rm ONE_CLICK_*.md
rm CRITICAL_*.md
rm COMPLETE_*.md
```

**Consolidation**:
- Move valid test scripts to `tests/legacy/` (for reference)
- Archive important summaries to `docs/legacy/`
- Update README.md references

**Acceptance Criteria**:
- [ ] 50+ test files removed from root
- [ ] 40+ summary files removed/archived
- [ ] Important files preserved in legacy folders
- [ ] README.md updated with new structure
- [ ] .gitignore updated if needed

---

#### 13. Create E2E Tests (4 hours)

**Test Files**:
```
tests/v3/
├── __init__.py
├── test_fast_path_e2e.py
├── test_insight_path_e2e.py
├── test_api_endpoints.py
└── conftest.py
```

**Fast Path E2E Test**:
```python
# tests/v3/test_fast_path_e2e.py
import pytest
import asyncio
from datetime import datetime
from aiops_core.models import LogEntry, AnomalyDetected, Incident

@pytest.mark.asyncio
async def test_fast_path_end_to_end():
    """
    Test Fast Path pipeline: Log → Anomaly → Enrich → Correlate → Incident
    Target latency: <100ms
    """
    start_time = datetime.now()
    
    # 1. Send test log via Vector
    tracking_id = send_test_log(
        message="ERROR Database connection timeout",
        ship_id="ship-aurora",
        severity="error"
    )
    
    # 2. Wait for anomaly detection
    anomaly = await wait_for_nats_message(
        topic="anomaly.detected",
        tracking_id=tracking_id,
        timeout=5
    )
    assert anomaly.tracking_id == tracking_id
    
    # 3. Wait for enrichment
    enriched = await wait_for_nats_message(
        topic="anomaly.enriched",
        tracking_id=tracking_id,
        timeout=5
    )
    assert enriched.context is not None
    
    # 4. Wait for incident creation
    incident = await wait_for_nats_message(
        topic="incidents.created",
        tracking_id=tracking_id,
        timeout=5
    )
    assert incident.id is not None
    
    # 5. Verify incident in API
    api_incident = get_incident_by_tracking_id(tracking_id)
    assert api_incident.id == incident.id
    
    # 6. Verify latency SLO
    end_time = datetime.now()
    latency_ms = (end_time - start_time).total_seconds() * 1000
    assert latency_ms < 100, f"Fast Path latency {latency_ms}ms exceeds 100ms SLO"
    
    # 7. Verify trace API
    trace = get_trace(tracking_id)
    assert trace["total_latency_ms"] < 100
    assert len(trace["stages"]) == 4  # detect, enrich, correlate, store
```

**Insight Path E2E Test**:
```python
# tests/v3/test_insight_path_e2e.py
import pytest
import asyncio
from datetime import datetime

@pytest.mark.asyncio
async def test_insight_path_end_to_end():
    """
    Test Insight Path: Incident → LLM Enrichment → Enhanced Incident
    Target latency: <5s
    """
    start_time = datetime.now()
    
    # 1. Create incident (via Fast Path)
    incident_id = create_test_incident()
    
    # 2. Wait for LLM enrichment
    enriched_incident = await wait_for_nats_message(
        topic="incidents.enriched",
        incident_id=incident_id,
        timeout=10
    )
    
    # 3. Verify AI insights
    assert enriched_incident.llm_insights is not None
    assert "root_cause" in enriched_incident.llm_insights
    assert "recommendations" in enriched_incident.llm_insights
    
    # 4. Verify RAG context
    assert enriched_incident.similar_incidents is not None
    assert len(enriched_incident.similar_incidents) > 0
    
    # 5. Verify latency SLO
    end_time = datetime.now()
    latency_s = (end_time - start_time).total_seconds()
    assert latency_s < 5, f"Insight Path latency {latency_s}s exceeds 5s SLO"
    
    # 6. Verify LLM cache
    cache_hit = check_llm_cache(incident_id)
    # First call won't be cached, but verify cache works
```

**Acceptance Criteria**:
- [ ] Fast Path E2E test validates full pipeline
- [ ] Insight Path E2E test validates LLM enrichment
- [ ] SLO assertions in place (100ms, 5s)
- [ ] Tests run in CI/CD pipeline
- [ ] All tests passing
- [ ] Test coverage >80% for V3 code

**Estimated Lines**: ~600 lines of test code

---

#### 14. Build and Test Grafana Plugin (2 hours)

**Directory**: `grafana/plugins/aiops-ops-console/`

**Current State**: Skeleton only, not built

**Build Process**:
```bash
cd grafana/plugins/aiops-ops-console

# Install dependencies
npm install

# Build plugin
npm run build

# Generate production bundle
npm run build:prod

# Verify build artifacts
ls -la dist/
```

**Required npm Scripts** (add to package.json):
```json
{
  "scripts": {
    "build": "webpack --mode development",
    "build:prod": "webpack --mode production",
    "dev": "webpack --mode development --watch",
    "test": "jest",
    "lint": "eslint src/**/*.{ts,tsx}"
  }
}
```

**Manual Testing**:
1. Copy plugin to Grafana plugins directory
2. Restart Grafana
3. Enable plugin in Grafana UI
4. Test each page:
   - Incidents dashboard (list, filter, detail view)
   - Approvals workflow (pending actions, approve/reject)
   - Actions history (executed remediations)
   - Policy viewer (current active policies)
5. Test API integration with backend

**Acceptance Criteria**:
- [ ] `npm install` completes without errors
- [ ] `npm run build` produces dist/ artifacts
- [ ] Plugin loads in Grafana without errors
- [ ] All 4 pages render correctly
- [ ] API calls to incident-api succeed
- [ ] UI matches design mockups
- [ ] No console errors

---

## Implementation Strategy

### Execution Approach

**Phased Implementation** (Recommended for risk management):

**Phase 1 - Critical Services** (Week 1):
- Days 1-2: Tasks #1-4 (Service refactoring)
- Day 3: Integration testing, bug fixes

**Phase 2 - AI/ML Stack** (Week 2):
- Days 1-2: Tasks #5-7 (LLM/RAG)
- Day 3: Integration testing, performance tuning

**Phase 3 - Infrastructure** (Week 3):
- Days 1-2: Tasks #8-11 (docker-compose, VMAlert, tracking_id, logging)
- Day 3: Integration testing, documentation

**Phase 4 - Quality** (Week 4):
- Day 1: Task #12 (Cleanup)
- Days 2-3: Tasks #13-14 (E2E tests, Grafana plugin)
- Day 4: Final validation, deployment prep

### Continuous Integration Strategy

**After Each Phase**:
1. Run integration tests
2. Deploy to staging environment
3. Performance validation against SLOs
4. Update documentation
5. Team review and approval

**Quality Gates**:
- [ ] All unit tests passing (>90% coverage)
- [ ] Integration tests passing
- [ ] SLO metrics within targets
- [ ] No critical security vulnerabilities
- [ ] Documentation updated

### Rollback Plan

**Per Service**:
- Feature flags for V3 services
- Graceful degradation if LLM unavailable
- Old V2 services remain available during transition
- Database migrations reversible

---

## Testing Strategy

### Unit Tests
- Each service has >90% code coverage
- Mock external dependencies (NATS, ClickHouse, Ollama)
- Test edge cases and error handling

### Integration Tests
- Service-to-service communication
- NATS message flow
- ClickHouse queries
- LLM integration

### E2E Tests
- Fast Path pipeline (<100ms)
- Insight Path pipeline (<5s)
- API endpoints
- Error scenarios

### Performance Tests
- Load testing (1000 events/sec)
- Latency validation (SLO compliance)
- Resource usage monitoring
- Stress testing (failure scenarios)

### Manual Tests
- Grafana plugin UI
- Dashboard functionality
- User workflows
- Documentation accuracy

---

## Success Criteria

### Functional Requirements
- [ ] Fast Path pipeline operational (<100ms latency)
- [ ] Insight Path pipeline operational (<5s latency)
- [ ] All V3 API endpoints functional
- [ ] LLM enrichment working with fallback
- [ ] RAG similarity search functional
- [ ] Incident correlation and deduplication working
- [ ] tracking_id throughout entire pipeline
- [ ] Structured logging in all services

### Non-Functional Requirements
- [ ] 99th percentile latency: Fast Path <100ms, Insight Path <5s
- [ ] Error rate <1% under normal load
- [ ] Service uptime >99.9%
- [ ] Code coverage >90%
- [ ] Documentation complete and accurate
- [ ] Grafana dashboards operational

### Deployment Requirements
- [ ] All services in docker-compose.yml
- [ ] Health checks passing
- [ ] VMAlert monitoring configured
- [ ] Initialization scripts working
- [ ] One-command deployment: `docker-compose up`

---

## Risk Assessment

### Technical Risks

**Risk 1: LLM Latency Exceeds SLO**
- **Probability**: Medium
- **Impact**: High (Insight Path SLO violation)
- **Mitigation**: 
  - Implement 300ms timeout with fallback
  - Cache frequently asked patterns
  - Use streaming responses where possible
  - Model optimization (quantization)

**Risk 2: Service Integration Issues**
- **Probability**: Medium
- **Impact**: Medium (Pipeline breaks)
- **Mitigation**:
  - Incremental testing after each service
  - Contract testing between services
  - Comprehensive error handling
  - Service mesh observability

**Risk 3: Performance Degradation**
- **Probability**: Low
- **Impact**: High (SLO violations)
- **Mitigation**:
  - Load testing before production
  - Performance profiling
  - Resource limits configured
  - Auto-scaling strategy

**Risk 4: Data Migration Issues**
- **Probability**: Low
- **Impact**: Medium (Temporary data unavailability)
- **Mitigation**:
  - Database migration scripts tested
  - Rollback procedures defined
  - Backward compatibility maintained
  - Zero-downtime deployment

### Organizational Risks

**Risk 5: Time Estimate Overrun**
- **Probability**: Medium
- **Impact**: Medium (Delayed delivery)
- **Mitigation**:
  - Buffer time in estimates (20%)
  - Phased delivery approach
  - Clear prioritization (critical first)
  - Daily progress tracking

**Risk 6: Scope Creep**
- **Probability**: Medium
- **Impact**: Medium (Extended timeline)
- **Mitigation**:
  - Strict adherence to defined scope
  - Change control process
  - Defer non-critical features
  - Regular stakeholder alignment

---

## Resource Requirements

### Development Team
- **Senior Backend Engineer**: 3-4 weeks full-time
- **ML/AI Engineer**: 1 week (LLM/RAG integration)
- **DevOps Engineer**: 1 week (Infrastructure)
- **QA Engineer**: 1 week (Testing)
- **Technical Writer**: 0.5 week (Documentation)

### Infrastructure
- **Development Environment**:
  - Docker host: 8 CPU, 16GB RAM
  - Disk: 100GB SSD
  - GPU: Optional (for Ollama optimization)

- **Staging Environment**:
  - Similar to production
  - Kubernetes cluster OR docker-compose
  - Monitoring stack (Grafana, Prometheus)

- **Production Requirements**:
  - Per PR #156 architecture specs
  - Ollama model size: ~2GB (phi3:mini)
  - Qdrant storage: 10GB+ (grows with incidents)

### External Dependencies
- **Ollama**: phi3:mini model (2.3GB download)
- **Qdrant**: Vector database (container ~500MB)
- **Python packages**: See individual service requirements.txt
- **NPM packages**: Grafana plugin dependencies

---

## Documentation Updates Required

### Technical Documentation
- [ ] Update `docs/ARCHITECTURE_OVERVIEW.md` with implemented services
- [ ] Update `docs/SEQUENTIAL_PIPELINE_VALIDATION.md` with V3 validation
- [ ] Create `docs/V3_DEPLOYMENT_GUIDE.md`
- [ ] Create `docs/V3_TROUBLESHOOTING.md`
- [ ] Update `docs/quick-reference.md` with V3 APIs

### API Documentation
- [ ] OpenAPI/Swagger specs for all V3 endpoints
- [ ] Postman collection for V3 APIs
- [ ] API usage examples

### Operational Documentation
- [ ] Service startup/shutdown procedures
- [ ] Health check guide
- [ ] Monitoring and alerting guide
- [ ] Incident response runbook
- [ ] Performance tuning guide

### Development Documentation
- [ ] Service development guide (using aiops_core)
- [ ] Testing guide (unit, integration, E2E)
- [ ] Contributing guide updates
- [ ] Code style guide (Pydantic models, StructuredLogger)

---

## Related Information

### Related Issues
- **Depends on**: PR #156 (merged - foundation complete)
- **Blocks**: v1.0 milestone release
- **Related to**: 
  - Issue #147 (Benthos fixes - informational)
  - Historical issues documented in *_FIX_SUMMARY.md files

### Previous Work
- PR #156: Foundation (60% complete)
  - aiops_core package
  - Policy system
  - Documentation
  - Grafana plugin skeleton

### External Dependencies
- Ollama project: https://ollama.ai
- Qdrant project: https://qdrant.tech
- Pydantic V2: https://docs.pydantic.dev

---

## Copilot Agent Work Prompt

**Prompt for GitHub Copilot Agent to autonomously implement this issue:**

```
You are a senior backend engineer implementing the remaining 40% of the V3 AIOps Architecture.

CONTEXT:
- PR #156 delivered the foundation (aiops_core, policies, docs)
- You need to implement 14 tasks across 4 priority levels
- All V3 models are in aiops_core.models (Pydantic V2)
- All services should use aiops_core.utils.StructuredLogger
- Target SLOs: Fast Path <100ms, Insight Path <5s

CRITICAL PATH (Do First):
1. Refactor anomaly-detection to use AnomalyDetected model from aiops_core
2. Create enrichment-service (Fast Path L1 enrichment)
3. Create correlation-service (incident formation)
4. Add V3 endpoints to incident-api (/api/v3/stats, /api/v3/trace/{id})

IMPLEMENTATION GUIDELINES:
- Use aiops_core.models for all data contracts
- Use aiops_core.utils.StructuredLogger for all logging
- Preserve tracking_id throughout pipeline
- Add health checks to all services
- Follow existing code patterns from PR #156
- Test incrementally after each service

SERVICE PATTERNS:
```python
from aiops_core.models import AnomalyDetected, Incident
from aiops_core.utils import StructuredLogger
import asyncio
from nats.aio.client import Client as NATS

logger = StructuredLogger.get_logger(__name__, "service-name", "3.0.0")

async def main():
    nc = await NATS.connect("nats://nats:4222")
    
    async def message_handler(msg):
        data = json.loads(msg.data.decode())
        tracking_id = data.get("tracking_id")
        
        logger.info("processing", tracking_id=tracking_id)
        # Process message
        logger.info("completed", tracking_id=tracking_id)
    
    await nc.subscribe("topic", cb=message_handler)
```

TESTING:
- Write unit tests with pytest
- Mock external dependencies
- Validate SLO compliance
- Run integration tests after each phase

SUCCESS CRITERIA:
- All 14 tasks completed
- Fast Path E2E test passing (<100ms)
- Insight Path E2E test passing (<5s)
- All services healthy in docker-compose
- Documentation updated

WORK INCREMENTALLY:
1. Complete critical tasks first (#1-4)
2. Commit after each service
3. Test before moving to next task
4. Update docker-compose progressively
5. Document as you go

Begin with Task #1: Refactor anomaly-detection service.
Use the detailed task descriptions in this issue as your specification.
Ask for clarification if any requirement is ambiguous.
```

---

## Timeline and Milestones

### Week 1: Critical Services (Tasks #1-4)
**Deliverables**:
- ✅ anomaly-detection refactored
- ✅ enrichment-service created
- ✅ correlation-service created  
- ✅ incident-api V3 endpoints added
- ✅ Fast Path pipeline functional

**Exit Criteria**: Fast Path E2E test passing

### Week 2: AI/ML Integration (Tasks #5-7)
**Deliverables**:
- ✅ llm-enricher service created
- ✅ Ollama integrated with phi3:mini
- ✅ Qdrant RAG functional
- ✅ Insight Path pipeline functional

**Exit Criteria**: Insight Path E2E test passing

### Week 3: Infrastructure (Tasks #8-11)
**Deliverables**:
- ✅ docker-compose.yml updated
- ✅ VMAlert monitoring configured
- ✅ tracking_id at Vector
- ✅ All services using StructuredLogger

**Exit Criteria**: Full observability stack operational

### Week 4: Quality & Cleanup (Tasks #12-14)
**Deliverables**:
- ✅ Old files removed
- ✅ E2E tests comprehensive
- ✅ Grafana plugin built
- ✅ Documentation complete

**Exit Criteria**: Production-ready system

---

## Status Tracking

### Overall Progress: 0% Complete (0/14 tasks)

**🔴 Critical** (0/4):
- [ ] Task #1: Refactor anomaly-detection
- [ ] Task #2: Create enrichment-service
- [ ] Task #3: Create correlation-service
- [ ] Task #4: Update incident-api V3 endpoints

**🟠 High** (0/3):
- [ ] Task #5: Create llm-enricher service
- [ ] Task #6: Add Ollama to docker-compose
- [ ] Task #7: Add Qdrant to docker-compose

**🟡 Medium** (0/4):
- [ ] Task #8: Update docker-compose.yml
- [ ] Task #9: Add VMAlert configuration
- [ ] Task #10: Add tracking_id at Vector
- [ ] Task #11: Update services to StructuredLogger

**🟢 Low** (0/3):
- [ ] Task #12: Cleanup old files
- [ ] Task #13: Create E2E tests
- [ ] Task #14: Build Grafana plugin

---

## Issue Lifecycle

### Status History
| Date | Status | Notes | Updated By |
|------|--------|-------|------------|
| 2025-10-03 | Open | Issue created from PR #156 review | Lead Engineer |

### Time Tracking
- **Estimated Total Time**: 32.5-37.5 hours
- **Time Spent**: 0 hours
- **Remaining**: 32.5-37.5 hours

---

## Additional Notes

### Key Success Factors
1. **Incremental Development**: Build and test one service at a time
2. **Early Integration**: Test service interactions immediately
3. **SLO Focus**: Continuously validate performance targets
4. **Documentation**: Update as you build, not after
5. **Team Collaboration**: Daily standups to track progress

### Post-Implementation Tasks
- Production deployment planning
- Performance tuning based on real traffic
- User training on Grafana Operations Console
- Incident response runbook creation
- Continuous monitoring setup

### Future Enhancements (Post-v1.0)
- Multi-model LLM support (beyond phi3:mini)
- Advanced RAG with fine-tuned embeddings
- Predictive analytics and forecasting
- Automated remediation execution
- Fleet-wide analytics and insights

---

**Issue Owner**: TBD (assign to implementation team)  
**Target Completion**: 4 weeks from assignment  
**Review Cadence**: Weekly progress reviews  
**Escalation Path**: Product Owner → Lead Engineer → CTO

---

## Appendix: Quick Reference

### Repository Structure (Post-Implementation)
```
AIOps-NAAS/
├── aiops_core/              # ✅ V3 models (PR #156)
├── services/
│   ├── anomaly-detection/   # ⚠️  Needs refactor
│   ├── enrichment-service/  # ❌ To be created
│   ├── correlation-service/ # ❌ To be created
│   ├── llm-enricher/        # ❌ To be created
│   └── incident-api/        # ⚠️  Needs V3 endpoints
├── tests/v3/                # ❌ To be created
├── vmalert/                 # ❌ To be created
├── docker-compose.yml       # ⚠️  Needs V3 services
├── vector/vector.toml       # ⚠️  Needs tracking_id
└── docs/                    # ✅ Updated in PR #156
```

### Key Commands
```bash
# Start full stack
docker-compose up -d

# Run V3 tests
pytest tests/v3/ -v

# Check Fast Path latency
curl http://localhost:8081/api/v3/stats | jq '.fast_path_latency_p99'

# Trace a request
curl http://localhost:8081/api/v3/trace/{tracking_id}

# Monitor SLOs
curl http://localhost:8880/api/v1/alerts
```

### Contact Information
- **Technical Questions**: Lead Engineer
- **Product Questions**: Product Owner
- **Deployment Questions**: DevOps Team
- **Documentation**: Technical Writer

---

**END OF ISSUE**

**Status**: ⚠️ OPEN - AWAITING ASSIGNMENT  
**Next Action**: Assign to implementation team and begin Phase 1
