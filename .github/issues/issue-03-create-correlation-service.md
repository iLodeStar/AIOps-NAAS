## Objective
Create correlation-service for Fast Path incident formation with deduplication and time-windowing.

## Service Purpose
Subscribe to `anomaly.enriched`, apply correlation logic, form incidents, publish to `incidents.created`.

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

## Reference
See [V3_IMPLEMENTATION_GITHUB_ISSUES.md](../../V3_IMPLEMENTATION_GITHUB_ISSUES.md) for full context.

**Estimated Effort**: 4-5 hours  
**Sprint**: 1 (Week 1 - Critical Services)  
**Priority**: Critical
