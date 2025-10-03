## Objective
Configure VMAlert for monitoring Fast Path (<100ms) and Insight Path (<5s) SLO compliance.

## Required Configuration
- Fast Path SLO alerts (latency, error rate)
- Insight Path SLO alerts (latency, service health)
- VMAlert service in docker-compose

## Acceptance Criteria
- [ ] VMAlert service configured in docker-compose
- [ ] Fast Path SLO alerts defined
- [ ] Insight Path SLO alerts defined
- [ ] Alert rules validated
- [ ] VMAlert UI accessible at http://localhost:8880

## Dependencies
- Issue #8 (services must be running to monitor)

**Estimated Effort**: 2 hours  
**Sprint**: 3 (Week 3)  
**Priority**: Medium
