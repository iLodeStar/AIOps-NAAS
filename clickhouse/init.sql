-- ClickHouse initialization script for AIOps NAAS
-- Create database and tables for log ingestion

CREATE DATABASE IF NOT EXISTS logs;

-- Raw logs table for JSON log ingestion via Vector
CREATE TABLE IF NOT EXISTS logs.raw (
    timestamp DateTime64(3) DEFAULT now64(),
    level LowCardinality(String),
    message String,
    source LowCardinality(String),
    host LowCardinality(String),
    service LowCardinality(String),
    raw_log String,
    labels Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, source, level)
TTL timestamp + INTERVAL 30 DAY
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

-- Insert some sample data for testing
INSERT INTO logs.raw (timestamp, level, message, source, host, service, raw_log, labels) VALUES
    (now() - INTERVAL 1 HOUR, 'INFO', 'Application started successfully', 'app', 'ship-01', 'api-server', '{"timestamp":"2024-01-01T12:00:00Z","level":"INFO","message":"Application started successfully"}', {'environment': 'dev', 'version': '1.0.0'}),
    (now() - INTERVAL 30 MINUTE, 'WARN', 'High memory usage detected', 'system', 'ship-01', 'monitor', '{"timestamp":"2024-01-01T12:30:00Z","level":"WARN","message":"High memory usage detected"}', {'threshold': '80%', 'current': '85%'}),
    (now() - INTERVAL 15 MINUTE, 'ERROR', 'Database connection failed', 'app', 'ship-01', 'api-server', '{"timestamp":"2024-01-01T12:45:00Z","level":"ERROR","message":"Database connection failed"}', {'retry_count': '3', 'error_code': 'CONNECTION_TIMEOUT'}),
    (now() - INTERVAL 5 MINUTE, 'INFO', 'Backup completed successfully', 'system', 'ship-01', 'backup-service', '{"timestamp":"2024-01-01T12:55:00Z","level":"INFO","message":"Backup completed successfully"}', {'size_mb': '1024', 'duration_sec': '45'});