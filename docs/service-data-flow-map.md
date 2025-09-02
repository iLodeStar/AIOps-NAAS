# Maritime AIOps Platform - Service Data Flow Architecture

## Complete Service Input/Output Map

```mermaid
graph TB
    %% Data Sources (External)
    subgraph "Data Sources (No Code Deployment)"
        A1["Ship Systems<br/>CPU/Memory/Disk"]
        A2["Network Devices<br/>Switches/Routers/Firewalls<br/>SNMP Protocol"]
        A3["VSAT Equipment<br/>Satellite Modems"]
        A4["Ship Sensors<br/>GPS/Weather/Navigation"]
        A5["Applications<br/>Docker Logs"]
        A6["External APIs<br/>Weather/AIS"]
    end

    %% Collection Layer
    subgraph "Collection Services"
        B1["node-exporter<br/>:9100"]
        B2["network-device-collector<br/>:8080"]
        B3["vsat-simulator<br/>:8081"]
        B4["ship-simulator<br/>:8082"]
        B5["vector<br/>:8686"]
        B6["external-api-collector<br/>:8087"]
    end

    %% Storage Layer
    subgraph "Storage Systems"
        C1["VictoriaMetrics<br/>:8428<br/>Time-series Metrics"]
        C2["ClickHouse<br/>:8123<br/>Logs & Events"]
        C3["NATS JetStream<br/>:4222<br/>Real-time Streams"]
    end

    %% AI/ML Layer
    subgraph "AI/ML Services"
        ML1["Ollama LLM<br/>:11434<br/>Local Language Model"]
        ML2["Qdrant Vector DB<br/>:6333<br/>Embeddings Storage"]
        ML3["LangChain RAG<br/>:8090<br/>Context Retrieval"]
    end

    %% Level 1 Correlation
    subgraph "Level 1: Data Enrichment"
        D1["benthos-enrichment<br/>:4195<br/>Raw Data Correlation"]
    end

    %% Anomaly Detection
    subgraph "Anomaly Detection"
        E1["anomaly-detection<br/>:8081<br/>Basic Detection"]
        E2["enhanced-anomaly-detection<br/>:8082<br/>Context-Aware Detection<br/>AI-Enhanced"]
    end

    %% Level 2 Correlation
    subgraph "Level 2: Anomaly Correlation"
        F1["benthos<br/>:4195<br/>Anomaly Correlation<br/>AI-Assisted"]
    end

    %% Incident Management
    subgraph "Incident & Alert Management"
        G1["incident-api<br/>:8083<br/>Lifecycle Management"]
        G2["vmalert<br/>:8080<br/>Alert Rules"]
        G3["alertmanager<br/>:9093<br/>Notifications"]
        G4["mailhog<br/>:8025<br/>Email Server"]
    end

    %% Remediation
    subgraph "Automation & Remediation"
        H1["remediation<br/>:8084<br/>Maritime Playbooks<br/>AI-Generated Solutions"]
    end

    %% Visualization
    subgraph "Monitoring & Visualization"
        I1["grafana<br/>:3000<br/>Maritime Dashboards"]
    end

    %% Intelligence
    subgraph "Fleet Intelligence"
        J1["capacity-forecasting<br/>:8085<br/>ML Predictions"]
        J2["cross-ship-benchmarking<br/>:8086<br/>AI Analysis"]
        J3["fleet-aggregation<br/>:8087"]
    end

    %% Data Flow Connections
    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B4
    A5 --> B5
    A6 --> B6

    B1 -->|"Prometheus Metrics"| C1
    B2 -->|"SNMP Metrics"| C1
    B3 -->|"Telemetry"| C3
    B4 -->|"Ship Data"| C3
    B5 -->|"Structured Logs"| C2
    B6 -->|"External Data"| C3

    %% AI/ML Integration
    C1 --> ML2
    C2 --> ML2
    C3 --> ML2
    ML2 --> ML3
    ML3 --> ML1

    C1 --> D1
    C2 --> D1
    C3 --> D1
    ML3 -->|"AI Context"| D1

    D1 -->|"Enriched Telemetry"| E1
    D1 -->|"Enriched Telemetry"| E2
    ML1 -->|"AI Insights"| E2

    E1 -->|"Basic Anomalies"| F1
    E2 -->|"Context-Aware Anomalies"| F1
    ML1 -->|"Correlation Suggestions"| F1

    F1 -->|"Correlated Incidents"| G1

    G1 --> G2
    C1 --> G2
    G2 --> G3
    G3 --> G4

    G3 --> H1
    G1 --> H1
    ML1 -->|"Solution Recommendations"| H1

    C1 --> I1
    C2 --> I1
    G1 --> I1
    H1 --> I1

    C1 --> J1
    G1 --> J2
    I1 --> J3
    ML1 -->|"ML Predictions"| J1
    ML1 -->|"Performance Analysis"| J2

    %% External outputs
    G4 -->|"Email Alerts"| K1["Ship Operators"]
    I1 -->|"Web Dashboard"| K2["Bridge Crew"]
    J3 -->|"Fleet Reports"| K3["Shore Management"]
    H1 -->|"Automated Actions"| K4["Ship Systems"]
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

### AI/ML Services
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| Ollama LLM | Query prompts + context | Text responses, insights | Local language model inference |
| Qdrant Vector DB | Text embeddings | Vector similarity search | Semantic search for logs/docs |
| LangChain RAG | Raw data + embeddings | Contextual information | Retrieval-Augmented Generation |

### Processing & Correlation  
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| benthos-enrichment | Raw metrics/logs/telemetry + AI context | Enriched data streams | Level 1 correlation with AI insights |
| anomaly-detection | Enriched telemetry | Anomaly events | Pattern detection |
| enhanced-anomaly-detection | Enriched + context + AI insights | Context-aware anomalies | Maritime-aware detection with ML |
| benthos correlation | Anomaly events + AI suggestions | Correlated incidents | Level 2 correlation with AI assistance |

### Operations & Response
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| incident-api | Incident events | REST API, lifecycle events | Incident management |
| vmalert | Metrics + incidents | Alert rules evaluation | Alert generation |
| alertmanager | Alert events | Email, webhooks | Notification routing |
| remediation | Alerts + incidents + AI recommendations | Automated actions | Maritime playbooks with AI-generated solutions |

### Intelligence & Visualization
| Service | Input | Output | Function |
|---------|--------|--------|---------|
| grafana | All data sources | Web dashboards | Unified visualization |
| capacity-forecasting | Historical metrics + ML models | Capacity predictions | ML-powered resource planning |
| cross-ship-benchmarking | Incident data + AI analysis | Performance comparisons | AI-enhanced fleet optimization |
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

## AI/ML Integration Points

### How AI Enhances the Maritime AIOps Platform

**Ollama Local LLM (Port: 11434)**
- **Context Analysis**: Understands maritime operational context (weather, satellite, ship position)
- **Pattern Recognition**: Identifies complex relationships between system events
- **Solution Generation**: Creates contextual remediation recommendations
- **Natural Language Processing**: Converts technical metrics into operational insights

**Qdrant Vector Database (Port: 6333)**  
- **Semantic Search**: Vector embeddings of logs, incidents, and procedures
- **Pattern Matching**: Historical incident pattern recognition
- **Maritime Knowledge**: Stores maritime-specific operational knowledge vectors
- **Context Retrieval**: Retrieves relevant context for correlation and remediation

**LangChain RAG System (Port: 8090)**
- **Knowledge Retrieval**: Connects stored knowledge with current incidents
- **Context Enrichment**: Adds relevant historical context to current events  
- **Procedure Lookup**: Retrieves relevant maritime operational procedures
- **Documentation Integration**: Incorporates equipment manuals and best practices

### AI Enhancement by Service Layer

**Data Enrichment Layer**
- AI enriches raw telemetry with semantic context about maritime operations
- Understands relationships between weather conditions and satellite performance
- Provides operational context (normal operations vs. storm conditions vs. port arrival)

**Anomaly Detection Layer**
- AI-enhanced pattern recognition beyond statistical thresholds
- Semantic understanding of complex multi-system maritime scenarios
- Context-aware anomaly classification (weather-related vs. equipment failure vs. operational)

**Correlation Layer**
- AI suggests correlation patterns based on maritime operational knowledge
- Semantic clustering of related anomalies into operational incidents
- Natural language explanations of correlation reasoning

**Remediation Layer**  
- AI generates contextual solution recommendations based on maritime best practices
- Learning from historical remediation success/failure patterns
- Natural language explanations help operators understand recommended actions

**Intelligence Layer**
- ML-powered predictive analytics for capacity and performance forecasting
- AI-enhanced fleet benchmarking with operational context awareness
- Semantic analysis of operational patterns across maritime environments

### AI Data Processing Flow

```mermaid
graph TD
    %% Maritime Knowledge Ingestion
    A1["Equipment Manuals"] --> A2["Knowledge Ingestion"]
    A3["Historical Incidents"] --> A2
    A4["Maritime Procedures"] --> A2
    A5["Weather Correlations"] --> A2

    %% Vector Processing
    A2 --> B1["Text Embeddings"]
    B1 --> B2["Qdrant Vector DB"]

    %% Real-time AI Processing
    C1["Live Telemetry"] --> C2["LangChain RAG"]
    B2 --> C2
    C2 --> C3["Context + Query"]
    C3 --> D1["Ollama LLM"]

    %% AI Outputs to Services
    D1 --> E1["Enhanced Context"]
    D1 --> E2["Correlation Suggestions"]
    D1 --> E3["Solution Recommendations"] 
    D1 --> E4["Predictive Insights"]

    %% Service Integration
    E1 --> F1["benthos-enrichment"]
    E2 --> F2["benthos correlation"]
    E3 --> F3["remediation-service"]
    E4 --> F4["Fleet Intelligence"]
```

This AI integration transforms the platform from reactive monitoring into proactive maritime operational intelligence.