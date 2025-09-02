# Network Device Monitoring Implementation Guide

## Overview

This document explains the comprehensive network device monitoring implementation for the Maritime AIOps platform, addressing the collection, processing, and correlation of network infrastructure data from switches, bridges, routers, firewalls, and other network components.

## Network Component Data Collection

### Supported Device Types

The system monitors the following maritime network infrastructure:

#### Core Infrastructure
- **Switches**: Cisco Catalyst, HP/Aruba, Juniper EX series
- **Routers**: Cisco ISR, Juniper MX series, other enterprise routers  
- **Firewalls**: Fortinet FortiGate, Palo Alto, SonicWall, Cisco ASA
- **WiFi Controllers**: Aruba, Cisco WLC, Ubiquiti UniFi
- **Access Points**: All major vendor wireless access points

#### Maritime-Specific Equipment
- **VSAT Modems/Terminals**: iDirect, Hughes, Viasat
- **Satellite Communication Equipment**: Inmarsat, Iridium terminals
- **Bridge Network Equipment**: Navigation system switches/routers
- **Engine Room Network**: Industrial-grade network equipment
- **Guest Network Infrastructure**: Hospitality-focused WiFi equipment

#### Support Systems
- **Network Attached Storage (NAS)**: Synology, QNAP, FreeNAS
- **Uninterruptible Power Supplies (UPS)**: APC, Eaton with network cards
- **Environmental Monitoring**: Temperature, humidity sensors
- **Power Distribution Units (PDU)**: Network-enabled power strips

## Data Collection Methods

### 1. SNMP-Based Collection

Primary method using Simple Network Management Protocol:

**Supported SNMP Versions:**
- SNMPv1: Basic compatibility
- SNMPv2c: Primary method (community-based)
- SNMPv3: Secure authentication and encryption

**Standard MIBs Collected:**
```
- System MIB (1.3.6.1.2.1.1): Device identification, uptime
- Interfaces MIB (1.3.6.1.2.1.2): Interface statistics, status
- Host Resources MIB (1.3.6.1.2.1.25): CPU, memory, storage
- Entity MIB (1.3.6.1.2.1.47): Physical component inventory
```

**Vendor-Specific MIBs:**
- Cisco: CISCO-PROCESS-MIB, CISCO-MEMORY-POOL-MIB, CISCO-ENVMON-MIB
- Juniper: JUNIPER-MIB, JUNIPER-CHASSIS-DEFINES-MIB  
- Fortinet: FORTINET-FORTIGATE-MIB
- HP/Aruba: HP-ICF-OID, ARUBA-MIB

### 2. Syslog Collection

Network device logs via Syslog protocol:

**Supported Formats:**
- RFC 3164 (Legacy BSD Syslog)
- RFC 5424 (New Syslog Protocol)

**Log Categories:**
- Authentication events
- Configuration changes
- Interface state changes
- Security events
- Performance alerts

### 3. Flow-Based Monitoring

Traffic analysis using flow protocols:

**Supported Protocols:**
- NetFlow v5, v9, v10 (IPFIX)
- sFlow
- J-Flow (Juniper)

**Metrics Collected:**
- Traffic patterns and volumes
- Application identification  
- Bandwidth utilization
- Top talkers and conversations

## Maritime-Specific Data Processing

### 1. Device Classification

Automatic classification based on:
- System description parsing
- Vendor identification
- Location-based grouping
- Criticality assessment

```yaml
Device Classifications:
  critical_infrastructure:
    - Core routers
    - Primary firewalls  
    - Satellite communication equipment
    failure_impact: "critical"
    
  security_infrastructure:
    - Perimeter firewalls
    - Network access control
    - VPN concentrators
    failure_impact: "high"
    
  guest_services:
    - WiFi controllers
    - Guest network switches
    - Entertainment systems
    failure_impact: "medium"
```

### 2. Environmental Context Integration

Network device data is enriched with maritime environmental factors:

**Weather Correlation:**
- Temperature impact on device performance
- Humidity effects on electronics
- Rain fade correlation with satellite-dependent traffic

**Ship Motion Integration:**
- Pitch/roll/yaw correlation with wireless performance
- Vibration impact on fiber optic connections
- Navigation-correlated traffic patterns

**Power System Context:**
- UPS status correlation with network stability
- Generator operation impact on power quality
- Shore power vs. generator performance differences

### 3. Critical Path Monitoring

Identification and enhanced monitoring of critical communication paths:

```yaml
Critical Paths:
  satellite_uplink:
    devices: [primary_router, satellite_modem]
    monitoring_interval: 15s
    alert_threshold: 0.5  # 50% availability threshold
    
  navigation_network:
    devices: [bridge_switch, gps_systems, radar_equipment] 
    monitoring_interval: 30s
    alert_threshold: 0.8
    
  safety_systems:
    devices: [emergency_switch, safety_comm_equipment]
    monitoring_interval: 15s
    alert_threshold: 0.9  # Highest availability requirement
```

## Data Correlation and Enrichment

### Level 1 Correlation (Raw Data Enrichment)

Network device data is correlated with:

**System Resource Context:**
- CPU/memory utilization from host systems
- Disk I/O impacting network performance
- Application resource consumption

**Satellite Link Quality:**
- SNR/BER correlation with network performance
- Rain fade impact on traffic routing
- Backup link activation correlation

**Weather Conditions:**
- Temperature impact on device performance
- Humidity correlation with error rates
- Atmospheric conditions affecting RF links

**Ship Telemetry:**
- GPS position for location-aware monitoring
- Speed/heading correlation with antenna performance
- Attitude (pitch/roll/yaw) impact on stabilized communications

### Level 2 Correlation (Anomaly Correlation)

Network anomalies are correlated to create unified incidents:

**Cross-System Correlation:**
```
CPU Spike + Network Latency + Satellite Degradation 
→ "System Overload with Communication Impact"
```

**Weather Impact Correlation:**
```  
Rain Rate Increase + Satellite BER Increase + Network Rerouting
→ "Weather-Induced Communication Degradation"
```

**Infrastructure Failure Correlation:**
```
Switch CPU High + Interface Errors + Downstream Device Unreachable
→ "Network Infrastructure Failure"
```

## Service Implementation

### Network Device Collector Service

**Location:** `services/network-device-collector/`

**Key Components:**
- `network_collector.py`: Main collector service
- `Dockerfile`: Container configuration
- `requirements.txt`: Python dependencies

**Features:**
- Automatic device discovery via IP scanning
- SNMP polling with vendor-specific optimization
- Topology discovery using LLDP/CDP
- Real-time metrics publishing to NATS
- Prometheus metrics exposition

**Configuration:** `configs/network-devices.yaml`
```yaml
discovery:
  ip_ranges:
    - "192.168.1.0/24"    # Ship management network
    - "10.0.0.0/24"       # Core infrastructure
    - "172.16.0.0/24"     # WiFi and guest network
    
monitoring:
  polling_interval: 30
  interface_monitoring: true
  health_monitoring: true
  topology_discovery: true
```

### Docker Integration

Added to `docker-compose.yml`:
```yaml
network-device-collector:
  build:
    context: ./services/network-device-collector
  ports:
    - "8088:8080"  # Prometheus metrics
  volumes:
    - ./configs/network-devices.yaml:/app/config.yaml:ro
  depends_on:
    - nats
    - victoria-metrics
```

### Metrics Collection

**Prometheus Metrics:**
- `aiops_network_devices_total`: Device count by type/vendor
- `aiops_network_interface_utilization_percent`: Interface utilization
- `aiops_network_device_cpu_percent`: Device CPU usage
- `aiops_network_device_memory_percent`: Device memory usage  
- `aiops_network_collection_duration_seconds`: Collection performance
- `aiops_network_collection_errors_total`: Error tracking

**VictoriaMetrics Integration:**
Updated `vmagent/prometheus.yml` to scrape network device collector:
```yaml
- job_name: 'network-device-collector'
  static_configs:
    - targets: ['network-device-collector:8080']
  scrape_interval: 30s
```

## Data Flow and Processing

### 1. Collection Flow
```
Network Devices → SNMP/Syslog → Network Device Collector → NATS → Benthos Enrichment
```

### 2. Enrichment Flow
```
Raw Network Data → Level 1 Correlation → Context Enrichment → Enhanced Anomaly Detection
```

### 3. Correlation Flow  
```
Network Anomalies → Level 2 Correlation → Unified Incidents → Maritime Context → Remediation
```

## NATS Message Structure

### Device Discovery Messages
**Subject:** `telemetry.network.discovery`
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "total_devices": 12,
  "devices": [
    {
      "ip_address": "192.168.1.10",
      "hostname": "core-switch-bridge", 
      "device_type": "switch",
      "vendor": "cisco",
      "model": "WS-C2960X-24TS-L",
      "location": "bridge",
      "critical": true
    }
  ],
  "maritime_context": {
    "location": "ship_network",
    "collection_method": "snmp_discovery"
  }
}
```

### Interface Metrics Messages
**Subject:** `telemetry.network.interfaces`
```json
{
  "device_ip": "192.168.1.10",
  "device_type": "switch",
  "vendor": "cisco",
  "interfaces": [
    {
      "interface_name": "GigabitEthernet1/0/1",
      "interface_index": 1,
      "admin_status": "up",
      "oper_status": "up", 
      "utilization_percent": 75.5,
      "in_errors": 2,
      "out_errors": 0
    }
  ],
  "maritime_context": {
    "location": "ship_network",
    "critical_communications": true
  }
}
```

### Device Health Messages
**Subject:** `telemetry.network.health`
```json
{
  "device_ip": "192.168.1.10",
  "cpu_utilization_percent": 45.2,
  "memory_utilization_percent": 62.8,
  "temperature_celsius": 42.5,
  "power_supply_status": "normal",
  "fan_status": "normal",
  "maritime_context": {
    "environmental_monitoring": true,
    "critical_infrastructure": true
  }
}
```

## Enhanced Benthos Configuration

Updated `benthos/data-enrichment.yaml` with network device correlation:

### Network Device Enrichment Processing
```yaml
# Network device enrichment with system and satellite context
if this.data_source == "network" {
  root.enrichment_context.network_correlation = {
    "device_type": this.original_data.device_type || "unknown",
    "device_ip": this.original_data.device_ip,
    "vendor": this.original_data.vendor,
    "location": this.original_data.location
  }
  
  # Correlate with system load
  if system_data != null {
    root.enrichment_context.network_correlation.system_context = {
      "cpu_utilization": system_data.original_data.cpu_percent,
      "memory_utilization": system_data.original_data.memory_percent
    }
  }
  
  # Correlate with satellite link quality
  if related != null && related.data_source == "satellite" {
    root.enrichment_context.network_correlation.satellite_context = {
      "satellite_snr": related.original_data.snr_db,
      "satellite_ber": related.original_data.ber
    }
  }
}
```

## Testing and Validation

### Updated Test Script

Enhanced `scripts/test_two_level_correlation.py` with network device testing:

**Network Device Test Data:**
```python
def generate_network_data(self, scenario: str = "normal"):
    return {
        "device_ip": "192.168.1.10",
        "device_type": "switch",
        "vendor": "cisco",
        "hostname": "core-switch-bridge",
        "cpu_utilization_percent": 25.0,
        "memory_utilization_percent": 40.0,
        "interfaces": [
            {
                "interface_name": "GigabitEthernet1/0/1",
                "utilization_percent": 35.0,
                "in_errors": 2,
                "out_errors": 0
            }
        ]
    }
```

**Test Scenarios:**
1. **Normal Operations**: Baseline network performance
2. **High System Load**: Network correlation with system overload  
3. **Weather Stress**: Satellite impact on network routing
4. **Heavy Rain Impact**: Complete weather degradation scenario

## Maritime Operational Context

### Critical Infrastructure Monitoring

**Bridge Systems:**
- Navigation equipment network connectivity
- Radar/GPS system network performance  
- Communication system redundancy

**Engine Room Networks:**
- Industrial network monitoring
- SCADA system connectivity
- Environmental sensor networks

**Guest Services:**
- WiFi performance and capacity
- Entertainment system networks
- Internet connectivity for passengers

**Safety Systems:**
- Emergency communication networks
- Fire detection system connectivity
- Man overboard system networks

### Environmental Considerations

**Temperature Management:**
- Device operating temperature monitoring
- Cooling system correlation
- Hot spot identification

**Power Quality:**
- UPS integration for network stability
- Generator impact on network performance
- Shore power vs. ship power correlation

**Physical Security:**
- Access control system networks
- CCTV system connectivity
- Intrusion detection networks

## Alerting and Incident Management

### Network-Specific Alert Conditions

**Critical Infrastructure Failure:**
```yaml
condition: "critical_path_health < 0.5"
severity: "critical"
description: "Critical network path has failed"
```

**Environmental Impact:**
```yaml  
condition: "environmental_temperature > 50 OR humidity > 85"
severity: "warning"
description: "Network performance degraded due to environmental conditions"
```

**Satellite Link Degradation:**
```yaml
condition: "satellite_link_quality < 0.7 AND satellite_dependent_services > 0"
severity: "warning"
description: "Satellite-dependent network services at risk"
```

### Remediation Playbooks

Network device specific remediation actions:

**Switch/Router Issues:**
- Interface reset procedures
- VLAN reconfiguration
- Routing table cleanup
- Configuration backup/restore

**Firewall Issues:**  
- Connection table cleanup
- Rule optimization
- Traffic load balancing
- Backup firewall activation

**WiFi Issues:**
- Channel optimization
- Access point load balancing
- Authentication server checks
- Guest network isolation

## Performance Monitoring

### Key Performance Indicators

**Device Health KPIs:**
- CPU utilization < 80%
- Memory utilization < 85%
- Temperature < 50°C (maritime environment adjusted)
- Interface error rate < 0.01%

**Network Performance KPIs:**
- Interface utilization < 80%
- Packet loss < 0.1%
- Latency < 100ms (satellite-adjusted)
- Availability > 99.9% (critical paths)

**Maritime-Specific KPIs:**
- Satellite-dependent service availability
- Environmental impact factor
- Critical path redundancy status
- Emergency communication readiness

## Future Enhancements

### Planned Features

**AI/ML Integration:**
- Predictive failure analysis
- Anomaly pattern recognition
- Performance optimization recommendations
- Capacity planning automation

**Enhanced Topology Discovery:**
- Automatic cable tracing
- Port mapping automation
- VLAN topology visualization
- Dependency mapping

**Security Integration:**
- Network security monitoring
- Intrusion detection correlation
- Vulnerability assessment integration
- Compliance monitoring

**Advanced Correlation:**
- Multi-ship fleet correlation
- Shore-to-ship performance comparison
- Route-based performance analysis
- Port vs. sea performance patterns

This comprehensive network device monitoring implementation provides the maritime AIOps platform with complete visibility into network infrastructure, enabling proactive maintenance, intelligent correlation, and rapid incident resolution in the challenging maritime environment.