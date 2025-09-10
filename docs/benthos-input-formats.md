# Benthos Input Formats and Upstream Sources

## Overview

This document describes the comprehensive input format support and upstream source compatibility for the Benthos stream processor in the AIOps NAAS platform. The system is designed to handle diverse log formats from various maritime devices, operating systems, and applications.

## Supported Input Sources

### 1. NATS Message Bus Sources

#### Basic Anomaly Detection
- **Subject**: `anomaly.detected`
- **Format**: JSON
- **Required Fields**: `ship_id`, `metric_name`, `anomaly_score`, `timestamp`
- **Example**:
```json
{
  "ship_id": "ship-01",
  "metric_name": "cpu_usage", 
  "anomaly_score": 0.85,
  "timestamp": "2025-01-15T10:30:00Z",
  "labels": {
    "instance": "ship-01",
    "job": "node-exporter"
  }
}
```

#### Enhanced Anomaly Detection
- **Subject**: `anomaly.detected.enriched`
- **Format**: JSON with enrichment context
- **Additional Fields**: `correlation_level`, `enrichment_context`, `maritime_context`
- **Example**:
```json
{
  "ship_id": "vessel-alpha",
  "metric_name": "satellite_signal_strength",
  "anomaly_score": 0.92,
  "correlation_level": "level_1_enriched",
  "enrichment_context": {
    "weather_impact": "rain_fade",
    "system_load": "high"
  },
  "maritime_context": {
    "sea_state": 4,
    "position": {"lat": 45.5, "lon": -125.3}
  }
}
```

#### Application Log Anomalies
- **Subject**: `logs.anomalous`
- **Format**: Structured application logs
- **Required Fields**: `application`, `logger_name`, `level`, `message`
- **Example**:
```json
{
  "ship_id": "ship-02",
  "application": "navigation-system",
  "logger_name": "com.maritime.nav.gps",
  "level": "ERROR",
  "message": "GPS signal lost - switching to backup",
  "trace_id": "abc123",
  "span_id": "def456",
  "thread": "gps-monitor"
}
```

#### SNMP Network Anomalies
- **Subject**: `telemetry.network.anomaly`
- **Format**: SNMP device telemetry
- **Required Fields**: `device_type`, `device_ip`, `metric_name`
- **Example**:
```json
{
  "ship_id": "ship-03",
  "host": "192.168.1.10",
  "device_type": "switch",
  "metric_name": "interface_utilization",
  "labels": {
    "interface": "eth0",
    "device_type": "managed_switch"
  },
  "value": 95.5
}
```

### 2. File-based Log Sources

#### Syslog Format (RFC3164/RFC5424)
```
Jan 15 10:30:00 ship-01 navigation[1234]: GPS coordinates updated
<14>Jan 15 10:30:00 vessel-alpha kernel: Out of memory: Kill process 1234
```

#### JSON Lines
```json
{"timestamp":"2025-01-15T10:30:00Z","host":"ship-01","service":"engine","level":"WARN","message":"Engine temperature high"}
{"timestamp":"2025-01-15T10:30:01Z","host":"ship-01","service":"radar","level":"INFO","message":"Radar sweep completed"}
```

#### Plain Text Logs
```
2025-01-15 10:30:00 [ERROR] Database connection failed
2025-01-15 10:30:01 [INFO] Retrying connection attempt 2/5
```

#### CSV Format
```csv
timestamp,host,service,level,message
2025-01-15T10:30:00Z,ship-01,gps,ERROR,Signal acquisition failed
2025-01-15T10:30:01Z,ship-01,compass,WARN,Magnetic deviation detected
```

## Input Validation and Standardization

### Automatic Format Detection

The Benthos configuration includes automatic format detection and standardization:

1. **JSON Detection**: Attempts to parse input as JSON first
2. **Syslog Pattern Matching**: Recognizes standard syslog formats
3. **Plain Text Fallback**: Wraps unstructured text in standard format
4. **CSV Processing**: Detects CSV headers and maps to standard fields

### Field Mapping and Defaults

| Input Field | Standard Field | Default Value | Notes |
|-------------|----------------|---------------|-------|
| `ship_id` | `ship_id` | `"unknown_ship"` | Primary identifier |
| `host` | `ship_id` | `"unknown_ship"` | Alternative identifier |
| `instance` | `ship_id` | `"unknown_ship"` | From labels.instance |
| `severity` | `severity` | `"info"` | Standardized severity |
| `level` | `severity` | `"info"` | Log level mapping |
| `metric_name` | `metric_name` | `"unknown_metric"` | Metric identifier |
| `source` | `event_source` | `"unknown_source"` | Event source type |

### Severity Mapping

| Input Level | Standard Severity | Priority |
|-------------|------------------|----------|
| `FATAL`, `ERROR` | `critical` | 4 |
| `WARN`, `WARNING` | `warning` | 2 |
| `INFO`, `INFORMATION` | `info` | 1 |
| `DEBUG`, `TRACE` | `debug` | 1 |

## Error Handling

### Null Value Protection

The configuration includes comprehensive null handling:

```yaml
# Safe ship_id extraction
root.ship_id = if this.ship_id != null && this.ship_id != "" { 
  this.ship_id 
} else if this.host != null && this.host != "" { 
  this.host 
} else { 
  "unknown_ship" 
}
```

### Cache Key Safety

All cache operations use safe key generation:

```yaml
key: "${! json(\"ship_id\") + \"_\" + json(\"event_source\") + \"_\" + json(\"metric_name\") }"
drop_on_err: true  # Prevents errors from missing cache keys
```

### Missing Field Handling

- **Required Fields**: Automatically populated with safe defaults
- **Optional Fields**: Gracefully handled with null checks
- **Invalid Data**: Wrapped in standardized error format

## Device and OS Compatibility

### Supported Operating Systems

1. **Linux** (Ubuntu, CentOS, RHEL, Alpine)
   - Syslog via rsyslog/syslog-ng
   - Systemd journal integration
   - Application logs via file watching

2. **Windows** (Server, IoT Core)
   - Windows Event Log integration
   - IIS logs
   - Application event logs

3. **Maritime-specific OS**
   - VxWorks (real-time systems)
   - QNX (navigation systems)
   - Custom embedded Linux

### Device Types

1. **Navigation Equipment**
   - GPS/GNSS systems
   - Radar units
   - AIS transponders
   - Electronic chart systems

2. **Communication Systems**
   - Satellite communication terminals
   - VHF/UHF radios
   - Network switches/routers

3. **Engine/Propulsion**
   - Engine management systems
   - Fuel monitoring
   - Emission control systems

4. **Safety Systems**
   - Fire detection/suppression
   - Emergency shutdown systems
   - Life safety equipment

## Log Format Examples by Source

### Ubuntu VM Logs (Issue Context)

```bash
# Standard syslog format
Jan 15 10:30:00 ubuntu-vm systemd[1]: Started application.service

# JSON application logs
{"timestamp":"2025-01-15T10:30:00.123Z","hostname":"ubuntu-vm","application":"app","level":"ERROR","message":"Connection timeout","pid":1234}

# Docker container logs
2025-01-15T10:30:00.123456789Z [INFO] Container started successfully

# Nginx access logs
192.168.1.100 - - [15/Jan/2025:10:30:00 +0000] "GET /api/health HTTP/1.1" 200 85
```

### Network Device Logs

```bash
# Cisco switch
%LINK-3-UPDOWN: Interface GigabitEthernet1/1, changed state to up

# SNMP trap format
SNMPv2-MIB::sysUpTime.0 = Timeticks: (123456) 0:20:34.56
SNMPv2-MIB::snmpTrapOID.0 = OID: SNMPv2-SMI::enterprises.9.9.41.1.2.1.2
```

## Configuration Debugging

### Debug Information

Each processed event includes debug metadata:

```json
{
  "debug_input": {
    "raw_content": "original input",
    "content_type": "string",
    "timestamp": "2025-01-15T10:30:00Z",
    "metadata": {}
  },
  "input_metadata": {
    "original_format": "string",
    "standardized": true,
    "validation_timestamp": "2025-01-15T10:30:00Z",
    "processing_stage": "input_validation"
  }
}
```

### Common Issues and Solutions

1. **"Key does not exist" errors**
   - **Cause**: Cache key references non-existent entries
   - **Solution**: Added `drop_on_err: true` to cache operations

2. **"Cannot compare types null" errors**
   - **Cause**: Null values in severity priority calculations
   - **Solution**: Comprehensive null checking before comparisons

3. **"Cannot add types null and string" errors**
   - **Cause**: String concatenation with null values
   - **Solution**: Safe field extraction with defaults

## Testing Input Formats

### Manual Testing

```bash
# Test syslog format
echo "<14>$(date '+%b %d %H:%M:%S') $(hostname) test-service: ERROR Database connection failed" | nc localhost 1515

# Test JSON format
echo '{"ship_id":"test-ship","metric_name":"cpu_usage","anomaly_score":0.8}' | nats pub anomaly.detected

# Test plain text
echo "$(date) ERROR: System overload detected" | nc localhost 1515
```

### Automated Validation

The repository includes test scripts for validating input format handling:

- `test_benthos_null_fixes.py`: Tests null value scenarios
- `test_benthos_fixes_simple.py`: Tests basic format processing
- `validate_benthos_fix.sh`: Comprehensive validation script

## Best Practices

1. **Always include ship_id**: Either directly or via host/instance fields
2. **Use structured logging**: JSON format preferred for applications
3. **Include timestamps**: ISO 8601 format recommended
4. **Provide context**: Include service/application identifiers
5. **Use standard log levels**: ERROR, WARN, INFO, DEBUG
6. **Monitor Benthos metrics**: Check processing rates and error counts

## Conclusion

The Benthos configuration is designed to handle the diverse range of log formats and upstream sources encountered in maritime environments. The robust error handling and automatic format standardization ensure reliable processing regardless of the input source or format variations.