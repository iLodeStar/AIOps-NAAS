## Objective
Update all Python services to use StructuredLogger from aiops_core for consistent structured logging.

## Affected Services
- services/anomaly-detection/
- services/incident-api/
- services/enrichment-service/
- services/correlation-service/
- services/llm-enricher/
- All other Python services

## Acceptance Criteria
- [ ] All services use StructuredLogger
- [ ] Legacy logging.getLogger removed
- [ ] All log statements include tracking_id
- [ ] JSON log format validated
- [ ] Grafana dashboards can parse structured logs

## Dependencies
- Issue #1 (StructuredLogger pattern established)

**Estimated Effort**: 3 hours  
**Sprint**: 3 (Week 3)  
**Priority**: Medium
