-- ClickHouse initialization script for AIOps NAAS
CREATE DATABASE IF NOT EXISTS logs;

-- Raw logs & metrics table for Vector JSON ingestion
CREATE TABLE IF NOT EXISTS logs.raw (
    timestamp DateTime64(3) DEFAULT now64(),
    level LowCardinality(String),
    message String,
    source LowCardinality(String),
    host LowCardinality(String),
    service LowCardinality(String),
    raw_log String,
    labels Map(String, String),
    -- Metrics fields
    name String,
    namespace String,
    tags Map(String, String),
    kind String,
    counter_value Float64,
    gauge_value Float64,
    -- Network vendor/device extensions (backward-compatible)
    vendor LowCardinality(String) DEFAULT '',
    device_type LowCardinality(String) DEFAULT '',
    cruise_segment LowCardinality(String) DEFAULT '',
    facility LowCardinality(String) DEFAULT '',
    severity LowCardinality(String) DEFAULT '',
    category LowCardinality(String) DEFAULT '',
    event_id String DEFAULT '',
    ip_address IPv4 DEFAULT toIPv4('0.0.0.0'),
    ingestion_time DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, vendor, device_type, source, level)
TTL timestamp + INTERVAL 30 DAY
SETTINGS index_granularity = 8192;

-- Incidents table for correlated events and incident management
CREATE TABLE IF NOT EXISTS logs.incidents (
    incident_id String,
    event_type LowCardinality(String),
    incident_type LowCardinality(String),
    incident_severity LowCardinality(String),
    ship_id LowCardinality(String),
    service LowCardinality(String),
    status LowCardinality(String),
    acknowledged UInt8 DEFAULT 0,
    created_at DateTime64(3),
    updated_at DateTime64(3),
    correlation_id String,
    processing_timestamp DateTime64(3),
    metric_name String,
    metric_value Float64,
    anomaly_score Float64,
    detector_name LowCardinality(String),
    correlated_events String, -- JSON array
    timeline String, -- JSON array 
    suggested_runbooks Array(String),
    metadata String -- JSON object
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(created_at)
ORDER BY (created_at, incident_id, ship_id)
TTL created_at + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Audit table for runbook executions and manual actions
CREATE TABLE IF NOT EXISTS logs.audit (
    audit_id String,
    timestamp DateTime64(3) DEFAULT now64(),
    event_type LowCardinality(String),
    user_id String,
    ship_id LowCardinality(String),
    incident_id String,
    runbook_id String,
    action LowCardinality(String),
    status LowCardinality(String),
    details String, -- JSON object
    policy_decisions String, -- OPA policy results JSON
    execution_time_ms UInt32,
    error_message String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, event_type, ship_id)
TTL timestamp + INTERVAL 365 DAY -- Keep audit logs for 1 year
SETTINGS index_granularity = 8192;

-- Create a view for easier log analysis
CREATE VIEW IF NOT EXISTS logs.summary AS
SELECT 
    toStartOfHour(timestamp) as hour,
    source,
    level,
    count() as count,
    uniq(host) as unique_hosts,
    uniq(service) as unique_services
FROM logs.raw 
GROUP BY hour, source, level
ORDER BY hour DESC;

-- Create incident summary view
CREATE VIEW IF NOT EXISTS logs.incident_summary AS
SELECT
    toStartOfHour(created_at) as hour,
    incident_type,
    incident_severity,
    ship_id,
    count() as incident_count,
    countIf(status = 'open') as open_incidents,
    countIf(acknowledged = 1) as acknowledged_incidents,
    avg(anomaly_score) as avg_anomaly_score
FROM logs.incidents
GROUP BY hour, incident_type, incident_severity, ship_id
ORDER BY hour DESC;

-- Insert some sample data for testing
INSERT INTO logs.raw (timestamp, level, message, source, host, service, raw_log, labels) VALUES
    (now() - INTERVAL 1 HOUR, 'INFO', 'Application started successfully', 'app', 'ship-01', 'api-server', '{"timestamp":"2024-01-01T12:00:00Z","level":"INFO","message":"Application started successfully"}', {'environment': 'dev', 'version': '1.0.0'}),
    (now() - INTERVAL 30 MINUTE, 'WARN', 'High memory usage detected', 'system', 'ship-01', 'monitor', '{"timestamp":"2024-01-01T12:30:00Z","level":"WARN","message":"High memory usage detected"}', {'threshold': '80%', 'current': '85%'}),
    (now() - INTERVAL 15 MINUTE, 'ERROR', 'Database connection failed', 'app', 'ship-01', 'api-server', '{"timestamp":"2024-01-01T12:45:00Z","level":"ERROR","message":"Database connection failed"}', {'retry_count': '3', 'error_code': 'CONNECTION_TIMEOUT'}),
    (now() - INTERVAL 5 MINUTE, 'INFO', 'Backup completed successfully', 'system', 'ship-01', 'backup-service', '{"timestamp":"2024-01-01T12:55:00Z","level":"INFO","message":"Backup completed successfully"}', {'size_mb': '1024', 'duration_sec': '45'});
