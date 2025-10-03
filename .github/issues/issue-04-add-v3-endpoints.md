## Task
Add V3 endpoints to `services/incident-api/incident_api.py`.

## New Endpoints

1. **Stats API**:
```python
@app.get("/api/v3/stats")
async def get_stats(time_range: str = "1h"):
    # Return: incidents by severity/status/category
    # Processing metrics (fast/insight path)
    # SLO compliance (latency percentiles)
```

2. **Trace API**:
```python
@app.get("/api/v3/trace/{tracking_id}")
async def trace_request(tracking_id: str):
    # Return: end-to-end trace with latency breakdown
```

3. **Incident CRUD**:
```python
@app.post("/api/v3/incidents")
async def create_incident(incident: Incident):
    # Accept V3 Incident model

@app.get("/api/v3/incidents/{incident_id}")
async def get_incident(incident_id: str):
    # Return V3 Incident model
```

## Acceptance Criteria
- [ ] `/api/v3/stats` returns categorized counts
- [ ] `/api/v3/trace/{tracking_id}` returns full trace
- [ ] All endpoints use V3 models
- [ ] Unit tests pass

**Effort**: 2-3h | **Priority**: Critical | **Dependencies**: #3
