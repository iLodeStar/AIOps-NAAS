## Task
Create E2E test suite for V3 pipelines.

## Test Files

```
tests/v3/
├── test_fast_path_e2e.py    # Log → Anomaly → Enrich → Correlate
├── test_insight_path_e2e.py  # Incident → LLM → Enhanced
└── test_api_endpoints.py     # V3 API tests
```

## Fast Path Test
```python
@pytest.mark.asyncio
async def test_fast_path_e2e():
    tracking_id = send_test_log(...)
    anomaly = await wait_for("anomaly.detected", tracking_id)
    enriched = await wait_for("anomaly.enriched", tracking_id)
    incident = await wait_for("incidents.created", tracking_id)
    assert latency < 100  # ms
```

## Acceptance Criteria
- [ ] Fast Path test validates pipeline
- [ ] Insight Path test validates LLM
- [ ] SLO assertions (100ms, 5s)
- [ ] All tests pass
- [ ] Coverage >80%

**Effort**: 4h | **Priority**: Low | **Dependencies**: #1-11
