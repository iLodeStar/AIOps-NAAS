## Objective
Add V3 API endpoints to incident-api for statistics and request tracing.

## New Endpoints Required

### 1. Statistics API
```python
@app.get("/api/v3/stats")
async def get_stats(time_range: str = "1h"):
    # Return incident statistics by severity, status, category
    # Processing metrics (fast path, insight path)
    # SLO compliance (latency percentiles)
```

### 2. Trace API
```python
@app.get("/api/v3/trace/{tracking_id}")
async def trace_request(tracking_id: str):
    # End-to-end trace with latency breakdown
```

### 3. Update Incident CRUD
```python
@app.post("/api/v3/incidents")
async def create_incident(incident: Incident):
    # Accept V3 Incident model

@app.get("/api/v3/incidents/{incident_id}")
async def get_incident(incident_id: str):
    # Return V3 Incident model
```

## Files to Modify
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

**Estimated Effort**: 2-3 hours  
**Sprint**: 1 (Week 1)  
**Priority**: Critical
