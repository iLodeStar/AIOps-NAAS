-- Migration script to add vendor/device support to existing logs.raw table
-- This is backward-compatible and can be run on existing deployments

-- Add vendor/device type columns if they don't exist
ALTER TABLE logs.raw 
ADD COLUMN IF NOT EXISTS vendor LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS device_type LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS cruise_segment LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS facility LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS severity LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS category LowCardinality(String) DEFAULT '',
ADD COLUMN IF NOT EXISTS event_id String DEFAULT '',
ADD COLUMN IF NOT EXISTS ip_address IPv4 DEFAULT toIPv4('0.0.0.0'),
ADD COLUMN IF NOT EXISTS ingestion_time DateTime DEFAULT now();

-- Update the ORDER BY key to include vendor and device_type for better performance
-- Note: This is a heavy operation and should be done during maintenance window
-- ALTER TABLE logs.raw MODIFY ORDER BY (timestamp, vendor, device_type, source, level);

-- Create an index on vendor and device_type for faster queries
-- ALTER TABLE logs.raw ADD INDEX IF NOT EXISTS idx_vendor_device (vendor, device_type) TYPE bloom_filter(0.01) GRANULARITY 8192;

-- Create a view for vendor statistics
CREATE VIEW IF NOT EXISTS logs.vendor_summary AS
SELECT 
    toStartOfHour(timestamp) as hour,
    vendor,
    device_type,
    cruise_segment,
    source,
    level,
    count() as log_count,
    uniq(host) as unique_hosts,
    uniq(service) as unique_services,
    countIf(level = 'ERROR') as error_count,
    countIf(level = 'WARN') as warning_count
FROM logs.raw 
WHERE vendor != ''
GROUP BY hour, vendor, device_type, cruise_segment, source, level
ORDER BY hour DESC, log_count DESC;