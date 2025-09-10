# Device Registry & Mapping Service

The Device Registry & Mapping Service is a core component of the AIOps NAAS platform that manages hostname → ship_id mappings and maintains a comprehensive device inventory. This service solves the critical issue where systems like Vector and SNMP report raw hostnames (like "ubuntu-vm-01") instead of meaningful ship identifiers.

## Overview

### Problem Solved

Previously, the platform had several issues with device identification:

- **Raw Hostname Problem**: Vector sends system hostnames ("ubuntu-vm-01", "debian-server") instead of ship IDs
- **SNMP IP Addresses**: Network devices identified only by IP addresses
- **Inconsistent Ship IDs**: No standardized ship identification across data sources
- **Missing Device Context**: No device type classification or fleet hierarchy
- **Hardcoded Fallbacks**: Services used hardcoded fallbacks like "ship-01"

### Solution

The Device Registry provides:

- **Centralized Mapping**: hostname → ship_id → device_type mappings
- **Auto-generated Device IDs**: Unique device identifiers (e.g., `dev_a1b2c3d4e5f6`)
- **Device Classification**: Navigation, engine, communication, safety, network, server, etc.
- **Fleet Hierarchy**: Ships → Systems → Devices organization
- **Interactive Registration**: User-friendly CLI for device registration
- **API Integration**: RESTful API for automated lookups and registrations

## Architecture

### Database Schema

```sql
-- Ships table
CREATE TABLE ships (
    ship_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    fleet_id TEXT,
    location TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Devices table  
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,           -- Auto-generated: dev_a1b2c3d4e5f6
    hostname TEXT UNIQUE NOT NULL,       -- ubuntu-vm-01, 192.168.1.100
    ship_id TEXT NOT NULL,               -- ship-aurora, msc-container-01
    device_type TEXT NOT NULL,           -- navigation, engine, network, server
    vendor TEXT,                         -- Dell, Cisco, Siemens
    model TEXT,                          -- PowerEdge R740, Catalyst 9300
    location TEXT,                       -- Bridge, Engine Room, Server Rack 1
    capabilities TEXT,                   -- JSON array of capabilities
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ship_id) REFERENCES ships (ship_id)
);

-- Hostname mappings for fast lookups
CREATE TABLE hostname_mappings (
    hostname TEXT PRIMARY KEY,           -- ubuntu-vm-01, 192.168.1.100  
    ship_id TEXT NOT NULL,               -- ship-aurora
    device_id TEXT NOT NULL,             -- dev_a1b2c3d4e5f6
    device_type TEXT NOT NULL,           -- server
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ship_id) REFERENCES ships (ship_id),
    FOREIGN KEY (device_id) REFERENCES devices (device_id)
);
```

### Service Components

1. **FastAPI Web Service** (`services/device-registry/app.py`)
   - RESTful API for device management
   - Health checks and monitoring endpoints
   - SQLite database with automatic schema initialization
   - Comprehensive error handling and validation

2. **Interactive CLI Script** (`scripts/register_device.py`)
   - User-friendly device registration wizard
   - Ship creation and management
   - Hostname lookup and validation
   - Registry statistics and device listing

3. **Benthos Integration** (`benthos/device-registry-integration.yaml`)
   - Automatic hostname → ship_id resolution
   - Fallback logic for offline scenarios
   - Performance monitoring and debug metadata

## API Endpoints

### Health Check
```bash
GET /health
```

### Ship Management
```bash
# Create a new ship
POST /ships
{
  "ship_id": "ship-aurora",
  "name": "MSC Aurora", 
  "fleet_id": "msc-fleet-01",
  "location": "Port of Singapore",
  "status": "active"
}

# List all ships
GET /ships
```

### Device Registration
```bash
# Register a new device
POST /devices/register  
{
  "hostname": "ubuntu-vm-01",
  "ship_id": "ship-aurora",
  "device_type": "server",
  "vendor": "Dell",
  "model": "PowerEdge R740", 
  "location": "Server Room"
}

# List devices (all or by ship)
GET /devices?ship_id=ship-aurora
```

### Hostname Lookup
```bash
# Lookup hostname mapping
GET /lookup/ubuntu-vm-01

# Response:
{
  "success": true,
  "hostname": "ubuntu-vm-01",
  "mapping": {
    "ship_id": "ship-aurora",
    "ship_name": "MSC Aurora",
    "device_id": "dev_a1b2c3d4e5f6", 
    "device_type": "server",
    "vendor": "Dell",
    "model": "PowerEdge R740",
    "location": "Server Room"
  }
}

# Update last seen timestamp
POST /lookup/ubuntu-vm-01/update-last-seen
```

### Statistics
```bash
# Get registry statistics
GET /stats

# Response:
{
  "total_ships": 3,
  "total_devices": 24,
  "device_types": {
    "navigation": 6,
    "engine": 4, 
    "network": 8,
    "server": 6
  },
  "ship_device_counts": {
    "ship-aurora": 12,
    "ship-pacific": 8,
    "ship-atlantic": 4
  }
}
```

## Device Type Categories

The service supports comprehensive device classification:

### Maritime-Specific Types
- **navigation**: GPS, radar, AIS, chart plotters, compass systems
- **communication**: VHF radios, satellite communication, intercom systems
- **engine**: Engine monitoring, propulsion systems, fuel management
- **safety**: Fire detection, emergency systems, life safety equipment

### IT Infrastructure Types  
- **network**: Switches, routers, wireless access points, firewalls
- **server**: Application servers, databases, file servers, virtualization hosts
- **workstation**: User workstations, terminals, laptops, tablets
- **security**: CCTV systems, access control, alarm systems

### IoT and Sensors
- **iot_sensor**: Temperature, humidity, pressure, vibration sensors
- **other**: Miscellaneous or custom device types

## Usage Examples

### Interactive Registration

The easiest way to register devices is using the interactive CLI:

```bash
# Start interactive registration wizard
python scripts/register_device.py

# Or connect to different registry URL
python scripts/register_device.py --registry-url http://device-registry:8081
```

The interactive script provides:
- 🚢 **Ship Registration Wizard**: Step-by-step ship creation
- 🖥️ **Device Registration Wizard**: Guided device registration with auto-completion
- 🔍 **Hostname Lookup**: Quick hostname resolution testing
- 📊 **Statistics Dashboard**: Registry overview and device counts
- 📋 **Device Listing**: Comprehensive device inventory browsing

### Command Line Registration

For automation and scripting:

```bash
# Create a ship
python scripts/register_device.py --ship-id "ship-aurora" --ship-name "MSC Aurora"

# Register a device
python scripts/register_device.py --hostname "ubuntu-vm-01" --ship-id "ship-aurora" --device-type "server"

# Lookup a hostname
python scripts/register_device.py --lookup "ubuntu-vm-01"

# Show statistics
python scripts/register_device.py --stats
```

### Integration Examples

#### Vector Integration
Update Vector configuration to query the device registry:

```yaml
[transforms.enrich_ship_id]
type = "lua"
inputs = ["parse_logs"]
source = '''
  function transform(event, emit)
    local hostname = event.log.host
    if hostname then
      local registry_url = "http://device-registry:8080/lookup/" .. hostname
      local result = http.request("GET", registry_url)
      if result.status == 200 then
        local mapping = json.decode(result.body).mapping
        event.log.ship_id = mapping.ship_id
        event.log.device_id = mapping.device_id
        event.log.device_type = mapping.device_type
      end
    end
    emit(event)
  end
'''
```

#### SNMP Integration
For network device collection:

```python
# In network-device-collector service
import requests

def resolve_device_info(ip_address):
    try:
        response = requests.get(f"http://device-registry:8080/lookup/{ip_address}")
        if response.status_code == 200:
            mapping = response.json()['mapping']
            return {
                'ship_id': mapping['ship_id'],
                'device_id': mapping['device_id'],
                'device_type': mapping['device_type']
            }
    except:
        pass
    
    # Fallback logic
    return {
        'ship_id': f"network-{ip_address.split('.')[2]}",
        'device_id': f"dev_{ip_address.replace('.', '_')}",
        'device_type': 'network'
    }
```

## Integration with Benthos

The Benthos pipeline automatically uses the Device Registry for hostname resolution:

### Automatic Ship ID Resolution

```yaml
# In benthos.yaml - Device Registry Integration processor
- mapping: |
    # Enhanced ship_id resolution using Device Registry service
    if this.ship_id == null || this.ship_id.contains("unknown") {
      let hostname = this.host || this.labels.instance
      if hostname != null {
        try {
          let result = ("http://device-registry:8080/lookup/" + hostname).http_get().parse_json()
          if result.success {
            root.ship_id = result.mapping.ship_id
            root.device_id = result.mapping.device_id
            root.device_type = result.mapping.device_type
            root.ship_id_source = "device_registry"
          }
        } catch {
          # Fallback to hostname-based derivation
          root.ship_id = hostname.split("-")[0] + "-ship"
          root.ship_id_source = "fallback"
        }
      }
    }
```

### Benefits in Benthos
- **Consistent Ship IDs**: All events get proper ship identification
- **Device Context**: Events enriched with device type and metadata
- **Fallback Safety**: Graceful degradation when registry is unavailable
- **Performance Monitoring**: Registry lookup success rates tracked
- **Debug Metadata**: Full resolution path logged for troubleshooting

## Deployment

### Docker Compose Integration

The service is included in the main `docker-compose.yml`:

```yaml
services:
  device-registry:
    build:
      context: ./services/device-registry
    container_name: aiops-device-registry
    ports:
      - "8081:8080"
    volumes:
      - device_registry_data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
      - DATABASE_PATH=/app/data/device_registry.db
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8080/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

### Starting the Service

```bash
# Start all services including device registry
docker-compose up -d

# Check device registry health
curl http://localhost:8081/health

# View logs
docker-compose logs device-registry
```

## Best Practices

### Device Registration Strategy

1. **Ship Registration First**: Always create ships before registering devices
2. **Consistent Naming**: Use standardized ship_id patterns (e.g., `ship-aurora`, `msc-container-01`)
3. **Meaningful Device Types**: Choose appropriate device classifications for better analytics
4. **Location Details**: Include specific locations for easier physical device identification
5. **Vendor/Model Info**: Record hardware details for inventory management

### Hostname Management

1. **Unique Hostnames**: Ensure each hostname is unique across the fleet
2. **Descriptive Names**: Use hostnames that indicate function (e.g., `aurora-bridge-nav-01`)
3. **IP Address Handling**: Register both hostnames and IP addresses when applicable
4. **FQDN Support**: Full domain names work (e.g., `server.ship-aurora.fleet.local`)

### Integration Guidelines

1. **Error Handling**: Always implement fallback logic for registry unavailability
2. **Caching**: Consider caching frequent lookups to reduce load
3. **Timeouts**: Use reasonable timeouts (2-5 seconds) for registry calls
4. **Monitoring**: Track registry lookup success rates and performance
5. **Batch Operations**: Use bulk APIs for initial data imports

## Monitoring and Troubleshooting

### Health Monitoring

```bash
# Check service health
curl http://localhost:8081/health

# Get statistics
curl http://localhost:8081/stats

# Monitor lookup success rates in Benthos logs
docker-compose logs benthos | grep "registry_lookup"
```

### Common Issues

**Issue: "Hostname not found"**
- Solution: Register the hostname using the interactive script
- Check: Verify ship exists before registering device

**Issue: "Registry service unavailable"** 
- Solution: Check docker-compose service status
- Fallback: System uses hostname-based derivation automatically

**Issue: "Duplicate hostname error"**
- Solution: Each hostname can only be registered once
- Check: Use lookup to see existing registration

**Issue: "Performance issues"**
- Solution: Monitor registry response times
- Optimization: Consider implementing Redis caching for high-volume lookups

### Debug Information

Benthos adds comprehensive debug metadata to all events:

```json
{
  "registry_metadata": {
    "lookup_attempted": true,
    "lookup_success": true,
    "ship_id_source": "device_registry",
    "original_host": "ubuntu-vm-01",
    "resolved_ship_id": "ship-aurora",
    "timestamp": "2024-09-10T17:30:00Z"
  }
}
```

This metadata helps troubleshoot ship_id resolution issues and monitor registry performance.

## Migration from Legacy Systems

For existing deployments with hardcoded ship IDs:

1. **Audit Current Data**: Identify all unique hostnames in your logs
2. **Register Ships**: Create ship records for all vessels in your fleet
3. **Bulk Registration**: Use the CLI script to register existing devices
4. **Update Services**: Deploy updated Benthos configuration with registry integration
5. **Monitor Performance**: Watch registry lookup success rates during transition
6. **Gradual Rollout**: Test with subset of data sources before full deployment

The Device Registry provides backward compatibility - existing ship_id values are preserved, and the registry only enriches previously unknown hostnames.