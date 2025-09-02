# Maritime AIOps Platform - Service Data Flow Architecture

## Complete Service Input/Output Map

```mermaid
graph TB
    %% Data Sources (External)
    subgraph "Data Sources (No Code Deployment)"
        A1[Ship Systems<br/>CPU/Memory/Disk]
        A2[Network Devices<br/>Switches/Routers/Firewalls<br/>SNMP Protocol]
        A3[VSAT Equipment<br/>Satellite Modems]
        A4[Ship Sensors<br/>GPS/Weather/Navigation]
        A5[Applications<br/>Docker Logs]
        A6[External APIs<br/>Weather/AIS]
    end

    %% Collection Layer
    subgraph "Collection Services"
        B1[node-exporter<br/>:9100]
        B2[network-device-collector<br/>:8080]
        B3[vsat-simulator<br/>:8081]
        B4[ship-simulator<br/>:8082]
        B5[vector<br/>:8686]
        B6[external-api-collector<br/>:8087]
    end

    %% Storage Layer
    subgraph "Storage Systems"
        C1[VictoriaMetrics<br/>:8428<br/>Time-series Metrics]
        C2[ClickHouse<br/>:8123<br/>Logs & Events]
        C3[NATS JetStream<br/>:4222<br/>Real-time Streams]
    end

    %% Level 1 Correlation
    subgraph "Level 1: Data Enrichment"
        D1[benthos-enrichment<br/>:4195<br/>Raw Data Correlation]
    end

    %% Anomaly Detection
    subgraph "Anomaly Detection"
        E1[anomaly-detection<br/>:8081<br/>Basic Detection]
        E2[enhanced-anomaly-detection<br/>:8082<br/>Context-Aware Detection]
    end

    %% Level 2 Correlation
    subgraph "Level 2: Anomaly Correlation"
        F1[benthos<br/>:4195<br/>Anomaly Correlation]
    end

    %% Incident Management
    subgraph "Incident & Alert Management"
        G1[incident-api<br/>:8083<br/>Lifecycle Management]
        G2[vmalert<br/>:8080<br/>Alert Rules]
        G3[alertmanager<br/>:9093<br/>Notifications]
        G4[mailhog<br/>:8025<br/>Email Server]
    end

    %% Remediation
    subgraph "Automation & Remediation"
        H1[remediation<br/>:8084<br/>Maritime Playbooks]
    end

    %% Visualization
    subgraph "Monitoring & Visualization"
        I1[grafana<br/>:3000<br/>Maritime Dashboards]
    end

    %% Intelligence
    subgraph "Fleet Intelligence"
        J1[capacity-forecasting<br/>:8085]
        J2[cross-ship-benchmarking<br/>:8086]
        J3[fleet-aggregation<br/>:8087]
    end

    %% Data Flow Connections
    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
    A5 --> B5
    A6 --> B6

    B1 -->|Prometheus Metrics| C1
    B2 -->|SNMP Metrics| C1
    B3 -->|Telemetry| C3
    B4 -->|Ship Data| C3
    B5 -->|Structured Logs| C2
    B6 -->|External Data| C3

    C1 --> D1
    C2 --> D1
    C3 --> D1

    D1 -->|Enriched Telemetry| E1
    D1 -->|Enriched Telemetry| E2

    E1 -->|Basic Anomalies| F1
    E2 -->|Context-Aware Anomalies| F1

    F1 -->|Correlated Incidents| G1

    G1 --> G2
    C1 --> G2
    G2 --> G3
    G3 --> G4

    G3 --> H1
    G1 --> H1

    C1 --> I1
    C2 --> I1
    G1 --> I1
    H1 --> I1

    C1 --> J1
    G1 --> J2
    I1 --> J3

    %% External outputs
    G4 -->|Email Alerts| K1[Ship Operators]
    I1 -->|Web Dashboard| K2[Bridge Crew]
    J3 -->|Fleet Reports| K3[Shore Management]
    H1 -->|Automated Actions| K4[Ship Systems]
```

## Key Service Functions

### Data Collection Layer
| Service | Input | Output | Protocol |
|---------|--------|--------|----------|
| node-exporter | Ship system metrics | Prometheus metrics | HTTP scraping |
| network-device-collector | Network devices | SNMP metrics | SNMP v2c/v3 |
| vector | Application logs | Structured logs | File tailing, Docker API |
| Data simulators | VSAT/Ship telemetry | Simulated data | Internal generation |

### Storage & Messaging
| Service | Input | Output | Purpose |
|---------|--------|--------|---------|
| VictoriaMetrics | Prometheus metrics | Time-series queries | Metrics storage |
| ClickHouse | Structured logs | SQL queries | Log analytics |
| NATS JetStream | Real-time events | Message streams | Event streaming |

### Processing & Correlation
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| benthos-enrichment | Raw metrics/logs/telemetry | Enriched data streams | Level 1 correlation |
| anomaly-detection | Enriched telemetry | Anomaly events | Pattern detection |
| enhanced-anomaly-detection | Enriched + context | Context-aware anomalies | Maritime-aware detection |
| benthos correlation | Anomaly events | Correlated incidents | Level 2 correlation |

### Operations & Response
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| incident-api | Incident events | REST API, lifecycle events | Incident management |
| vmalert | Metrics + incidents | Alert rules evaluation | Alert generation |
| alertmanager | Alert events | Email, webhooks | Notification routing |
| remediation | Alerts + incidents | Automated actions | Maritime playbooks |

### Intelligence & Visualization
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| grafana | All data sources | Web dashboards | Unified visualization |
| capacity-forecasting | Historical metrics | Capacity predictions | Resource planning |
| cross-ship-benchmarking | Incident data | Performance comparisons | Fleet optimization |
| fleet-aggregation | Multi-ship data | Fleet coordination | Operations intelligence |

## Network Device Data Collection (SNMP)

**Critical Point**: We collect network device data via **SNMP (Simple Network Management Protocol)** - no code deployment on devices required.

### How SNMP Works:
1. **Native Support**: Switches, routers, firewalls support SNMP out-of-the-box
2. **Remote Queries**: Our `network-device-collector` queries devices over the network
3. **Standard OIDs**: Uses industry-standard Object Identifiers for metrics
4. **Vendor MIBs**: Supports vendor-specific Management Information Bases
5. **Configuration Only**: Requires only SNMP community string configuration on devices

### Data Collected via SNMP:
- **Interface Metrics**: Utilization, error rates, packet counts
- **Device Health**: CPU, memory, temperature, power status
- **Network Topology**: LLDP/CDP neighbor discovery
- **Security Stats**: Firewall connection counts, throughput
- **Environmental**: Device temperature, humidity, power quality

### Supported Devices:
- **Switches**: Cisco Catalyst, HP/Aruba, Juniper EX
- **Routers**: Cisco ISR, Juniper MX  
- **Firewalls**: Fortinet FortiGate, Palo Alto, SonicWall
- **WiFi**: Controllers and access points
- **Maritime Equipment**: VSAT modems, satellite terminals
- **Support Systems**: NAS, UPS, environmental sensors

This architecture provides comprehensive maritime network monitoring without requiring software deployment on individual network devices.