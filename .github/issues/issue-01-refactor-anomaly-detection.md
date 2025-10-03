## Task
Refactor `services/anomaly-detection/anomaly_service.py` to use V3 Pydantic models from `aiops_core`.

## Changes Required

1. **Update imports**:
```python
from aiops_core.models import AnomalyDetected, LogEntry
from aiops_core.utils import StructuredLogger
```

2. **Refactor service logic**:
- Accept `LogEntry` V3 model as input
- Output `AnomalyDetected` V3 model
- Preserve `tracking_id` throughout
- Replace all logging with `StructuredLogger`

3. **Update tests**:
- Test with V3 models
- Validate tracking_id propagation

## Acceptance Criteria
- [ ] Uses `AnomalyDetected` from aiops_core
- [ ] tracking_id preserved
- [ ] StructuredLogger for all logs
- [ ] Unit tests pass
- [ ] Health check passes

**Effort**: 2-3h | **Priority**: Critical | **Dependencies**: None
