# Sequential Event Processing Pipeline - Visual Diagrams

## Complete Pipeline Flow

```mermaid
graph TB
    subgraph "Data Sources"
        A1[Syslog UDP/TCP]
        A2[Application Logs]
        A3[File Logs]
    end
    
    subgraph "Stage 1: Log Ingestion"
        V[Vector<br/>Port: 8686]
    end
    
    subgraph "Stage 2: Basic Anomaly Detection"
        AD[Anomaly Detection Service<br/>Port: 8080<br/>ML: Rule-based + Statistical]
    end
    
    subgraph "Stage 3: Level 1 Enrichment"
        BE[Benthos Enrichment<br/>Port: 4196<br/>AI: LLM/Ollama Context]
    end
    
    subgraph "Stage 4: Level 2 Advanced Analysis"
        EA[Enhanced Anomaly Detection<br/>Port: 9082<br/>AI: LLM Grouping + History]
    end
    
    subgraph "Stage 5: Incident Formation"
        BC[Benthos Correlation<br/>Port: 4195<br/>AI: LLM Root Cause]
    end
    
    subgraph "Stage 6: Storage & API"
        IA[Incident API<br/>Port: 9081<br/>REST API]
        CH[(ClickHouse<br/>logs.incidents)]
    end
    
    subgraph "Supporting Infrastructure"
        NATS[NATS JetStream<br/>Port: 4222<br/>Message Bus]
        DR[Device Registry<br/>Port: 8083<br/>Context Data]
        OL[Ollama<br/>Port: 11434<br/>LLM Inference]
    end
    
    A1 --> V
    A2 --> V
    A3 --> V
    
    V -->|logs.raw| CH
    V -->|logs.anomalous<br/>ERROR/WARNING only| NATS
    NATS --> AD
    
    AD -->|anomaly.detected| NATS
    NATS --> BE
    
    BE -->|anomaly.detected.enriched| NATS
    BE -.->|Query Device Info| DR
    BE -.->|LLM Analysis| OL
    NATS --> EA
    
    EA -->|anomaly.detected.enriched.final| NATS
    EA -.->|LLM Grouping| OL
    NATS --> BC
    
    BC -->|incidents.created| NATS
    BC -.->|LLM Root Cause| OL
    NATS --> IA
    
    IA --> CH
    
    style V fill:#e1f5ff
    style AD fill:#fff4e6
    style BE fill:#e8f5e9
    style EA fill:#f3e5f5
    style BC fill:#fce4ec
    style IA fill:#fff9c4
    style NATS fill:#ffebee
    style OL fill:#e0f2f1
```

## NATS Topic Flow

```mermaid
graph LR
    subgraph "NATS Topics (Sequential)"
        T1[logs.anomalous]
        T2[anomaly.detected]
        T3[anomaly.detected.enriched]
        T4[anomaly.detected.enriched.final]
        T5[incidents.created]
    end
    
    S1[Vector] -->|Publish| T1
    T1 -->|Subscribe| S2[Anomaly Detection]
    S2 -->|Publish| T2
    T2 -->|Subscribe| S3[Benthos Enrichment]
    S3 -->|Publish| T3
    T3 -->|Subscribe| S4[Enhanced Anomaly]
    S4 -->|Publish| T4
    T4 -->|Subscribe| S5[Benthos Correlation]
    S5 -->|Publish| T5
    T5 -->|Subscribe| S6[Incident API]
    
    style T1 fill:#ffcdd2
    style T2 fill:#f8bbd0
    style T3 fill:#e1bee7
    style T4 fill:#d1c4e9
    style T5 fill:#c5cae9
```

## Service Dependency Chain

```mermaid
graph TD
    NATS[NATS<br/>Message Bus]
    CH[ClickHouse<br/>Database]
    DR[Device Registry<br/>Context]
    OL[Ollama<br/>LLM]
    
    V[Vector] --> NATS
    
    AD[Anomaly Detection<br/>Port: 8080] --> NATS
    
    BE[Benthos Enrichment<br/>Port: 4196] --> NATS
    BE --> AD
    BE -.-> DR
    BE -.-> OL
    
    EA[Enhanced Anomaly<br/>Port: 9082] --> NATS
    EA --> BE
    EA -.-> OL
    
    BC[Benthos Correlation<br/>Port: 4195] --> NATS
    BC --> EA
    BC --> CH
    BC -.-> OL
    
    IA[Incident API<br/>Port: 9081] --> NATS
    IA --> BC
    IA --> CH
    
    style NATS fill:#ffebee
    style CH fill:#e3f2fd
    style DR fill:#f1f8e9
    style OL fill:#e0f2f1
```

## Data Enrichment Flow

```mermaid
graph LR
    subgraph "Input: Basic Anomaly"
        I[anomaly_id<br/>tracking_id<br/>ship_id<br/>device_id<br/>log_message<br/>severity]
    end
    
    subgraph "Level 1: Benthos Enrichment"
        E1[+ Device context<br/>+ Ship location<br/>+ Maritime context<br/>+ Weather correlation<br/>+ Operational status<br/>+ Investigation guidance]
    end
    
    subgraph "Level 2: Enhanced Analysis"
        E2[+ Anomaly grouping<br/>+ Historical patterns<br/>+ Time correlation<br/>+ Risk assessment<br/>+ Urgency level<br/>+ Enhanced scoring]
    end
    
    subgraph "Level 3: Incident Formation"
        E3[+ Deduplication<br/>+ Root cause analysis<br/>+ Runbook selection<br/>+ Business impact<br/>+ Remediation plan<br/>+ Incident metadata]
    end
    
    subgraph "Output: Complete Incident"
        O[incident_id<br/>All anomaly data<br/>All enrichment data<br/>Complete context<br/>Recommended actions<br/>Tracking history]
    end
    
    I --> E1
    E1 --> E2
    E2 --> E3
    E3 --> O
    
    style I fill:#ffebee
    style E1 fill:#e8f5e9
    style E2 fill:#f3e5f5
    style E3 fill:#fce4ec
    style O fill:#fff9c4
```

## AI/ML Integration Points

```mermaid
graph TB
    subgraph "LLM/Ollama Integration"
        LLM[Ollama Server<br/>Port: 11434<br/>Models: Mistral, Mixtral, Qwen2]
    end
    
    subgraph "Enrichment Stage (L1)"
        E1[Maritime Context<br/>Error Interpretation<br/>Investigation Guidance]
        E1F[Rule-based Fallback]
    end
    
    subgraph "Enhanced Analysis Stage (L2)"
        E2[Anomaly Grouping<br/>Historical Analysis<br/>Risk Assessment]
        E2F[Statistical Fallback]
    end
    
    subgraph "Correlation Stage (L3)"
        E3[Root Cause Analysis<br/>Runbook Selection<br/>Impact Assessment]
        E3F[Template Fallback]
    end
    
    LLM -.->|Success| E1
    LLM -.->|Success| E2
    LLM -.->|Success| E3
    
    LLM -.->|Failure| E1F
    LLM -.->|Failure| E2F
    LLM -.->|Failure| E3F
    
    E1F -.->|Fallback| E1
    E2F -.->|Fallback| E2
    E3F -.->|Fallback| E3
    
    style LLM fill:#e0f2f1
    style E1 fill:#e8f5e9
    style E2 fill:#f3e5f5
    style E3 fill:#fce4ec
    style E1F fill:#ffccbc
    style E2F fill:#ffccbc
    style E3F fill:#ffccbc
```

## Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Observability Layer                       │
│  Grafana (3000) │ Prometheus │ VictoriaMetrics │ ClickHouse UI │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Application Services                         │
│  Device Registry │ Link Health │ Remediation │ Onboarding      │
│     (8083)       │    (8082)    │  (8084)     │   (8090)       │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│              Sequential Event Processing Pipeline                │
│                                                                  │
│  Vector → Anomaly Detection → Benthos Enrichment →             │
│  (8686)      (8080)              (4196)                         │
│                                                                  │
│  Enhanced Anomaly → Benthos Correlation → Incident API         │
│     (9082)             (4195)                (9081)            │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Message Bus Layer                           │
│              NATS JetStream (4222, 8222)                        │
│  Topics: logs.anomalous → anomaly.detected →                   │
│          anomaly.detected.enriched →                            │
│          anomaly.detected.enriched.final →                      │
│          incidents.created                                      │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Storage & AI/ML Layer                         │
│  ClickHouse (8123, 9000) │ VictoriaMetrics (8428)             │
│  Qdrant (6333)           │ Ollama (11434)                     │
└─────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────┐
│                       Data Sources                               │
│  Syslog │ Applications │ Network Devices │ VSAT Modems         │
└─────────────────────────────────────────────────────────────────┘
```

## Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| **Pipeline Services** | | | |
| Vector | 8686 | HTTP | Metrics & health |
| Vector | 1514 | UDP | Syslog input |
| Anomaly Detection | 8080 | HTTP | Health & metrics |
| Benthos Enrichment | 4196 | HTTP | Ping & stats |
| Enhanced Anomaly | 9082 | HTTP | Health |
| Benthos Correlation | 4195 | HTTP | Ping & stats |
| Incident API | 9081 | HTTP | REST API |
| **Infrastructure** | | | |
| NATS | 4222 | NATS | Client connections |
| NATS Monitor | 8222 | HTTP | Monitoring |
| ClickHouse | 8123 | HTTP | Query interface |
| ClickHouse | 9000 | TCP | Native protocol |
| VictoriaMetrics | 8428 | HTTP | Query & write |
| Grafana | 3000 | HTTP | UI |
| Ollama | 11434 | HTTP | LLM API |
| Qdrant | 6333 | HTTP | Vector DB |
| **Application Services** | | | |
| Device Registry | 8083 | HTTP | REST API |
| Link Health | 8082 | HTTP | Predictions |
| Remediation | 8084 | HTTP | Automation |
| Onboarding | 8090 | HTTP | Workflow UI |

## Health Check Commands

```bash
# Pipeline Services
curl http://localhost:8686/health     # Vector
curl http://localhost:8080/health     # Anomaly Detection
curl http://localhost:4196/ping       # Benthos Enrichment
curl http://localhost:9082/health     # Enhanced Anomaly
curl http://localhost:4195/ping       # Benthos Correlation
curl http://localhost:9081/health     # Incident API

# Infrastructure
curl http://localhost:4222/healthz    # NATS
curl http://localhost:8222/varz       # NATS Monitor
curl http://localhost:8123/ping       # ClickHouse
curl http://localhost:8428/health     # VictoriaMetrics
curl http://localhost:3000/api/health # Grafana
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:6333/           # Qdrant
```

## Testing the Pipeline

### Quick Test
```bash
# Send test syslog message
echo "<11>$(date '+%b %d %H:%M:%S') ship-test app: ERROR TEST-$(uuidgen | cut -d'-' -f1) Test error message" | nc -u localhost 1514

# Wait for processing
sleep 30

# Check incident creation
curl http://localhost:9081/api/v1/incidents | jq
```

### Comprehensive Test
```bash
# Run full end-to-end verification
./scripts/verify_modular_pipeline.sh

# Expected output: 
# - All services healthy
# - Test message processed through all stages
# - Tracking ID preserved
# - Incident created in ClickHouse
# - REST API returns incident data
```

## Troubleshooting

### Check Service Logs
```bash
docker logs aiops-vector
docker logs aiops-anomaly-detection
docker logs aiops-benthos-enrichment
docker logs aiops-enhanced-anomaly-detection
docker logs aiops-benthos-correlation
docker logs aiops-incident-api
```

### Monitor NATS Topics
```bash
# View messages on each topic (requires nats CLI)
nats sub "logs.anomalous"
nats sub "anomaly.detected"
nats sub "anomaly.detected.enriched"
nats sub "anomaly.detected.enriched.final"
nats sub "incidents.created"
```

### Check ClickHouse Data
```bash
# Check raw logs
docker exec aiops-clickhouse clickhouse-client --query="SELECT count() FROM logs.raw"

# Check incidents
docker exec aiops-clickhouse clickhouse-client --query="SELECT * FROM logs.incidents ORDER BY created_at DESC LIMIT 5 FORMAT Pretty"
```

## References

- [Sequential Pipeline Architecture](sequential-pipeline-architecture.md) - Detailed design
- [Sequential Pipeline Validation](SEQUENTIAL_PIPELINE_VALIDATION.md) - Validation report
- [Architecture Overview](ARCHITECTURE_OVERVIEW.md) - Complete system architecture
- [Quick Reference](quick-reference.md) - Command reference

---

**Last Updated**: October 2, 2025  
**Architecture Version**: v1.0  
**Status**: Production Ready
