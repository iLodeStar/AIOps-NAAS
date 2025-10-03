## Objective
Refactor the anomaly-detection service to use V3 Pydantic models from `aiops_core` package.

## Current State
- Uses old dataclass models
- No tracking_id support
- No StructuredLogger

## Required Changes

### 1. Update imports
```python
from aiops_core.models import AnomalyDetected, LogEntry
from aiops_core.utils import StructuredLogger
```

### 2. Update anomaly detection logic
- Accept `LogEntry` V3 model as input
- Generate `AnomalyDetected` V3 model as output
- Preserve `tracking_id` throughout processing
- Use `StructuredLogger` for all logging

### 3. Update unit tests
- Test with V3 models
- Validate tracking_id propagation

## Files to Modify
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

## Reference
See [V3_IMPLEMENTATION_GITHUB_ISSUES.md](../../V3_IMPLEMENTATION_GITHUB_ISSUES.md) for full context.

**Estimated Effort**: 2-3 hours  
**Sprint**: 1 (Week 1 - Critical Services)  
**Priority**: Critical
