## Task
Create `services/correlation-service/` for incident formation with deduplication.

## Implementation

1. **Service structure**:
```
services/correlation-service/
├── correlation_service.py  # Main logic
├── deduplication.py       # Dedup logic
├── windowing.py           # Time windows
├── Dockerfile
└── requirements.txt
```

2. **Core logic**:
```python
from aiops_core.models import EnrichedAnomaly, Incident
from aiops_core.utils import StructuredLogger

# Subscribe: anomaly.enriched
# Correlation logic:
#   - Time-window clustering (5min default)
#   - Deduplication by signature
#   - Severity aggregation
# Form Incident
# Publish: incidents.created
```

3. **Algorithms**:
- Time-based windowing (1m-30m configurable)
- Fingerprint-based deduplication
- Suppression rules from policy

## Acceptance Criteria
- [ ] Subscribes to `anomaly.enriched`
- [ ] Deduplication works
- [ ] Time-windowing clusters anomalies
- [ ] Publishes `Incident` to `incidents.created`
- [ ] Latency <50ms (p99)
- [ ] `/health` and `/metrics` endpoints

**Effort**: 4-5h | **Priority**: Critical | **Dependencies**: #2
