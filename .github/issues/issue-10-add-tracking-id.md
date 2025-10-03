## Objective
Configure Vector to generate UUIDv4 tracking_id for all incoming logs at ingestion point.

## File to Modify
`vector/vector.toml`

## Acceptance Criteria
- [ ] tracking_id generated for all incoming logs
- [ ] UUIDv4 format validated
- [ ] ingestion_timestamp added
- [ ] ClickHouse stores tracking_id
- [ ] NATS messages include tracking_id
- [ ] No performance degradation (latency <5ms added)

## Dependencies
- None (independent configuration change)

**Estimated Effort**: 30 minutes  
**Sprint**: 3 (Week 3)  
**Priority**: Medium
