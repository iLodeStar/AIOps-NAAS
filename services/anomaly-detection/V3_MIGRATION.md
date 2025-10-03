# Anomaly Detection Service - V3 Refactoring

## Overview
This service has been refactored to use V3 Pydantic models from `aiops_core`, implementing proper tracking_id propagation and structured logging.

## V3 Changes Summary

### 1. Model Integration
The service now uses V3 Pydantic models from `aiops_core`:

```python
from aiops_core.models import AnomalyDetected, LogMessage, Domain
from aiops_core.utils import StructuredLogger, generate_tracking_id
```

#### AnomalyDetected Model
All anomaly events are published using the V3 `AnomalyDetected` model:

```python
anomaly = AnomalyDetected(
    tracking_id=tracking_id,
    ts=datetime.now(),
    ship_id=ship_id,
    domain=Domain.SYSTEM,
    anomaly_type="log_pattern",
    metric_name="log_anomaly",
    metric_value=1.0,
    threshold=0.7,
    score=0.85,
    detector="log_pattern_detector",
    service=service,
    device_id=device_id,
    raw_msg=message,
    meta={...}
)
```

### 2. Tracking ID Propagation
Every anomaly detection flow now preserves `tracking_id` end-to-end:

1. **Incoming Messages**: Extract `tracking_id` from log data or generate new one
2. **Logger Context**: Set tracking_id on StructuredLogger for all subsequent logs
3. **Anomaly Events**: Include tracking_id in all AnomalyDetected events
4. **Publishing**: tracking_id propagated through NATS to downstream services

```python
# Extract or generate tracking_id
tracking_id = log_data.get('tracking_id') or generate_tracking_id()

# Set on logger for context
logger.set_tracking_id(tracking_id)

# Include in anomaly event
anomaly = AnomalyDetected(tracking_id=tracking_id, ...)
```

### 3. StructuredLogger Integration
All logging now uses `StructuredLogger` with automatic tracking_id context:

```python
# Old style (replaced)
logger.info(f"Processing log: tracking_id={tracking_id}")

# New V3 style
logger.info("Processing log", level=log_level, severity=anomaly_severity)
# Output: "Processing log | tracking_id=req-123 level=ERROR severity=high"
```

Benefits:
- Automatic tracking_id inclusion in all logs
- Structured key=value format for easy parsing
- Error information automatically captured
- Context can be added for specific operations

### 4. API Changes

#### New Methods
- `publish_anomaly_v3(anomaly: AnomalyDetected)` - Publishes V3 AnomalyDetected events
- Enhanced all methods to use StructuredLogger

#### Updated Methods
- `process_anomalous_log()` - Now creates V3 AnomalyDetected directly
- `process_metrics()` - Uses V3 models for all anomaly events
- All helper methods updated to use StructuredLogger

#### Backward Compatibility
- Legacy `publish_anomaly()` method still available (converts to V3 internally)
- `AnomalyEvent` dataclass has `to_v3_model()` conversion method

## Testing

### Running Tests
```bash
cd services/anomaly-detection
pip install -r requirements.txt
python3 -m pytest test_anomaly_service_v3.py -v
```

### Test Coverage
- ✅ Tracking ID generation and format
- ✅ AnomalyEvent to V3 model conversion
- ✅ process_anomalous_log with tracking_id propagation
- ✅ V3 model publishing to NATS
- ✅ ship_id and device_id extraction
- ✅ Anomaly score calculation
- ✅ Normal operational message filtering
- ✅ INFO log skipping
- ✅ StructuredLogger tracking_id context
- ✅ Health check endpoint

All 12 tests pass ✅

## Migration Guide

### For Downstream Services
If you consume anomaly events from this service:

1. **Message Format**: Anomaly events are now published as V3 `AnomalyDetected` models
2. **Tracking ID**: Every event includes a `tracking_id` field for end-to-end tracing
3. **Domain Field**: Events include a `domain` field (SYSTEM, NET, APP, etc.)
4. **Serialization**: Events are serialized using Pydantic's `model_dump_json()`

Example consumption:
```python
from aiops_core.models import AnomalyDetected
import json

# Parse received message
data = json.loads(msg.data.decode())
anomaly = AnomalyDetected(**data)

# Access fields
print(f"Tracking ID: {anomaly.tracking_id}")
print(f"Ship: {anomaly.ship_id}")
print(f"Score: {anomaly.score}")
```

### For Service Operators

**Dependencies**: The service now requires `aiops_core` to be installed:
```bash
pip install -e ../../aiops_core
```

**Configuration**: No configuration changes required - all changes are internal

**Logs**: Log format is now structured with tracking_id automatically included

## Health Check

The health check endpoint remains unchanged:

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "healthy": true,
  "vm_connected": true,
  "nats_connected": true,
  "clickhouse_connected": true,
  "registry_connected": true
}
```

## Architecture

### Data Flow
```
1. Anomalous Log Received (NATS: logs.anomalous)
   ↓
2. Extract/Generate tracking_id
   ↓
3. Set tracking_id on StructuredLogger
   ↓
4. Extract ship_id, device_id from log data
   ↓
5. Calculate anomaly score
   ↓
6. Create V3 AnomalyDetected event
   ↓
7. Publish to NATS (anomaly.detected)
   ↓
8. tracking_id propagated to downstream services
```

### Metrics Flow
```
1. Query VictoriaMetrics
   ↓
2. Generate tracking_id for batch
   ↓
3. Run anomaly detection algorithms
   ↓
4. For each anomaly:
   a. Extract ship_id from labels
   b. Create V3 AnomalyDetected event
   c. Include tracking_id
   d. Publish to NATS
```

## Performance

V3 changes have minimal performance impact:
- Pydantic v2 uses Rust for fast validation
- Structured logging adds <1ms per log call
- Model serialization is optimized
- No additional database queries

## Troubleshooting

### Import Errors
If you get `ModuleNotFoundError: No module named 'aiops_core'`:
```bash
cd /path/to/AIOps-NAAS
pip install -e aiops_core
```

### Test Failures
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Tracking ID Not Propagating
Check that:
1. Incoming messages include `tracking_id` field OR
2. Service is generating new tracking_ids (check logs for `req-*` format)
3. StructuredLogger is being used (check log format includes `tracking_id=`)

## Future Enhancements

Potential V3 improvements:
- [ ] Add LogMessage input validation
- [ ] Implement correlation key generation
- [ ] Add metric-based domain classification
- [ ] Enhance context propagation with additional metadata
- [ ] Add distributed tracing integration

## References

- [V3 Data Contracts](../../aiops_core/aiops_core/models.py)
- [V3 Utilities](../../aiops_core/aiops_core/utils.py)
- [Issue #67: V3 Refactoring](https://github.com/iLodeStar/AIOps-NAAS/issues/67)
