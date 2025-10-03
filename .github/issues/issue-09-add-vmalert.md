## Task
Configure VMAlert for SLO monitoring.

## Implementation

1. **Create** `vmalert/alerts.yml`:
```yaml
groups:
  - name: fast_path_slo
    rules:
      - alert: FastPathLatencyHigh
        expr: histogram_quantile(0.99, aiops_fast_path_latency) > 0.1
        
  - name: insight_path_slo
    rules:
      - alert: InsightPathLatencyHigh
        expr: histogram_quantile(0.99, aiops_insight_path_latency) > 5.0
```

2. **Add to docker-compose.yml**:
```yaml
vmalert:
  image: victoriametrics/vmalert
  command: ['-rule=/etc/vmalert/alerts.yml']
  ports: ["8880:8880"]
```

## Acceptance Criteria
- [ ] VMAlert in docker-compose
- [ ] Alert rules defined
- [ ] UI at http://localhost:8880

**Effort**: 2h | **Priority**: Medium | **Dependencies**: #8
