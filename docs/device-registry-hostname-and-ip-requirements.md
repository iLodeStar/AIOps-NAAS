# Device Registry: Hostname AND IP Address Requirements

## Overview

The Device Registry & Mapping Service has been updated to enforce **both hostname AND IP address** requirements for all device registrations. This change ensures complete device identification and eliminates ambiguity in device lookups.

## Key Changes

### Previous Approach: "Hostname OR IP"
- Devices could be registered with either a hostname or an IP address as the primary identifier
- Additional identifiers were optional
- Caused confusion when logs contained raw IP addresses that couldn't be resolved

### New Approach: "Hostname AND IP"
- **Both hostname AND primary IP address are mandatory** for every device registration
- Additional IP addresses are optional but still supported
- Provides complete device identification for all lookup scenarios

## Updated Registration Requirements

### Mandatory Fields
1. **Hostname**: System hostname (e.g., `ubuntu-vm-01`, `nav-computer`)
2. **Primary IP Address**: Main IP address (e.g., `192.168.1.100`)
3. **Ship ID**: Associated ship identifier
4. **Device Type**: Device category (navigation, engine, communication, etc.)

### Optional Fields
- Additional IP addresses (for multi-homed devices)
- Vendor/manufacturer
- Model
- Physical location on ship

## Database Schema Changes

### Updated Device Table
```sql
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    ip_address TEXT NOT NULL,  -- New required field
    ship_id TEXT NOT NULL,
    device_type TEXT NOT NULL,
    vendor TEXT,
    model TEXT,
    location TEXT,
    capabilities TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ship_id) REFERENCES ships (ship_id),
    UNIQUE (hostname, ip_address)  -- Enforce unique hostname+IP combination
);
```

### Hostname Mappings Table
- Now stores both hostname and IP address entries for each device
- Enables lookup by either hostname or IP address
- Links to the same device record

## API Changes

### Registration Endpoint: `/devices/register`

**Previous Request:**
```json
{
    "hostname": "ubuntu-vm-01",
    "ship_id": "ship-aurora",
    "device_type": "server",
    "additional_identifiers": ["192.168.1.100"]
}
```

**New Request:**
```json
{
    "hostname": "ubuntu-vm-01",
    "ip_address": "192.168.1.100",
    "ship_id": "ship-aurora", 
    "device_type": "server",
    "additional_ip_addresses": ["10.0.0.50"]
}
```

**Response:**
```json
{
    "success": true,
    "device_id": "dev_a1b2c3d4e5f6",
    "hostname": "ubuntu-vm-01",
    "ip_address": "192.168.1.100",
    "ship_id": "ship-aurora",
    "identifiers_registered": [
        "ubuntu-vm-01",
        "192.168.1.100", 
        "10.0.0.50"
    ],
    "message": "Device registered successfully with hostname AND IP address + 1 additional IP(s)"
}
```

### Lookup Endpoint: `/lookup/{identifier}`

The lookup endpoint continues to work with both hostnames and IP addresses:

```bash
# Lookup by hostname
curl http://localhost:8081/lookup/ubuntu-vm-01

# Lookup by primary IP
curl http://localhost:8081/lookup/192.168.1.100

# Lookup by additional IP
curl http://localhost:8081/lookup/10.0.0.50
```

All return the same device information including both hostname and IP address.

## Interactive Registration Updates

### Auto-Detection
The auto-detection feature now:
1. **Detects hostname** using `socket.gethostname()`
2. **Detects all IP addresses** using multiple methods
3. **Requires selection of primary IP** if multiple IPs found
4. **Treats remaining IPs as additional** IP addresses

### Manual Registration
Manual registration now requires:
1. **Hostname input** (validated for uniqueness)
2. **Primary IP address input** (validated for format and uniqueness)
3. **Optional additional IP addresses** (validated individually)

### Example Auto-Registration Flow
```bash
# Auto-detect current system
python scripts/register_device.py --auto-register

# Output:
🔍 Auto-detecting system identifiers...
✅ Detected hostname: ubuntu-vm-01
✅ Detected IP addresses: 192.168.1.100, 10.0.0.50

✅ Using 192.168.1.100 as primary IP address
📡 Additional IP: 10.0.0.50 will be registered as additional identifier

📋 Auto-Registration Summary:
   Hostname: ubuntu-vm-01
   Primary IP: 192.168.1.100
   Additional IPs: 10.0.0.50
   Ship: ship-aurora
   Device Type: server
```

## Command Line Usage

### New Command Line Arguments
```bash
# Register device with hostname AND IP
python scripts/register_device.py \
    --hostname "ubuntu-vm-01" \
    --ip-address "192.168.1.100" \
    --ship-id "ship-aurora" \
    --device-type "server" \
    --additional-ip-addresses "10.0.0.50" "172.16.1.100"

# Auto-register current system
python scripts/register_device.py --auto-register

# Lookup by hostname or IP
python scripts/register_device.py --lookup "ubuntu-vm-01"
python scripts/register_device.py --lookup "192.168.1.100"
```

## Migration Guide

### For Existing Deployments

1. **Database Migration**: The database schema will automatically add the new `ip_address` column
2. **Existing Data**: Devices registered with the old approach will need to be updated with IP addresses
3. **API Compatibility**: Update all API calls to include both hostname and ip_address fields

### For Development

1. **Update Registration Calls**: Ensure all device registration code provides both hostname and IP address
2. **Test Coverage**: Validate both hostname and IP address lookup scenarios
3. **Error Handling**: Handle cases where hostname or IP address are missing or invalid

## Benefits

### Improved Identification
- **Complete Device Context**: Every device has both hostname and IP address
- **Reliable Lookups**: Can resolve ship_id from either hostname or IP address in logs
- **No Ambiguity**: Clear distinction between hostname and IP address roles

### Better Log Processing
- **Vector Integration**: Handles both hostname fields and source IP addresses from logs
- **SNMP Compatibility**: Works with SNMP devices that use IP addresses as identifiers
- **Container Support**: Supports containerized environments with dynamic IP assignment

### Enhanced Fleet Management
- **Network Topology**: Clear understanding of device network configuration
- **Troubleshooting**: Can correlate issues using either hostname or IP address
- **Documentation**: Complete device inventory with all identifiers

## Error Handling

### Validation Errors
- **Missing Hostname**: Returns 422 with "hostname is required"
- **Missing IP Address**: Returns 422 with "ip_address is required"
- **Invalid IP Format**: Returns 400 with "Invalid IP address format"
- **Duplicate Combination**: Returns 400 with "Device with this hostname+IP combination already exists"

### Recovery Scenarios
- **Service Unavailable**: Benthos gracefully falls back to hostname-based ship_id derivation
- **Lookup Failures**: Returns meaningful error messages for debugging
- **Registration Conflicts**: Clear error messages indicate which identifiers are already registered

## Testing

### Test Scenarios
1. **Registration with hostname and IP**: Verify both are required
2. **Lookup by hostname**: Ensure returns complete device info including IP
3. **Lookup by IP address**: Ensure returns complete device info including hostname
4. **Auto-detection**: Verify both hostname and IP are detected correctly
5. **Additional IPs**: Verify multiple IP addresses are handled properly

### Validation Commands
```bash
# Test service health
curl http://localhost:8081/health

# Test registration
curl -X POST http://localhost:8081/devices/register \
  -H "Content-Type: application/json" \
  -d '{
    "hostname": "test-device",
    "ip_address": "192.168.1.200",
    "ship_id": "ship-test",
    "device_type": "server"
  }'

# Test lookup
curl http://localhost:8081/lookup/test-device
curl http://localhost:8081/lookup/192.168.1.200
```

This updated approach ensures robust device identification across the entire AIOps platform while maintaining backward compatibility for lookup operations.