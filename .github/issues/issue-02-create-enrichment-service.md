## Objective
Create new enrichment-service for Fast Path L1 enrichment with ClickHouse context lookups.

## Service Purpose
Subscribe to `anomaly.detected` NATS topic, enrich with historical context, publish to `anomaly.enriched`.

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

## Reference
See [V3_IMPLEMENTATION_GITHUB_ISSUES.md](../../V3_IMPLEMENTATION_GITHUB_ISSUES.md) for full context.

**Estimated Effort**: 4-5 hours  
**Sprint**: 1 (Week 1 - Critical Services)  
**Priority**: Critical
