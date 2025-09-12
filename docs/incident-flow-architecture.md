# Incident Creation Data Flow Architecture

This document describes the complete data flow for incident creation in the AIOps NAAS platform, addressing the issues identified in #105.

## Overview

The incident creation process involves multiple services working together to detect anomalies, correlate events, and create actionable incidents. This architecture distinguishes between ship-local and fleet-global services.

## Service Architecture

### Ship-Local Services (Edge Processing)
These services run locally on each ship and handle autonomous operations with offline capability.

#### Tier 1: Data Collection
```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA COLLECTION LAYER                         │
├─────────────────────────────────────────────────────────────────────────┤
│  📡 SNMP Collectors    │  📊 Host Metrics     │  📝 Application Logs    │
│  (Network Devices)     │  (System Resources)   │  (Service Logs)         │
│  ↓                     │  ↓                   │  ↓                      │
│  Port: Various         │  Built-in Vector     │  NATS: logs.applications│
│  Purpose: Network      │  Purpose: System     │  Purpose: App           │
│  telemetry            │  monitoring          │  monitoring             │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Tier 2: Data Processing & Routing
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          VECTOR DATA ROUTER                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Service: vector                                                        │
│  Port: 8686 (API), 1514/1516 (Syslog)                                 │
│  Purpose: Log/metric collection, filtering, and routing                │
│  Upstream: ⬆️ SNMP, Host Metrics, Syslog, App Logs                     │
│  Downstream: ⬇️ ClickHouse, NATS (anomalous logs only)                 │
│                                                                         │
│  🔍 FILTERING LOGIC:                                                    │
│  • Normal logs → ClickHouse storage only                               │
│  • ERROR/CRITICAL/WARNING logs → ClickHouse + NATS                     │
│  • INFO logs with error patterns → NATS (if match critical patterns)   │
│                                                                         │
│  📊 Data Flow:                                                          │
│  1️⃣ Raw logs/metrics → Vector transforms → Structured data            │
│  2️⃣ All data → ClickHouse (logs.raw table)                           │
│  3️⃣ Anomalous data → NATS (logs.anomalous subject)                    │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Tier 3: Data Storage  
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SHIP LOCAL STORAGE                              │
├─────────────────────────────────────────────────────────────────────────┤
│  🗄️ ClickHouse          │  📈 VictoriaMetrics    │  🔄 NATS JetStream   │
│  Port: 8123/9000        │  Port: 8428             │  Port: 4222          │
│  Purpose: Log storage   │  Purpose: Metric storage│  Purpose: Event bus  │
│  Upstream: ⬆️ Vector     │  Upstream: ⬆️ VmAgent   │  Upstream: ⬆️ Vector  │
│  Downstream: ⬇️ Queries │  Downstream: ⬇️ Queries │  Downstream: ⬇️ Subs │
│                         │                         │                      │
│  • logs.raw table       │  • System metrics       │  • logs.anomalous   │
│  • logs.incidents table │  • Custom metrics       │  • anomaly.detected  │
│  • Historical data      │  • Prometheus format    │  • incidents.created│
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier 4: AI/ML Processing
```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ANOMALY DETECTION SERVICE                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Service: anomaly-detection                                             │
│  Port: 8082                                                             │  
│  Purpose: Real-time anomaly detection with historical context          │
│  Upstream: ⬆️ NATS (logs.anomalous), VictoriaMetrics, ClickHouse       │
│  Downstream: ⬇️ NATS (anomaly.detected)                                │
│                                                                         │
│  🧠 AI/ML INTEGRATION:                                                  │
│  • Statistical anomaly detection (Z-score, EWMA, MAD)                  │
│  • Historical baseline comparison                                       │
│  • Pattern recognition for log anomalies                               │
│  • CRITICAL FIX: Severity filtering (no INFO/DEBUG incidents)          │
│                                                                         │
│  📋 Processing Logic:                                                   │
│  1️⃣ Receive log from Vector (ERROR/CRITICAL/WARNING only)             │
│  2️⃣ Apply severity filters and operational message exclusion           │
│  3️⃣ Extract ship_id, device_id, tracking_id from log data             │
│  4️⃣ Calculate appropriate anomaly score based on severity              │
│  5️⃣ Publish enriched anomaly event to NATS                            │
│                                                                         │
│  📊 Metrics Processing:                                                 │
│  1️⃣ Query VictoriaMetrics for system metrics every 10s                │
│  2️⃣ Query ClickHouse for historical baselines                         │
│  3️⃣ Apply statistical detectors with combined scoring                  │
│  4️⃣ Publish metric anomalies above threshold                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier 5: Event Correlation  
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BENTHOS CORRELATION ENGINE                      │
├─────────────────────────────────────────────────────────────────────────┤
│  Service: benthos                                                       │
│  Port: 4195                                                             │
│  Purpose: Multi-source event correlation and incident creation         │
│  Upstream: ⬆️ NATS (anomaly.detected, anomaly.detected.enriched)       │
│  Downstream: ⬇️ NATS (incidents.created)                               │
│                                                                         │
│  🔍 CRITICAL FIXES APPLIED:                                             │
│  • Early severity filtering (drop INFO/DEBUG events)                   │
│  • Enhanced field mapping (ship_id, device_id, metric_value)           │
│  • Improved suppression logic (granular keys, longer TTL)              │
│  • Complete metadata propagation                                        │
│                                                                         │
│  🔄 Processing Pipeline:                                                │
│  1️⃣ Input validation & severity filtering                              │
│  2️⃣ Field normalization & metadata extraction                          │
│  3️⃣ Ship_id resolution with device registry integration                │
│  4️⃣ Context enrichment & correlation cache storage                     │
│  5️⃣ Cross-source correlation (logs + metrics + network)               │
│  6️⃣ Incident classification & severity calculation                     │
│  7️⃣ Duplicate suppression (15min for similar, 30min for tracking)     │
│  8️⃣ Final incident creation with complete metadata                     │
│                                                                         │
│  📊 Correlation Types:                                                  │
│  • CPU + Memory correlation → Resource pressure incidents              │
│  • App logs + System metrics → Application-system correlation          │
│  • Weather + Network → Weather degradation incidents                   │
│  • Multi-service failures → Cascading failure correlation              │
└─────────────────────────────────────────────────────────────────────────┘
```

## Fleet-Global Services (Shore/Control Plane)

### Tier 6: Incident Management
```
┌─────────────────────────────────────────────────────────────────────────┐
│                        INCIDENT API SERVICE                             │
├─────────────────────────────────────────────────────────────────────────┤
│  Service: incident-api                                                  │
│  Port: 8083                                                             │
│  Purpose: Incident lifecycle management and API access                 │
│  Upstream: ⬆️ NATS (incidents.created), Device Registry                │
│  Downstream: ⬇️ ClickHouse (logs.incidents), REST API                  │
│                                                                         │
│  🔧 CRITICAL FIX: Enhanced ship_id resolution                          │
│  1️⃣ Try device registry lookup by hostname                            │
│  2️⃣ Use existing ship_id if valid                                     │
│  3️⃣ Derive from hostname (e.g., dhruv-system-01 → dhruv-ship)        │
│  4️⃣ Ultimate fallback to unknown-ship                                  │
│                                                                         │
│  📊 Data Validation & Storage:                                         │
│  • Validate metric_value, anomaly_score as numbers                     │
│  • Map info/debug severity to low                                       │
│  • Ensure proper service name handling                                  │
│  • Store complete metadata, timeline, and runbooks                     │
│                                                                         │
│  🌐 REST API Endpoints:                                                │
│  • GET /api/incidents - List incidents with filtering                  │
│  • GET /api/incidents/{id} - Get incident details                      │
│  • PUT /api/incidents/{id} - Update incident status                    │
│  • GET /api/incidents/summary - Dashboard summary                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tier 7: Fleet Services
```
┌─────────────────────────────────────────────────────────────────────────┐
│                      FLEET MANAGEMENT SERVICES                          │
├─────────────────────────────────────────────────────────────────────────┤
│  🚢 Device Registry      │  📊 Fleet Aggregation   │  🔧 Remediation     │
│  Port: 8080              │  Port: 8084              │  Port: 8085         │
│  Purpose: Ship/device    │  Purpose: Cross-ship     │  Purpose: Automated │
│  mapping                 │  analytics               │  response actions   │
│  Upstream: Manual config │  Upstream: All ships     │  Upstream: Incidents│
│  Downstream: Ship lookup │  Downstream: Analytics   │  Downstream: Actions│
└─────────────────────────────────────────────────────────────────────────┘
```

## Complete Data Flow Summary

### Primary Incident Creation Path:
```
1. 📊 Ship Systems → Vector → ClickHouse + NATS (filtered)
2. 🤖 NATS → Anomaly Detection (severity filtered) → Enriched anomalies  
3. 🔄 Anomalies → Benthos Correlation (suppression) → Unified incidents
4. 🏪 Incidents → Incident API (ship_id resolution) → ClickHouse storage
5. 🌐 Storage → REST API → Ops Console/Grafana dashboards
```

### Key Integration Points:
- **AI Integration**: Anomaly detection service applies ML algorithms
- **Maritime Context**: Weather correlation, satellite impact assessment  
- **Correlation Engine**: Multi-source event correlation for comprehensive incidents
- **Fleet Management**: Cross-ship analytics and remediation orchestration

### Critical Fixes Applied:

#### 🚫 **Severity Filtering**
- Anomaly detection: Skip INFO/DEBUG logs unless high anomaly score
- Benthos: Early filtering pipeline to drop low-severity events
- Incident API: Map info/debug to low severity

#### 🔍 **Metadata Preservation**  
- Enhanced field mapping for ship_id, device_id, metric_name, metric_value
- Complete timeline and correlation metadata in incidents
- Tracking_id propagation for full traceability

#### 🛡️ **Duplicate Suppression**
- Granular suppression keys (incident_type + ship_id + metric + service)
- Extended TTL (15 min for similar incidents, 30 min for tracking-based)
- Multiple suppression strategies for comprehensive deduplication

#### 📋 **Enhanced Runbooks**
- Context-aware runbook suggestions based on incident type
- Maritime-specific runbooks for weather, communication issues
- Service-specific investigation procedures

This architecture ensures that only genuine anomalies create incidents, with complete metadata and effective deduplication, significantly reducing incident volume while maintaining operational visibility.