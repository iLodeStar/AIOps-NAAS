# AIOps Core - Shared Library v3.0

Shared Python package for AIOps-NAAS Version 3 architecture. Provides data contracts, Pydantic models, and utilities used across all services.

## Features

- **Pydantic V2 Models**: Type-safe data contracts with validation
- **Structured Logging**: Request tracking with tracking_id propagation
- **Compact Message Format**: Efficient NATS messaging with short field names
- **End-to-End Tracing**: tracking_id preserved across all services
- **Error Propagation**: Real error messages maintained from start to end

## Installation

```bash
# From aiops_core directory
pip install -e .

# Or from requirements.txt
-e ./aiops_core
```

## Usage

### Data Models

```python
from aiops_core import AnomalyDetected, Severity, Domain

anomaly = AnomalyDetected(
    tracking_id="req-20250102-123456-abc123",
    ship_id="viking-star",
    domain=Domain.COMMS,
    anomaly_type="link_degradation",
    score=0.85,
    detector="threshold",
    service="vsat-modem",
)

# Serialize to JSON for NATS
json_bytes = anomaly.model_dump_json().encode()
```

### Structured Logging

```python
from aiops_core import get_logger, tracked_operation

# Create logger with tracking context
logger = get_logger(__name__, tracking_id="req-123")

# Log with automatic tracking_id
logger.info("Processing event", service="comms", score=0.85)
# Output: Processing event | tracking_id=req-123 service=comms score=0.85

# Track operations with timing
with tracked_operation(logger, "enrich_anomaly", service="comms"):
    enrich_data()
# Automatically logs start, duration, and errors
```

### Utilities

```python
from aiops_core import (
    generate_tracking_id,
    compute_suppress_key,
    compute_correlation_keys,
    extract_error_message,
)

# Generate unique tracking ID
tracking_id = generate_tracking_id(prefix="req")
# Returns: req-20250102-103045-a1b2c3d4

# Compute suppression key for dedup
suppress_key = compute_suppress_key(
    incident_type="link_degradation",
    device_id="vsat-001",
    service="modem",
    ship_id="viking-star"
)
# Returns: link_degradation:viking-star:vsat-001:modem

# Compute correlation keys for grouping
corr_keys = compute_correlation_keys(
    incident_type="link_degradation",
    device_id="vsat-001",
    service="modem",
    ship_id="viking-star",
    domain="comms"
)
# Returns: [
#   "link_degradation:viking-star",
#   "comms:viking-star",
#   "modem:viking-star",
#   "vsat-001:viking-star",
#   "link_degradation:modem:viking-star"
# ]
```

## Data Models

### Message Flow

```
LogMessage → AnomalyDetected → AnomalyEnriched → IncidentCreated
                                                      ↓
                                           EnrichmentRequest
                                                      ↓
                                           EnrichmentCompleted
```

### Key Models

- **BaseMessage**: Common fields (schema_version, tracking_id, ts, ship_id)
- **LogMessage**: Raw logs from ingestion
- **AnomalyDetected**: Detected anomalies with score
- **AnomalyEnriched**: Anomalies with historical context
- **IncidentCreated**: Correlated incidents with evidence
- **EnrichmentRequest**: LLM enrichment request
- **EnrichmentCompleted**: LLM enrichment result
- **AuditEvent**: Audit trail for actions
- **StatsSnapshot**: Statistics for monitoring

## Field Naming Convention

To minimize NATS message size:
- Use short field names: `ts` (timestamp), `msg` (message), `meta` (metadata)
- Avoid redundant prefixes
- Use enums for categorical values
- Optional fields use `Optional[T]` with `None` default

## Schema Versioning

All messages include `schema_version` field (default "3.0"). Services validate versions at boundaries to detect mismatches.

## Error Handling

```python
from aiops_core import extract_error_message

try:
    risky_operation()
except Exception as e:
    error_msg = extract_error_message(e, include_traceback=True)
    logger.error("Operation failed", error=e)
    # Error message propagated to incident for future analysis
```

## Testing

```bash
# Run tests
pytest

# Type checking
mypy aiops_core
```

## Development

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run type checking
mypy aiops_core

# Run tests with coverage
pytest --cov=aiops_core tests/
```

## License

Apache 2.0
