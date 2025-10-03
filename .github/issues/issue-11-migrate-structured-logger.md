## Task
Migrate all services to use StructuredLogger.

## Migration Pattern

**Before**:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Processing anomaly")
```

**After**:
```python
from aiops_core.utils import StructuredLogger
logger = StructuredLogger.get_logger(__name__, "service-name", "3.0.0")
logger.info("processing_anomaly", tracking_id=tracking_id)
```

## Services to Update
- services/anomaly-detection/
- services/incident-api/
- services/enrichment-service/
- services/correlation-service/
- services/llm-enricher/

## Acceptance Criteria
- [ ] All services use StructuredLogger
- [ ] Legacy logging removed
- [ ] All logs include tracking_id
- [ ] JSON format validated

**Effort**: 3h | **Priority**: Medium | **Dependencies**: #1
