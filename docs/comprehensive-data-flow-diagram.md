# Comprehensive Data Flow Diagram - AIOps NAAS Platform

This document shows the complete data flow architecture with input/output types for each service in the maritime AIOps platform.

## Network Device Data Collection Architecture

### How Network Device Data is Collected (SNMP)

**Critical Understanding**: We don't need to deploy code ON network devices (switches, bridges, firewalls, etc.). Instead, we use **SNMP (Simple Network Management Protocol)** which is a standard protocol that most network devices support natively.

**SNMP Data Collection Process:**
1. **No Code Deployment Required**: Network devices (switches, bridges, firewalls) come with SNMP enabled by default
2. **Remote Querying**: Our `network-device-collector` service queries devices remotely using SNMP OIDs (Object Identifiers)
3. **Standard Protocol**: SNMP is an industry-standard protocol - works with Cisco, Juniper, HP, Fortinet, etc.
4. **Configuration Only**: We only need to configure SNMP community strings (like "public" or "private") on the devices
5. **No Agent Installation**: The devices act as SNMP agents automatically - no software installation needed

**What Data We Collect via SNMP:**
- **Interface metrics**: Port utilization, error rates, packet counts
- **Device health**: CPU, memory, temperature, power supply status  
- **Network topology**: LLDP/CDP neighbor discovery
- **Vendor-specific data**: Using vendor MIBs (Management Information Bases)

---

## Complete Data Flow Architecture

### Level 1: Data Collection Layer

```mermaid
graph TD
    %% Data Sources
    A1["Ship Systems<br/>CPU, Memory, Disk"] --> A2["node-exporter<br/>Port: 9100"]
    B1["Application Logs<br/>Docker containers,<br/>System logs"] --> B2["Vector Log Router<br/>Port: 8686"]
    C1["Network Devices<br/>Switches, Routers,<br/>Firewalls, WiFi"] --> C2["network-device-collector<br/>Port: 8080<br/>SNMP Protocol"]
    D1["VSAT Equipment<br/>Satellite modems,<br/>RF systems"] --> D2["VSAT Data Simulator<br/>SNR, BER, Signal"]
    E1["Ship Telemetry<br/>GPS, Weather,<br/>Navigation"] --> E2["Ship Data Simulator<br/>Location, Heading, etc."]
    F1["External APIs<br/>Weather, Maritime<br/>AIS data"] --> F2["External API Collector<br/>HTTP REST calls"]

    %% Collection outputs to storage
    A2 -->|"Prometheus Metrics"| G1["VictoriaMetrics<br/>Port: 8428"]
    B2 -->|"Structured Logs"| G2["ClickHouse<br/>Port: 8123"]
    C2 -->|"SNMP Metrics"| G1
    D2 -->|"Telemetry Data"| G3["NATS JetStream<br/>Port: 4222"]
    E2 -->|"Ship Data"| G3
    F2 -->|"External Data"| G3
```

**Input/Output Summary - Data Collection:**
- **Input**: Raw telemetry from ships, network devices, applications, external sources
- **Output**: Structured metrics (VictoriaMetrics), logs (ClickHouse), streaming data (NATS)

### Level 2: Data Enrichment and Correlation (Level 1 Correlation)

```mermaid
graph TD
    %% Storage to enrichment
    G1["VictoriaMetrics"] --> H1["benthos-enrichment<br/>Port: 4195"]
    G2["ClickHouse"] --> H1
    G3["NATS JetStream"] --> H1

    %% AI/ML Integration
    ML1["Ollama LLM<br/>Port: 11434"] --> H1
    ML2["Qdrant Vector DB<br/>Port: 6333"] --> ML3["LangChain RAG<br/>Port: 8090"]
    G2 --> ML2
    ML3 --> H1

    %% Enrichment processing
    H1 --> H2["Raw Data Correlation<br/>- Weather + Satellite<br/>- System + Network<br/>- Location + Performance<br/>- AI Context Enrichment"]
    
    %% Enriched data outputs
    H2 -->|"Enriched Metrics"| I1["NATS: telemetry.enriched.*"]
    H2 -->|"Context-Aware Events"| I2["NATS: events.correlated.*"]
    H2 -->|"Operational Status"| I3["NATS: status.operational.*"]
```

**Input/Output Summary - Level 1 Enrichment:**
- **Input**: Raw metrics, logs, telemetry from storage systems + AI context
- **Output**: Enriched and correlated data streams with maritime context and AI insights

## AI/ML Integration Architecture

### AI/ML Stack Components

**Ollama LLM (Local Language Model)**
- **Port**: 11434
- **Function**: Local AI inference for context analysis, correlation suggestions, and solution generation
- **Integration Points**: Data enrichment, anomaly detection, correlation engine, remediation service
- **Maritime Context**: Understands ship operations, weather impacts, satellite communications

**Qdrant Vector Database**
- **Port**: 6333  
- **Function**: Stores vector embeddings of logs, incidents, and operational procedures
- **Integration Points**: Ingests from ClickHouse logs, serves LangChain RAG system
- **Maritime Context**: Maritime-specific embeddings for operational procedures and incident patterns

**LangChain RAG System**
- **Port**: 8090
- **Function**: Retrieval-Augmented Generation for contextual information retrieval
- **Integration Points**: Connects Qdrant with Ollama, enriches data streams with relevant context
- **Maritime Context**: Retrieves relevant maritime procedures, weather correlations, equipment documentation

### AI/ML Functions in Each Service

**Level 1 Enrichment (benthos-enrichment)**
- AI enhances raw data correlation with semantic understanding
- Ollama provides context about maritime operations based on current conditions
- RAG system retrieves relevant historical patterns for similar operational scenarios

**Anomaly Detection (enhanced-anomaly-detection)**  
- AI-enhanced pattern recognition beyond statistical thresholds
- Ollama analyzes anomaly context in maritime operational terms
- Semantic understanding of complex multi-system interactions

**Level 2 Correlation (benthos correlation)**
- AI suggests correlation patterns based on historical incident analysis
- Ollama provides natural language explanations of correlation reasoning
- Pattern matching enhanced with semantic understanding of maritime operations

**Remediation Service**
- AI generates solution recommendations based on incident context
- Ollama creates natural language explanations for recommended actions
- RAG retrieves relevant procedures from maritime operational documentation

**Fleet Intelligence Services**
- ML-powered predictive analytics for capacity and performance forecasting
- AI-enhanced cross-ship benchmarking with contextual analysis
- Semantic analysis of operational patterns across fleet

### AI Data Flow

```mermaid
graph TD
    %% AI Data Sources
    A1["ClickHouse Logs"] --> A2["Text Processing"]
    A3["Incident Patterns"] --> A2
    A4["Maritime Procedures"] --> A2
    
    %% Embedding Generation
    A2 --> B1["Vector Embeddings"]
    B1 --> B2["Qdrant Vector DB<br/>Port: 6333"]
    
    %% Context Retrieval
    B2 --> C1["LangChain RAG<br/>Port: 8090"]
    C1 --> C2["Context Retrieval<br/>Semantic Search"]
    
    %% AI Inference
    C2 --> D1["Ollama LLM<br/>Port: 11434"]
    D1 --> D2["AI Inference<br/>Context Analysis<br/>Solution Generation"]
    
    %% Integration Points
    D2 -->|"AI Context"| E1["benthos-enrichment"]
    D2 -->|"Pattern Recognition"| E2["enhanced-anomaly-detection"] 
    D2 -->|"Correlation Suggestions"| E3["benthos correlation"]
    D2 -->|"Solution Recommendations"| E4["remediation-service"]
    D2 -->|"Predictive Insights"| E5["Fleet Intelligence"]
```

### AI/ML Value Proposition

**Enhanced Context Understanding**
- Natural language processing of maritime operational context
- Semantic understanding of relationships between weather, satellite, and system performance
- Historical pattern recognition for similar operational scenarios

**Intelligent Correlation**
- AI identifies non-obvious correlations between disparate system events
- Semantic clustering of related anomalies into meaningful operational incidents
- Context-aware incident classification with maritime operational understanding

**Proactive Remediation** 
- AI generates contextual solution recommendations based on historical success patterns
- Natural language explanations help operators understand recommended actions
- Learning from successful and failed remediation attempts

**Fleet-Wide Intelligence**
- Cross-ship pattern analysis for fleet-wide operational insights
- Predictive modeling enhanced with semantic understanding of operational context
- AI-powered benchmarking with contextual analysis of performance differences

### Level 3: Anomaly Detection

```mermaid
graph TD
    %% Anomaly detection services
    I1["NATS: telemetry.enriched.*"] --> J1["enhanced-anomaly-detection<br/>Port: 8082"]
    I1 --> J2["anomaly-detection<br/>Port: 8081<br/>Basic Detection"]
    I2["NATS: events.correlated.*"] --> J1
    ML1["Ollama LLM<br/>AI Insights"] --> J1
    
    %% Detection processing
    J1 --> J3["Context-Aware Detection<br/>- Weather-adjusted thresholds<br/>- System load correlation<br/>- Maritime operations context<br/>- AI-Enhanced Pattern Recognition"]
    J2 --> J4["Standard Detection<br/>- Statistical analysis<br/>- Time series patterns"]
    
    %% Anomaly outputs
    J3 -->|"Enhanced Anomalies"| K1["NATS: anomaly.detected.enriched"]
    J4 -->|"Basic Anomalies"| K2["NATS: anomaly.detected"]
```
```

**Input/Output Summary - Anomaly Detection:**
- **Input**: Enriched telemetry and correlated events
- **Output**: Anomaly events (basic and context-aware)

### Level 4: Anomaly Correlation (Level 2 Correlation)

```mermaid
graph TD
    %% Anomaly correlation
    K1["NATS: anomaly.detected.enriched"] --> L1["Benthos Correlation<br/>Port: 4195"]
    K2["NATS: anomaly.detected"] --> L1
    ML1["Ollama LLM<br/>AI Correlation Suggestions"] --> L1
    
    %% Correlation logic
    L1 --> L2["Anomaly Correlation Engine<br/>- Time window grouping<br/>- Causal relationship detection<br/>- Maritime scenario correlation<br/>- AI-Assisted Pattern Matching"]
    
    %% Correlated incident creation
    L2 -->|"Unified Incidents"| M1["NATS: incidents.correlated"]
    L2 -->|"Individual Anomalies"| M2["NATS: incidents.single"]
```

**Input/Output Summary - Level 2 Correlation:**
- **Input**: Individual anomaly events (basic and enriched)
- **Output**: Correlated incident groups and individual incidents

### Level 5: Incident Management

```mermaid
graph TD
    %% Incident API processing
    M1["NATS: incidents.correlated"] --> N1["incident-api<br/>Port: 8083"]
    M2["NATS: incidents.single"] --> N1
    
    %% Incident lifecycle
    N1 --> N2["Incident Lifecycle Manager<br/>- Create incidents<br/>- Update status<br/>- Track resolution"]
    
    %% Incident outputs
    N2 -->|"REST API"| O1["GET /api/incidents<br/>POST /api/incidents<br/>PUT /api/incidents/{id}"]
    N2 -->|"Incident Events"| O2["NATS: incidents.lifecycle.*"]
```

**Input/Output Summary - Incident Management:**
- **Input**: Correlated and individual incidents from NATS
- **Output**: REST API for incident CRUD, lifecycle events

### Level 6: Alerting and Notification

```mermaid
graph TD
    %% Alerting pipeline
    O2["NATS: incidents.lifecycle.*"] --> P1["VMAlert<br/>Port: 8080"]
    G1["VictoriaMetrics"] --> P1
    
    %% Alert processing
    P1 --> P2["Alert Rules Engine<br/>- Threshold monitoring<br/>- Maritime-specific rules<br/>- Critical path monitoring"]
    
    %% Alert manager
    P2 -->|"Firing Alerts"| Q1["Alertmanager<br/>Port: 9093"]
    
    %% Notification outputs
    Q1 -->|"Email Alerts"| R1["MailHog<br/>Port: 8025<br/>SMTP Server"]
    Q1 -->|"Webhook Notifications"| R2["HTTP Webhooks<br/>External systems"]
    Q1 -->|"NATS Notifications"| R3["NATS: alerts.notifications.*"]
```

**Input/Output Summary - Alerting:**
- **Input**: Incident lifecycle events and metrics
- **Output**: Email alerts, webhooks, notification streams

### Level 7: Remediation and Automation

```mermaid
graph TD
    %% Remediation triggers
    R3["NATS: alerts.notifications.*"] --> S1["remediation-service<br/>Port: 8084"]
    O1["Incident API"] --> S1
    ML1["Ollama LLM<br/>Solution Generation"] --> S1
    
    %% Remediation processing
    S1 --> S2["Maritime Playbook Engine<br/>- OPA policy evaluation<br/>- Automated remediation<br/>- Human approval workflows<br/>- AI-Generated Solutions"]
    
    %% Remediation outputs
    S2 -->|"Remediation Actions"| T1["System Commands<br/>Service restarts,<br/>Config changes"]
    S2 -->|"Status Updates"| T2["NATS: remediation.status.*"]
    S2 -->|"Approval Requests"| T3["Human Operators<br/>Manual intervention"]
```

**Input/Output Summary - Remediation:**
- **Input**: Alert notifications and incident data
- **Output**: Automated remediation actions, status updates, approval requests

### Level 8: Monitoring and Visualization

```mermaid
graph TD
    %% Monitoring data sources
    G1["VictoriaMetrics"] --> U1["Grafana<br/>Port: 3000"]
    G2["ClickHouse"] --> U1
    T2["NATS: remediation.status.*"] --> U1
    O2["NATS: incidents.lifecycle.*"] --> U1
    
    %% Visualization outputs
    U1 --> U2["Maritime Dashboards<br/>- System health<br/>- Network topology<br/>- Incident timeline<br/>- Correlation analysis"]
    
    %% External access
    U2 -->|"HTTP Dashboard"| V1["Web Interface<br/>Ship operators,<br/>Fleet management"]
```

**Input/Output Summary - Monitoring:**
- **Input**: Metrics, logs, incident data, remediation status
- **Output**: Interactive dashboards and visualizations

### Level 9: Intelligence and Analytics

```mermaid
graph TD
    %% Intelligence services
    G1["VictoriaMetrics"] --> W1["capacity-forecasting<br/>Port: 8085"]
    O1["Incident API"] --> W2["cross-ship-benchmarking<br/>Port: 8086"]
    U1["Grafana"] --> W3["fleet-aggregation<br/>Port: 8087"]
    ML1["Ollama LLM<br/>ML Predictions"] --> W1
    ML1 --> W2
    
    %% Analytics processing
    W1 --> W4["Predictive Analytics<br/>- Capacity planning<br/>- Performance forecasting<br/>- Resource optimization<br/>- ML-Powered Predictions"]
    W2 --> W5["Fleet Intelligence<br/>- Cross-ship comparison<br/>- Best practice sharing<br/>- Performance benchmarking<br/>- AI-Enhanced Analysis"]
    W3 --> W6["Fleet Operations<br/>- Multi-ship coordination<br/>- Resource allocation<br/>- Route optimization"]
    
    %% Intelligence outputs
    W4 -->|"Forecasts"| X1["Management Reports"]
    W5 -->|"Benchmarks"| X2["Operational Insights"]
    W6 -->|"Coordination Data"| X3["Fleet Commands"]
```

**Input/Output Summary - Intelligence:**
- **Input**: Historical metrics, incident patterns, fleet data
- **Output**: Forecasts, benchmarks, operational intelligence

---

## Complete Data Flow Summary

### Primary Data Flow Path:
1. **Raw Collection**: Ship systems → Collectors → Storage (VictoriaMetrics/ClickHouse/NATS)
2. **Level 1 Enrichment**: Storage → benthos-enrichment → Correlated telemetry streams
3. **Anomaly Detection**: Enriched data → Detection services → Anomaly events
4. **Level 2 Correlation**: Anomaly events → Benthos correlation → Unified incidents  
5. **Incident Management**: Incidents → incident-api → REST API + lifecycle tracking
6. **Alerting**: Incidents → VMAlert → Alertmanager → Notifications (email/webhook)
7. **Remediation**: Alerts → remediation-service → Automated actions + approvals
8. **Visualization**: All data → Grafana → Maritime operational dashboards
9. **Intelligence**: Historical data → Analytics services → Predictive insights

### Key Integration Points:
- **NATS JetStream**: Primary message bus for all real-time data
- **VictoriaMetrics**: Time-series metrics storage and querying
- **ClickHouse**: Log storage and analytical queries  
- **Grafana**: Unified visualization of all data sources
- **REST APIs**: External integration and manual operations

### Maritime-Specific Features:
- **Environmental Context**: Weather correlation with network performance
- **Critical Path Monitoring**: Satellite and navigation system prioritization
- **Ship Operations Integration**: Location, heading, operational mode awareness
- **Fleet Coordination**: Cross-ship data sharing and benchmarking
- **Offline Resilience**: Local processing with shore synchronization

This architecture provides complete observability and automated operations for maritime environments with comprehensive network infrastructure monitoring.