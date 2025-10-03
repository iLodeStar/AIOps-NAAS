## Task
Create `services/enrichment-service/` for Fast Path L1 enrichment.

## Implementation

1. **Service structure**:
```
services/enrichment-service/
├── enrichment_service.py  # Main service
├── clickhouse_queries.py  # Context queries
├── Dockerfile
└── requirements.txt
```

2. **Core logic**:
```python
from aiops_core.models import AnomalyDetected, EnrichedAnomaly
from aiops_core.utils import StructuredLogger

# Subscribe: anomaly.detected
# Enrich with ClickHouse:
#   - Device metadata
#   - Historical failure rates (24h)
#   - Similar anomalies (7d)
# Publish: anomaly.enriched
```

3. **ClickHouse queries**:
- Device metadata by device_id
- Anomaly count (24h window)
- Similar anomalies (7d window)

## Acceptance Criteria
- [ ] Subscribes to `anomaly.detected`
- [ ] ClickHouse queries work
- [ ] Publishes `EnrichedAnomaly` to `anomaly.enriched`
- [ ] Latency <30ms (p99)
- [ ] `/health` and `/metrics` endpoints
- [ ] Error fallback handling

**Effort**: 4-5h | **Priority**: Critical | **Dependencies**: #1
