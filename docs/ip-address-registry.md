# IP Address Registry & Multi-Identifier Support

The Device Registry & Mapping Service now provides comprehensive support for IP address lookups and multi-identifier device registration, ensuring ships can be identified by any IP address or hostname appearing in logs.

## Key Features

### 1. IP Address Lookup Support

The Device Registry can now resolve ship IDs from IP addresses in addition to hostnames:

```bash
# Lookup by IP address
curl http://localhost:8081/lookup/192.168.1.100

# Lookup by hostname  
curl http://localhost:8081/lookup/ubuntu-vm-01
```

**Response Format:**
```json
{
  "success": true,
  "hostname": "192.168.1.100",
  "mapping": {
    "ship_id": "ship-aurora",
    "device_id": "dev_a1b2c3d4e5f6",
    "device_type": "server",
    "ship_name": "MSC Aurora",
    "vendor": "Dell",
    "model": "PowerEdge R740",
    "location": "Server Room"
  }
}
```

### 2. Multi-Identifier Device Registration

Devices can now be registered with multiple identifiers (hostname + IP addresses):

**API Registration:**
```bash
curl -X POST http://localhost:8081/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "ubuntu-vm-01",
    "ship_id": "ship-aurora", 
    "device_type": "server",
    "additional_identifiers": ["192.168.1.100", "10.0.0.50"]
  }'
```

**Response:**
```json
{
  "success": true,
  "device_id": "dev_a1b2c3d4e5f6",
  "hostname": "ubuntu-vm-01",
  "ship_id": "ship-aurora",
  "identifiers_registered": ["ubuntu-vm-01", "192.168.1.100", "10.0.0.50"],
  "message": "Device registered successfully with 3 identifier(s)"
}
```

### 3. Auto-Detection in Interactive Script

The registration script can now automatically detect the current system's hostname and IP addresses:

```bash
# Auto-register current system
python scripts/register_device.py --auto-register

# Command line with additional IPs
python scripts/register_device.py \
  --hostname "ubuntu-vm-01" \
  --ship-id "ship-aurora" \
  --device-type "server" \
  --additional-identifiers "192.168.1.100" "10.0.0.50"
```

**Auto-Detection Features:**
- **Hostname Detection**: Uses `socket.gethostname()` to get system hostname
- **IP Detection**: Multiple methods to detect all network interfaces:
  - Primary IP via socket connection test
  - Interface IPs via `ip route` (Linux) or `route get` (macOS)  
  - Fallback to hostname resolution
- **Smart Suggestions**: Device type suggestions based on hostname patterns
- **Validation**: Checks for existing registrations before proceeding

## Benthos Integration

The enhanced registry seamlessly integrates with Benthos for log processing:

**Device Registry Lookup in Benthos:**
```yaml
# Enhanced hostname/IP resolution
- mapping: |
    # Try hostname first, then IP
    let identifier = if this.host != null { 
      this.host 
    } else if this.labels.instance != null { 
      this.labels.instance 
    } else if this.source_ip != null {
      this.source_ip
    } else { 
      null 
    }
    
    if identifier != null {
      try {
        let result = ("http://device-registry:8080/lookup/" + identifier).http_get().parse_json()
        if result.success {
          root.ship_id = result.mapping.ship_id
          root.device_id = result.mapping.device_id
          root.device_type = result.mapping.device_type
          root.ship_id_source = "device_registry"
        }
      } catch {
        root.ship_id = "unknown_ship"
        root.ship_id_source = "fallback"
      }
    }
```

## Use Cases

### 1. Vector Syslog Processing
Vector often sends logs with both hostname and IP. The registry can resolve either:

```json
// Log from Vector
{
  "host": "ubuntu-vm-01",
  "source_ip": "192.168.1.100", 
  "message": "CPU usage high"
}
```

Both `host` and `source_ip` will resolve to the same ship_id.

### 2. SNMP Network Monitoring
SNMP devices typically use IP addresses as identifiers:

```json
// SNMP metric
{
  "labels": {
    "instance": "192.168.1.200",
    "device": "switch-01"
  },
  "metric_name": "interface_utilization"
}
```

The IP `192.168.1.200` will resolve to the correct ship.

### 3. Container/VM Logs
Containers and VMs may have different internal/external IP addresses:

```bash
# Register container with multiple IPs
python scripts/register_device.py \
  --hostname "app-container-01" \
  --ship-id "ship-aurora" \
  --device-type "server" \
  --additional-identifiers "172.17.0.5" "192.168.1.150"
```

## Database Schema

The registry uses a flexible hostname_mappings table that supports any identifier type:

```sql
CREATE TABLE hostname_mappings (
    hostname TEXT PRIMARY KEY,      -- Can be hostname, IP, or any identifier
    ship_id TEXT NOT NULL,
    device_id TEXT NOT NULL, 
    device_type TEXT NOT NULL,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Sample Data:**
```sql
INSERT INTO hostname_mappings VALUES 
  ('ubuntu-vm-01', 'ship-aurora', 'dev_a1b2c3d4e5f6', 'server', '2024-01-15 10:00:00'),
  ('192.168.1.100', 'ship-aurora', 'dev_a1b2c3d4e5f6', 'server', '2024-01-15 10:00:00'),
  ('10.0.0.50', 'ship-aurora', 'dev_a1b2c3d4e5f6', 'server', '2024-01-15 10:00:00');
```

## API Endpoints

### Get Device Identifiers
```bash
# Get all identifiers for a device
curl http://localhost:8081/devices/dev_a1b2c3d4e5f6/identifiers
```

**Response:**
```json
{
  "success": true,
  "device_id": "dev_a1b2c3d4e5f6",
  "identifiers": ["ubuntu-vm-01", "192.168.1.100", "10.0.0.50"],
  "count": 3
}
```

### Enhanced Device Listing
Device lists now include all identifiers:

```bash
curl http://localhost:8081/devices
```

**Response:**
```json
[
  {
    "device_id": "dev_a1b2c3d4e5f6",
    "hostname": "ubuntu-vm-01",
    "ship_id": "ship-aurora",
    "device_type": "server",
    "all_identifiers": ["ubuntu-vm-01", "192.168.1.100", "10.0.0.50"],
    "ship_name": "MSC Aurora"
  }
]
```

## Benefits

1. **Complete IP Coverage**: Any IP address in logs can be resolved to a ship_id
2. **Flexible Registration**: Support for complex networking scenarios (containers, VMs, multi-homed devices)
3. **Auto-Discovery**: Easy registration of current system without manual entry
4. **Backward Compatibility**: Existing hostname-only registrations continue to work
5. **Performance**: Indexed lookups for fast resolution during log processing
6. **Audit Trail**: Track when identifiers were last seen for monitoring

## Examples

### Auto-Register Current System
```bash
# Run on any system to auto-register it
python scripts/register_device.py --auto-register

# Output:
# 🔍 Detecting current system identifiers...
# 📋 Detected System Information:
#    Hostname: ubuntu-vm-01
#    IP Addresses: 192.168.1.100, 10.0.0.50
# Use detected hostname 'ubuntu-vm-01'? (Y/n): y
# Register these IP addresses as additional identifiers? (Y/n): y
# Select ship (1-3) or enter ship_id directly: ship-aurora
# Select device type... [suggested: workstation]: server
# ✅ System registered successfully!
#    Device ID: dev_a1b2c3d4e5f6
#    Registered Identifiers: ubuntu-vm-01, 192.168.1.100, 10.0.0.50
```

### Test IP Lookup
```bash
# Test lookup by different identifiers
python scripts/register_device.py --lookup ubuntu-vm-01
python scripts/register_device.py --lookup 192.168.1.100
python scripts/register_device.py --lookup 10.0.0.50

# All should return the same ship_id and device_id
```

This comprehensive IP address registry ensures that the AIOps platform can reliably identify ships regardless of whether logs contain hostnames, IP addresses, or other network identifiers.