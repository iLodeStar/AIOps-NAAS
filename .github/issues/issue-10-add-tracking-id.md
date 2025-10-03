## Task
Configure Vector to generate tracking_id for all logs.

## Changes to `vector/vector.toml`

```toml
[transforms.add_tracking_id]
type = "remap"
inputs = ["syslog"]
source = '''
  .tracking_id = uuid_v4()
  .ingestion_timestamp = now()
'''

[sinks.to_clickhouse]
inputs = ["add_tracking_id"]  # Changed from ["syslog"]

[sinks.to_nats_anomaly]
inputs = ["add_tracking_id"]  # Changed from ["syslog"]
```

## Acceptance Criteria
- [ ] tracking_id generated (UUIDv4)
- [ ] ingestion_timestamp added
- [ ] ClickHouse stores tracking_id
- [ ] NATS messages include tracking_id

**Effort**: 30m | **Priority**: Medium | **Dependencies**: None
