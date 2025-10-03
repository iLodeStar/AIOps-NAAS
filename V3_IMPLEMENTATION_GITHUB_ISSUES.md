# V3 Implementation - GitHub Issues Breakdown

**Epic**: V3 Architecture Implementation Completion  
**Epic ID**: ISSUE-20251003-142429-V3-COMPLETION  
**Total Issues**: 14  
**Total Effort**: 32.5-37.5 hours (4 weeks)

---

## 📋 Issue Execution Order

### Sprint 1 - Week 1: Critical Services (Foundation)
**Goal**: Fast Path Pipeline Operational (<100ms)

```
Issue #1 → Issue #2 → Issue #3 → Issue #4
  ↓         ↓         ↓         ↓
(Can start in parallel after dependencies are clear)
```

**Dependencies**:
- Issue #2 depends on Issue #1 (needs AnomalyDetected model)
- Issue #3 depends on Issue #2 (needs EnrichedAnomaly)
- Issue #4 can run in parallel with #3

---

### Sprint 2 - Week 2: AI/ML Integration
**Goal**: Insight Path Pipeline Operational (<5s)

```
Issue #5 depends on: Issues #1-4 complete
Issue #6 → Issue #7 (can run in parallel)
  ↓         ↓
Issue #5 (needs both Ollama and Qdrant)
```

**Dependencies**:
- Issue #6 and #7 have no dependencies (infrastructure)
- Issue #5 depends on #6 and #7 (needs Ollama + Qdrant services)

---

### Sprint 3 - Week 3: Infrastructure & Observability
**Goal**: Production-Ready Infrastructure

```
Issue #10 (can start immediately)
  ↓
Issue #8 depends on: Issues #1-7 complete
  ↓
Issue #9 (depends on services running)
  ↓
Issue #11 (refactor all services)
```

**Dependencies**:
- Issue #10 is independent (Vector config)
- Issue #8 depends on all new services being created
- Issue #9 depends on Issue #8 (services must be running)
- Issue #11 can start after Issue #1 (incremental refactor)

---

### Sprint 4 - Week 4: Quality & Polish
**Goal**: Production-Ready Codebase

```
Issue #12 (can start anytime, low priority)
Issue #13 depends on: Issues #1-11 complete
Issue #14 (can start anytime after foundation)
```

**Dependencies**:
- Issue #12 is independent (cleanup)
- Issue #13 depends on full pipeline working
- Issue #14 is mostly independent (frontend)

---

## 📊 Detailed Issue Breakdown

### Issue #1: Refactor anomaly-detection Service to V3 Models

**Title**: `[V3] Refactor anomaly-detection service to use V3 Pydantic models`

**Labels**: `priority: critical`, `type: refactoring`, `sprint: 1`, `v3-architecture`

**Estimated Effort**: 2-3 hours

**Description**:
```markdown
## Objective
Refactor the anomaly-detection service to use V3 Pydantic models from `aiops_core` package.

## Current State
- Uses old dataclass models
- No tracking_id support
- No StructuredLogger

## Required Changes
1. **Update imports**:
   ```python
   from aiops_core.models import AnomalyDetected, LogEntry
   from aiops_core.utils import StructuredLogger
   ```

2. **Update anomaly detection logic**:
   - Accept `LogEntry` V3 model as input
   - Generate `AnomalyDetected` V3 model as output
   - Preserve `tracking_id` throughout processing
   - Use `StructuredLogger` for all logging

3. **Update unit tests**:
   - Test with V3 models
   - Validate tracking_id propagation

## File to Modify
- `services/anomaly-detection/anomaly_service.py`
- `services/anomaly-detection/test_anomaly_service.py` (if exists)

## Acceptance Criteria
- [ ] Service uses `AnomalyDetected` from aiops_core
- [ ] tracking_id preserved from log entry
- [ ] All logging uses StructuredLogger
- [ ] Unit tests updated for V3 models
- [ ] Service health check passes
- [ ] No breaking changes to NATS message format

## Dependencies
- None (foundation task)

## Blocks
- Issue #2 (enrichment-service needs AnomalyDetected model)
```

---

### Issue #2: Create enrichment-service for Fast Path L1 Enrichment

**Title**: `[V3] Create enrichment-service for Fast Path context enrichment`

**Labels**: `priority: critical`, `type: feature`, `sprint: 1`, `v3-architecture`, `new-service`

**Estimated Effort**: 4-5 hours

**Description**:
```markdown
## Objective
Create new enrichment-service for Fast Path L1 enrichment with ClickHouse context lookups.

## Service Purpose
Subscribe to anomaly.detected NATS topic, enrich with historical context, publish to anomaly.enriched.

## Directory Structure
```
services/enrichment-service/
├── Dockerfile
├── requirements.txt
├── enrichment_service.py
├── clickhouse_queries.py
├── config.yaml
└── tests/
```

## Core Functionality
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

## ClickHouse Queries Needed
- Device metadata lookup by device_id
- Historical anomaly count (24h window)
- Similar anomaly search (7d window)
- Service health metrics

## Acceptance Criteria
- [ ] Service subscribes to `anomaly.detected` NATS topic
- [ ] ClickHouse context queries functional
- [ ] Publishes `EnrichedAnomaly` to `anomaly.enriched`
- [ ] Latency <30ms (99th percentile)
- [ ] Error handling with fallback to basic enrichment
- [ ] Health endpoint at `/health`
- [ ] Metrics endpoint at `/metrics`
- [ ] Unit tests with >90% coverage

## Dependencies
- Issue #1 (needs AnomalyDetected model definition)

## Blocks
- Issue #3 (correlation-service needs EnrichedAnomaly)
```

---

### Issue #3: Create correlation-service for Incident Formation

**Title**: `[V3] Create correlation-service for incident formation and deduplication`

**Labels**: `priority: critical`, `type: feature`, `sprint: 1`, `v3-architecture`, `new-service`

**Estimated Effort**: 4-5 hours

**Description**:
```markdown
## Objective
Create correlation-service for Fast Path incident formation with deduplication and time-windowing.

## Service Purpose
Subscribe to anomaly.enriched, apply correlation logic, form incidents, publish to incidents.created.

## Directory Structure
```
services/correlation-service/
├── Dockerfile
├── requirements.txt
├── correlation_service.py
├── deduplication.py
├── windowing.py
├── config.yaml
└── tests/
```

## Core Functionality
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

## Correlation Algorithms
- Time-based windowing (configurable: 1m-30m)
- Fingerprint-based deduplication
- Related anomaly grouping
- Suppression rules from policy system

## Acceptance Criteria
- [ ] Service subscribes to `anomaly.enriched` NATS topic
- [ ] Deduplication logic prevents duplicate incidents
- [ ] Time-windowing clusters related anomalies
- [ ] Publishes `Incident` to `incidents.created`
- [ ] Latency <50ms (99th percentile)
- [ ] Suppression rules applied from policy
- [ ] Health endpoint at `/health`
- [ ] Metrics endpoint at `/metrics`
- [ ] Unit tests with >90% coverage

## Dependencies
- Issue #2 (needs EnrichedAnomaly model)

## Blocks
- Issue #4 (incident-api needs Incident model flowing)
```

---

### Issue #4: Add V3 Endpoints to incident-api

**Title**: `[V3] Add V3 API endpoints to incident-api (stats, trace)`

**Labels**: `priority: critical`, `type: feature`, `sprint: 1`, `v3-architecture`, `api`

**Estimated Effort**: 2-3 hours

**Description**:
```markdown
## Objective
Add V3 API endpoints to incident-api for statistics and request tracing.

## Current State
- Basic CRUD operations only
- No V3 endpoints
- No stats or tracing APIs

## New Endpoints Required

### 1. Statistics API
```python
@app.get("/api/v3/stats")
async def get_stats(time_range: str = "1h"):
    """
    Return incident statistics:
    - Total incidents (by severity, status, category)
    - Processing metrics (fast path, insight path)
    - SLO compliance (latency percentiles)
    """
```

### 2. Trace API
```python
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
```

### 3. Update Incident CRUD
```python
@app.post("/api/v3/incidents")
async def create_incident(incident: Incident):
    """Accept V3 Incident model"""

@app.get("/api/v3/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Return V3 Incident model"""
```

## File to Modify
- `services/incident-api/incident_api.py`

## Acceptance Criteria
- [ ] `/api/v3/stats` returns categorized incident counts
- [ ] `/api/v3/trace/{tracking_id}` returns full pipeline trace
- [ ] All endpoints use V3 Pydantic models
- [ ] ClickHouse queries optimized for stats
- [ ] API documentation updated (OpenAPI/Swagger)
- [ ] Unit tests for new endpoints
- [ ] Integration tests pass

## Dependencies
- Issue #3 (needs Incident model flowing through pipeline)

## Blocks
- None (completes Sprint 1 critical path)
```

---

### Issue #5: Create llm-enricher Service for AI Insights

**Title**: `[V3] Create llm-enricher service for LLM/RAG-based insights`

**Labels**: `priority: high`, `type: feature`, `sprint: 2`, `v3-architecture`, `ai-ml`, `new-service`

**Estimated Effort**: 4-5 hours

**Description**:
```markdown
## Objective
Create llm-enricher service for Insight Path AI enrichment using Ollama LLM and Qdrant RAG.

## Service Purpose
Subscribe to incidents.created, generate AI insights, retrieve similar incidents, publish enhanced incidents.

## Directory Structure
```
services/llm-enricher/
├── Dockerfile
├── requirements.txt
├── llm_service.py
├── ollama_client.py
├── qdrant_rag.py
├── llm_cache.py
├── config.yaml
└── tests/
```

## Core Functionality
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

## Integration Requirements
- **Ollama**: phi3:mini model for LLM inference
- **Qdrant**: Vector search for similar incidents
- **ClickHouse**: LLM response caching
- **Timeout Handling**: 300ms max, graceful degradation

## Acceptance Criteria
- [ ] Service subscribes to `incidents.created` NATS topic
- [ ] Ollama integration functional with phi3:mini model
- [ ] Qdrant RAG retrieves similar incidents
- [ ] LLM responses cached in ClickHouse
- [ ] Publishes `EnrichedIncident` to `incidents.enriched`
- [ ] Timeout fallback (graceful degradation)
- [ ] Latency <300ms target (99th percentile)
- [ ] Health endpoint at `/health`
- [ ] Metrics for LLM latency and cache hit rate
- [ ] Unit tests with mocked LLM/RAG

## Dependencies
- Issue #6 (Ollama service must be running)
- Issue #7 (Qdrant service must be running)
- Issues #1-4 (Fast Path must be operational)

## Blocks
- None (completes Sprint 2)
```

---

### Issue #6: Add Ollama Service to docker-compose

**Title**: `[V3] Add Ollama LLM service to docker-compose.yml`

**Labels**: `priority: high`, `type: infrastructure`, `sprint: 2`, `v3-architecture`, `ai-ml`

**Estimated Effort**: 1 hour

**Description**:
```markdown
## Objective
Add Ollama LLM service to docker-compose.yml and initialize with phi3:mini model.

## Current State
`docker-compose.v3.yml` exists but not integrated into main compose file.

## Required Changes

### 1. Add to docker-compose.yml
```yaml
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

### 2. Create Initialization Script
```bash
# scripts/init_ollama.sh
#!/bin/bash
until curl -f http://localhost:11434/api/tags; do
  sleep 2
done
docker exec aiops-ollama ollama pull phi3:mini
echo "Ollama initialized with phi3:mini model"
```

## Acceptance Criteria
- [ ] Ollama service added to docker-compose.yml
- [ ] phi3:mini model pulled and ready
- [ ] Health check passing
- [ ] API accessible at http://localhost:11434
- [ ] Initialization script created and tested
- [ ] Documentation updated with Ollama usage

## Dependencies
- None (infrastructure component)

## Blocks
- Issue #5 (llm-enricher needs Ollama)
```

---

### Issue #7: Add Qdrant Vector Database to docker-compose

**Title**: `[V3] Add Qdrant vector database to docker-compose.yml`

**Labels**: `priority: high`, `type: infrastructure`, `sprint: 2`, `v3-architecture`, `ai-ml`

**Estimated Effort**: 1 hour

**Description**:
```markdown
## Objective
Add Qdrant vector database to docker-compose.yml and initialize incidents collection.

## Required Changes

### 1. Add to docker-compose.yml
```yaml
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

### 2. Create Collection Initialization
```python
# scripts/init_qdrant.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(host="localhost", port=6333)

client.create_collection(
    collection_name="incidents",
    vectors_config=VectorParams(
        size=384,  # all-MiniLM-L6-v2 embedding size
        distance=Distance.COSINE
    )
)
```

## Acceptance Criteria
- [ ] Qdrant service added to docker-compose.yml
- [ ] Collection "incidents" created
- [ ] Health check passing
- [ ] HTTP API accessible at http://localhost:6333
- [ ] gRPC API accessible at localhost:6334
- [ ] Initialization script created and tested
- [ ] Documentation updated with Qdrant usage

## Dependencies
- None (infrastructure component)

## Blocks
- Issue #5 (llm-enricher needs Qdrant RAG)
```

---

### Issue #8: Update docker-compose.yml with All V3 Services

**Title**: `[V3] Add all V3 services to main docker-compose.yml`

**Labels**: `priority: medium`, `type: infrastructure`, `sprint: 3`, `v3-architecture`

**Estimated Effort**: 2 hours

**Description**:
```markdown
## Objective
Add all V3 services to main docker-compose.yml with proper dependencies and configuration.

## Services to Add

### 1. enrichment-service
```yaml
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
```

### 2. correlation-service
```yaml
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
```

### 3. llm-enricher
```yaml
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
```

### 4. Merge Ollama and Qdrant from docker-compose.v3.yml

## Dependency Graph
```
Vector → anomaly-detection → enrichment-service → correlation-service → incident-api
                                                         ↓
                                                   llm-enricher (async)
                                                         ↓
                                                   incident-api (enriched)
```

## Acceptance Criteria
- [ ] All V3 services added to docker-compose.yml
- [ ] Dependencies correctly configured
- [ ] Environment variables set
- [ ] Health checks defined for all services
- [ ] `docker-compose up` starts all services successfully
- [ ] Service startup order correct
- [ ] No port conflicts
- [ ] All services can communicate

## Dependencies
- Issues #1, #2, #3, #4 (services must exist)
- Issues #6, #7 (Ollama and Qdrant services)

## Blocks
- Issue #9 (VMAlert needs services running)
```

---

### Issue #9: Add VMAlert Configuration for SLO Monitoring

**Title**: `[V3] Configure VMAlert for Fast Path and Insight Path SLO monitoring`

**Labels**: `priority: medium`, `type: infrastructure`, `sprint: 3`, `v3-architecture`, `observability`

**Estimated Effort**: 2 hours

**Description**:
```markdown
## Objective
Configure VMAlert for monitoring Fast Path (<100ms) and Insight Path (<5s) SLO compliance.

## Directory Structure
```
vmalert/
├── alerts.yml
└── README.md
```

## Alert Rules

### Fast Path SLO Alerts
```yaml
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

      - alert: FastPathErrorRate
        expr: |
          sum(rate(aiops_fast_path_errors_total[5m])) 
          / sum(rate(aiops_fast_path_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: high
```

### Insight Path SLO Alerts
```yaml
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
```

## VMAlert Docker Service
```yaml
services:
  vmalert:
    image: victoriametrics/vmalert:latest
    container_name: aiops-vmalert
    command:
      - '-rule=/etc/vmalert/alerts.yml'
      - '-datasource.url=http://victoriametrics:8428'
    ports:
      - "8880:8880"
    volumes:
      - ./vmalert/alerts.yml:/etc/vmalert/alerts.yml:ro
    depends_on:
      - victoriametrics
```

## Acceptance Criteria
- [ ] VMAlert service configured in docker-compose
- [ ] Fast Path SLO alerts defined (latency, error rate)
- [ ] Insight Path SLO alerts defined (latency, service health)
- [ ] Alert rules validated
- [ ] VMAlert UI accessible at http://localhost:8880
- [ ] Alerts firing correctly when SLOs violated
- [ ] Documentation updated

## Dependencies
- Issue #8 (services must be running to monitor)

## Blocks
- None
```

---

### Issue #10: Add tracking_id Generation at Vector

**Title**: `[V3] Configure Vector to generate tracking_id for all logs`

**Labels**: `priority: medium`, `type: infrastructure`, `sprint: 3`, `v3-architecture`, `observability`

**Estimated Effort**: 30 minutes

**Description**:
```markdown
## Objective
Configure Vector to generate UUIDv4 tracking_id for all incoming logs at ingestion point.

## File to Modify
`vector/vector.toml`

## Required Changes
```toml
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

## Verification Query
```sql
-- ClickHouse query to verify tracking_id
SELECT tracking_id, COUNT(*) 
FROM logs.raw 
WHERE ingestion_timestamp > now() - INTERVAL 1 HOUR
GROUP BY tracking_id
LIMIT 10;
```

## Acceptance Criteria
- [ ] tracking_id generated for all incoming logs
- [ ] UUIDv4 format validated
- [ ] ingestion_timestamp added
- [ ] ClickHouse stores tracking_id
- [ ] NATS messages include tracking_id
- [ ] No performance degradation (latency <5ms added)
- [ ] E2E trace query works with tracking_id

## Dependencies
- None (independent configuration change)

## Blocks
- None (enhances observability)
```

---

### Issue #11: Migrate All Services to StructuredLogger

**Title**: `[V3] Migrate all services to use StructuredLogger from aiops_core`

**Labels**: `priority: medium`, `type: refactoring`, `sprint: 3`, `v3-architecture`, `observability`

**Estimated Effort**: 3 hours

**Description**:
```markdown
## Objective
Update all Python services to use StructuredLogger from aiops_core for consistent structured logging.

## Affected Services
- `services/anomaly-detection/`
- `services/incident-api/`
- `services/enrichment-service/` (new)
- `services/correlation-service/` (new)
- `services/llm-enricher/` (new)
- All other Python services in `services/`

## Migration Pattern
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
    service="service-name",
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

## Benefits
- Automatic tracking_id propagation
- Structured JSON output
- Correlation-friendly format
- Performance metrics
- Error categorization

## Acceptance Criteria
- [ ] All services use StructuredLogger
- [ ] Legacy logging.getLogger removed
- [ ] All log statements include tracking_id
- [ ] JSON log format validated
- [ ] ClickHouse logs table updated if needed
- [ ] Grafana dashboards can parse structured logs
- [ ] No breaking changes to log consumers

## Dependencies
- Issue #1 (StructuredLogger pattern established)

## Blocks
- None (improves observability)
```

---

### Issue #12: Cleanup Legacy Test and Documentation Files

**Title**: `[V3] Remove legacy test files and redundant documentation`

**Labels**: `priority: low`, `type: maintenance`, `sprint: 4`, `v3-architecture`, `cleanup`

**Estimated Effort**: 1 hour

**Description**:
```markdown
## Objective
Remove ~100 legacy test files and redundant documentation to clean up the repository.

## Files to Remove

### Old Test Files (~50 files)
```bash
rm test_benthos_*.py
rm test_integration*.py
rm test_issue_*.py
rm test_v0*.py
rm validate_*.py
rm demo_*.py
```

### Old Documentation (~40 files)
```bash
rm *_FIX_SUMMARY.md
rm *_ISSUE_REPORT*.md
rm INCIDENT_DATA_*.md
rm ONE_CLICK_*.md
rm CRITICAL_*.md
rm COMPLETE_*.md
```

## Preservation Strategy
- Move valid test scripts to `tests/legacy/` (for reference)
- Archive important summaries to `docs/legacy/`
- Update README.md references

## Files to Keep
- Current V3 implementation docs
- Active integration tests
- PR review documents (PR_156_*)
- ISSUE_TEMPLATE.md

## Acceptance Criteria
- [ ] 50+ test files removed from root
- [ ] 40+ summary files removed/archived
- [ ] Important files preserved in legacy folders
- [ ] README.md updated with new structure
- [ ] .gitignore updated if needed
- [ ] No broken links in documentation
- [ ] Git history preserved

## Dependencies
- None (independent cleanup)

## Blocks
- None
```

---

### Issue #13: Create End-to-End Test Suite for V3 Pipeline

**Title**: `[V3] Create comprehensive E2E test suite for Fast Path and Insight Path`

**Labels**: `priority: low`, `type: testing`, `sprint: 4`, `v3-architecture`, `e2e-tests`

**Estimated Effort**: 4 hours

**Description**:
```markdown
## Objective
Create comprehensive end-to-end test suite validating Fast Path and Insight Path pipelines.

## Test Structure
```
tests/v3/
├── __init__.py
├── test_fast_path_e2e.py
├── test_insight_path_e2e.py
├── test_api_endpoints.py
└── conftest.py
```

## Fast Path E2E Test
```python
@pytest.mark.asyncio
async def test_fast_path_end_to_end():
    """
    Test: Log → Anomaly → Enrich → Correlate → Incident
    Target latency: <100ms
    """
    start_time = datetime.now()
    
    # 1. Send test log
    tracking_id = send_test_log(...)
    
    # 2. Verify anomaly detected
    anomaly = await wait_for_nats_message("anomaly.detected", tracking_id)
    
    # 3. Verify enrichment
    enriched = await wait_for_nats_message("anomaly.enriched", tracking_id)
    
    # 4. Verify incident created
    incident = await wait_for_nats_message("incidents.created", tracking_id)
    
    # 5. Verify API
    api_incident = get_incident_by_tracking_id(tracking_id)
    
    # 6. Verify SLO
    latency_ms = (datetime.now() - start_time).total_seconds() * 1000
    assert latency_ms < 100
```

## Insight Path E2E Test
```python
@pytest.mark.asyncio
async def test_insight_path_end_to_end():
    """
    Test: Incident → LLM Enrichment → Enhanced Incident
    Target latency: <5s
    """
    # Test LLM enrichment flow
    # Verify AI insights generated
    # Verify RAG similar incidents
    # Verify latency SLO
```

## Acceptance Criteria
- [ ] Fast Path E2E test validates full pipeline
- [ ] Insight Path E2E test validates LLM enrichment
- [ ] SLO assertions in place (100ms, 5s)
- [ ] Tests run in CI/CD pipeline
- [ ] All tests passing
- [ ] Test coverage >80% for V3 code
- [ ] Performance benchmarks documented

## Dependencies
- Issues #1-11 (all services must be operational)

## Blocks
- None (validates completion)
```

---

### Issue #14: Build and Deploy Grafana Operations Console Plugin

**Title**: `[V3] Build Grafana plugin and create deployment package`

**Labels**: `priority: low`, `type: frontend`, `sprint: 4`, `v3-architecture`, `ui`

**Estimated Effort**: 2 hours

**Description**:
```markdown
## Objective
Build the Grafana Operations Console plugin and create production-ready deployment package.

## Directory
`grafana/plugins/aiops-ops-console/`

## Build Process
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

## Required npm Scripts
Add to `package.json`:
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

## Manual Testing Checklist
1. Copy plugin to Grafana plugins directory
2. Restart Grafana
3. Enable plugin in Grafana UI
4. Test each page:
   - Incidents dashboard (list, filter, detail view)
   - Approvals workflow (pending actions, approve/reject)
   - Actions history (executed remediations)
   - Policy viewer (current active policies)
5. Test API integration with backend

## Acceptance Criteria
- [ ] `npm install` completes without errors
- [ ] `npm run build` produces dist/ artifacts
- [ ] Plugin loads in Grafana without errors
- [ ] All 4 pages render correctly
- [ ] API calls to incident-api succeed
- [ ] UI matches design mockups
- [ ] No console errors
- [ ] Production build optimized
- [ ] Deployment documentation created

## Dependencies
- Issue #4 (needs incident-api V3 endpoints)

## Blocks
- None (frontend component)
```

---

## 🗓️ Sprint Planning Summary

### Sprint 1 - Week 1 (Critical Path)
- **Goal**: Fast Path Pipeline Operational
- **Issues**: #1, #2, #3, #4
- **Effort**: 12-16 hours
- **Exit Criteria**: Fast Path E2E test passing (<100ms)

### Sprint 2 - Week 2 (AI/ML)
- **Goal**: Insight Path Pipeline Operational
- **Issues**: #5, #6, #7
- **Effort**: 6-7 hours
- **Exit Criteria**: Insight Path E2E test passing (<5s)

### Sprint 3 - Week 3 (Infrastructure)
- **Goal**: Production-Ready Infrastructure
- **Issues**: #8, #9, #10, #11
- **Effort**: 7.5 hours
- **Exit Criteria**: Full observability operational

### Sprint 4 - Week 4 (Quality)
- **Goal**: Production-Ready Codebase
- **Issues**: #12, #13, #14
- **Effort**: 7 hours
- **Exit Criteria**: Production deployment ready

---

## 📊 Dependency Matrix

| Issue | Depends On | Blocks |
|-------|-----------|--------|
| #1 | None | #2, #11 |
| #2 | #1 | #3 |
| #3 | #2 | #4 |
| #4 | #3 | #13 |
| #5 | #6, #7, #1-4 | #13 |
| #6 | None | #5 |
| #7 | None | #5 |
| #8 | #1-7 | #9 |
| #9 | #8 | None |
| #10 | None | None |
| #11 | #1 | None |
| #12 | None | None |
| #13 | #1-11 | None |
| #14 | #4 | None |

---

## 🎯 Critical Path

```
#1 → #2 → #3 → #4 → #6,#7 (parallel) → #5 → #8 → #9 → #13
```

**Parallelizable**:
- #6 and #7 can run in parallel
- #10, #11, #12, #14 can start anytime

**Serialized (Critical)**:
- #1 → #2 → #3 → #4 (Fast Path foundation)
- #5 needs #6 and #7 complete (Insight Path)
- #8 needs all services (#1-7)
- #13 needs everything complete

---

## 📋 Labels to Create in GitHub

### Priority Labels
- `priority: critical` (red) - Must complete for v1.0
- `priority: high` (orange) - Important for full functionality
- `priority: medium` (yellow) - Infrastructure improvements
- `priority: low` (green) - Quality and polish

### Type Labels
- `type: feature` (blue) - New functionality
- `type: refactoring` (purple) - Code improvement
- `type: infrastructure` (gray) - DevOps/deployment
- `type: testing` (cyan) - Test suite
- `type: maintenance` (white) - Cleanup/housekeeping
- `type: frontend` (pink) - UI/UX work
- `type: api` (teal) - API endpoints

### Component Labels
- `v3-architecture` - V3 implementation work
- `new-service` - Creates new microservice
- `ai-ml` - AI/ML components
- `observability` - Monitoring/logging
- `e2e-tests` - End-to-end testing
- `ui` - User interface

### Sprint Labels
- `sprint: 1` - Week 1 work
- `sprint: 2` - Week 2 work
- `sprint: 3` - Week 3 work
- `sprint: 4` - Week 4 work

---

**Total Issues**: 14  
**Total Estimated Effort**: 32.5-37.5 hours  
**Duration**: 4 weeks (4 sprints)  
**Epic**: V3 Architecture Implementation Completion
