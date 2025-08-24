# Vendor Configuration Guide

This guide explains how to configure vendor-specific parameters for network devices, satellite RF equipment, applications, and external data sources in the AIOps NAAS platform.

## Overview

The platform supports configurable integration with various vendor equipment and systems through:
- YAML configuration files for vendor models, data rates, and protocols
- Environment variables for secrets and deployment-specific settings
- No secrets stored in the repository

## Configuration Files

### Primary Configuration

**File:** `configs/vendor-integrations.yaml`

Copy the example template and customize for your environment:
```bash
cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml
```

**Environment Variables:** `.env`

Copy the example and set your specific values:
```bash
cp .env.example .env
```

> ⚠️ **Important**: Never commit secrets to version control. The `.env` file is gitignored.

## Network Device Configuration

Configure protocols, ports, and polling parameters for network equipment:

```yaml
network_devices:
  protocols:
    syslog:
      enabled: true
      port: 514
      format: "rfc3164"  # rfc3164, rfc5424
    snmp:
      enabled: true
      port: 161
      version: "2c"      # v1, v2c, v3
      community: "public"  # Override with SNMP_COMMUNITY env var
      timeout: 10
      retries: 3
    netflow:
      enabled: true
      port: 2055
      version: 9         # 5, 9, 10 (IPFIX)
  polling:
    interval_seconds: 30
    batch_size: 100
    concurrent_workers: 4
```

### Supported Protocols

- **Syslog**: RFC3164 (legacy) and RFC5424 (structured) formats
- **SNMP**: v1, v2c, v3 with configurable communities and timeouts
- **NetFlow/sFlow/IPFIX**: Flow-based network monitoring
- **Custom polling**: Configurable intervals and worker threads

## Satellite RF Equipment Configuration

Configure vendor-specific satellite modems and RF equipment:

```yaml
satellite_rf:
  vendors:
    - name: "vsat_vendor_1" 
      model: "VSAT-2000"
      api_endpoint: "${VSAT1_API_ENDPOINT}"
      authentication:
        type: "basic"      # basic, token, cert
        username: "${VSAT1_USERNAME}"
        password: "${VSAT1_PASSWORD}"
      kpi_mapping:
        snr_db: "signal.snr"
        es_no_db: "signal.es_no"
        ber: "quality.bit_error_rate"
        signal_strength_dbm: "signal.strength"
      thresholds:
        snr_warning: 12.0
        snr_critical: 8.0
```

### KPI Mapping

Map vendor-specific API fields to standardized KPIs:

| Standard KPI | Description | Units |
|--------------|-------------|-------|
| `snr_db` | Signal-to-Noise Ratio | dB |
| `es_no_db` | Energy per Symbol to Noise | dB |
| `ber` | Bit Error Rate | ratio |
| `signal_strength_dbm` | Received Signal Strength | dBm |
| `rain_fade_margin_db` | Rain Fade Margin | dB |
| `frequency_offset_hz` | Frequency Offset | Hz |
| `elevation_angle_deg` | Antenna Elevation | degrees |
| `azimuth_angle_deg` | Antenna Azimuth | degrees |

### Authentication Methods

- **Basic**: HTTP Basic Authentication with username/password
- **Token**: Bearer token or API key authentication  
- **Certificate**: Client certificate authentication

### SNMP Configuration

For SNMP-based satellite equipment:

```yaml
satellite_rf:
  vendors:
    - name: "vsat_vendor_2"
      model: "SAT-Link-Pro"
      snmp_config:
        host: "${VSAT2_SNMP_HOST}"
        port: 161
        community: "${VSAT2_SNMP_COMMUNITY}"
        mibs:
          - "SAT-LINK-MIB"
          - "VSAT-PERFORMANCE-MIB"
      kpi_mapping:
        snr_db: "1.3.6.1.4.1.12345.1.1.1"  # SNMP OID
        ber: "1.3.6.1.4.1.12345.1.1.2"
```

## Application Performance Monitoring

Configure application health checks and SLA monitoring:

```yaml
applications:
  probes:
    - name: "web_services"
      endpoints:
        - url: "${APP1_URL}/health"
          method: "GET"
          timeout_seconds: 5
          expected_status: 200
      sla:
        response_time_ms: 1000
        availability_percent: 99.9
        error_rate_percent: 0.1
  exporters:
    prometheus:
      enabled: true
      port: 9090
      scrape_interval: "15s"
```

### SLA Configuration

Define Service Level Agreements for monitoring:

- **response_time_ms**: Maximum acceptable response time
- **availability_percent**: Minimum uptime requirement  
- **error_rate_percent**: Maximum allowable error rate

## External Context Data Sources

Configure weather, navigation, and scheduling data sources:

```yaml
external_context:
  weather:
    provider: "openweather"
    api_base_url: "${WEATHER_API_URL}"
    api_key: "${WEATHER_API_KEY}"
    update_interval_minutes: 30
  
  ship_navigation:
    nmea:
      enabled: true
      sources:
        - type: "serial"
          device: "/dev/ttyUSB0" 
          baud_rate: 4800
        - type: "tcp"
          host: "${NMEA_TCP_HOST}"
          port: 2000
```

### Weather Integration

Supported weather providers:
- **OpenWeather**: Global weather data API
- **Custom APIs**: Configurable endpoints for proprietary weather systems

Required parameters:
- Temperature, humidity, precipitation
- Wind speed and direction
- Visibility and cloud cover

### Navigation Data (NMEA)

NMEA 0183 integration for ship position and movement:
- **Serial**: Direct RS-232/USB connection to GPS receiver
- **TCP**: Network-based NMEA data streams
- **AIS**: Automatic Identification System integration

## Environment Variables

Set sensitive configuration in `.env` file:

```bash
# Database Configuration
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_secure_password

# VSAT Vendor 1
VSAT1_API_ENDPOINT=http://vsat1.example.com:8090
VSAT1_USERNAME=api_user  
VSAT1_PASSWORD=secure_password

# Weather API
WEATHER_API_KEY=your_openweather_api_key

# External Systems
SCHEDULE_API_KEY=your_schedule_api_key
```

### Security Best Practices

1. **Never commit secrets**: Use environment variables for all sensitive data
2. **Rotate credentials**: Regularly update API keys and passwords
3. **Principle of least privilege**: Use read-only accounts where possible
4. **Secure transport**: Always use HTTPS/TLS for API communication

## Data Simulation Configuration

For testing and development, configure realistic data simulation:

```yaml
simulation:
  enabled: false  # Set to true for development
  base_distributions:
    modem:
      snr_db:
        mean: 15.0
        std_dev: 3.0
        min_value: 5.0
        max_value: 25.0
    weather:
      precipitation_mm_hr:
        mean: 0.5
        std_dev: 2.0
  anomalies:
    probability: 0.1
    types:
      - "rain_fade"
      - "equipment_degradation"
      - "interference"
```

### Simulation Parameters

- **base_distributions**: Normal operation statistical distributions
- **anomalies**: Random anomaly generation configuration
- **publishing**: NATS subject configuration and timing

## Configuration Validation

Validate your configuration before deployment:

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('configs/vendor-integrations.yaml'))"

# Test with data simulator
python3 tools/data-simulator/data_simulator.py --config configs/vendor-integrations.yaml --duration 10

# Run configuration validation
pytest tests/config_validation.py -v
```

## Troubleshooting

### Common Issues

**YAML Syntax Errors**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```
- Check indentation (use spaces, not tabs)
- Verify quotes around string values
- Ensure proper YAML structure

**Environment Variable Not Found**
```
KeyError: 'VSAT1_API_KEY'
```
- Ensure `.env` file exists and is loaded
- Check variable name spelling
- Verify environment variable is exported

**API Connection Failures**
```
requests.exceptions.ConnectionError: HTTPSConnectionPool
```
- Verify endpoint URLs are correct
- Check network connectivity
- Validate authentication credentials
- Review firewall settings

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Set debug environment
export LOG_LEVEL=DEBUG

# Run with verbose logging
python3 tools/data-simulator/data_simulator.py --log-level DEBUG
```

### Health Checks

Monitor vendor integration health:

```bash
# Check service health endpoints
curl http://localhost:8082/health  # Link Health Service
curl http://localhost:8083/health  # Remediation Service

# Check NATS connectivity
curl http://localhost:8222/connz   # NATS connections
```

## Next Steps

After configuring vendor integrations:

1. **Test Configuration**: Run the data simulator to validate settings
2. **Deploy Services**: Use `docker compose up -d` to start the platform  
3. **Monitor Integration**: Check service logs and health endpoints
4. **Run Soak Test**: Execute `bash scripts/run_soak_test.sh` to validate end-to-end operation
5. **Set up Monitoring**: Configure alerts for vendor integration failures

For deployment instructions, see [Local and Non-Production Deployment Guide](../deployment/local-and-nonprod.md).

For testing procedures, see [Test Plan](../testing/test-plan.md).