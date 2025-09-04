# AIOps NAAS - Comprehensive Data Flow Architecture

## Overview

This document provides a complete analysis of the AIOps NAAS data flow architecture, addressing key questions about data sources, processing, storage, visualization, and user-friendly correlation explanation.

## 1. Complete Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES (Multiple Ships/Devices)                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Syslog (UDP/TCP) │ Host Metrics │ SNMP Devices │ Application Logs │ File Logs │
│     :1514/:1515  │   (System)   │   (Network)  │    (Services)    │   (Files) │
└─────────┬───────────────┬─────────────┬──────────────┬─────────────────┬─────────┘
          │               │             │              │                 │
          ▼               ▼             ▼              ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VECTOR (Central Router)                            │
│ • Ingests all data types                                                        │
│ • Transforms and enriches data                                                  │
│ • Routes to multiple destinations                                               │
│ • Formats timestamps for ClickHouse compatibility                              │
└─────────┬───────────────────────────────────┬─────────────────────────────────┘
          │                                   │
          ▼                                   ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│      CLICKHOUSE         │         │    VICTORIAMETRICS      │
│   (Historical Storage)  │         │   (Metrics Storage)     │
│                         │         │                         │
│ • All logs & events     │         │ • System metrics        │
│ • Incidents timeline    │         │ • Performance data      │
│ • Cross-source data     │         │ • Time-series queries   │
│ • Long-term analytics   │         │ • Real-time dashboards  │
└─────────┬───────────────┘         └─────────┬───────────────┘
          │                                   │
          │     ┌─────────────────────────────▼─────────────────────────────┐
          │     │                  ANOMALY DETECTION                       │
          │     │ • Reads from VictoriaMetrics (metrics anomalies)         │
          │     │ • Reads from NATS (log anomalies)                        │
          │     │ • Should read from ClickHouse (historical baselines)     │
          │     │ • Publishes anomalies to NATS                            │
          │     └─────────────────────────────┬─────────────────────────────┘
          │                                   │
          │                                   ▼
          │     ┌─────────────────────────────────────────────────────────────┐
          │     │                          NATS                              │
          │     │           (Message Bus & Real-time Events)                 │
          │     │                                                             │
          │     │ • anomaly.detected (basic anomalies)                       │
          │     │ • anomaly.detected.enriched (enhanced anomalies)           │
          │     │ • incidents.created (correlated incidents)                 │
          │     │ • logs.anomalous (error/warning logs)                      │
          │     └─────────────────┬───────────────────────────────────────────┘
          │                       │
          │                       ▼
          │     ┌─────────────────────────────────────────────────────────────┐
          │     │                      BENTHOS                               │
          │     │              (Event Correlation Engine)                    │
          │     │                                                             │
          │     │ INPUT: Reads from NATS anomaly subjects                    │
          │     │ PROCESS: Correlates, deduplicates, suppresses             │
          │     │ OUTPUT: Creates incidents on NATS incidents.created       │
          │     │ LIMITATION: No ClickHouse historical correlation          │
          │     └─────────────────┬───────────────────────────────────────────┘
          │                       │
          │                       ▼
          │     ┌─────────────────────────────────────────────────────────────┐
          │     │                  INCIDENT API                               │
          │     │                                                             │
          │     │ • Consumes from NATS incidents.created                     │
          │     │ • Stores incidents in ClickHouse                           │
          │     │ • Provides REST API for incident management                │
          │     │ • Backend for Ops Console UI                               │
          │     └─────────────────┬───────────────────────────────────────────┘
          │                       │
          ▼                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GRAFANA VISUALIZATION                              │
│                                                                                 │
│ DATA SOURCES:                                                                   │
│ • VictoriaMetrics (real-time metrics, system performance)                      │
│ • ClickHouse (historical logs, incidents, correlation data)                    │
│                                                                                 │
│ CURRENT DASHBOARDS:                                                             │
│ • Fleet Overview (multi-ship comparison)                                       │
│ • Ship Overview (individual ship details)                                      │
│ • Capacity Forecasting (predictive analytics)                                  │
│ • Cross-Ship Benchmarking (performance comparison)                             │
│                                                                                 │
│ MISSING USER-FRIENDLY DASHBOARDS:                                              │
│ • Data Flow Visualization (real-time data journey)                             │
│ • Incident Correlation Story (plain language explanations)                     │
│ • Historical Pattern Analysis (root cause context)                             │
│ • Predictive Insights Panel (what might happen next)                           │
│ • Remediation Effectiveness Tracker (fix success rates)                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 2. Detailed Component Analysis

### 2.1 Benthos Data Input Sources

**Current Reality:**
```yaml
input:
  broker:
    inputs:
      - nats:
          subject: "anomaly.detected"           # Basic anomalies
      - nats:
          subject: "anomaly.detected.enriched"  # Enhanced anomalies
```

**Limitation:** Benthos only processes real-time anomalies from NATS. It does NOT access:
- Historical data from ClickHouse for baseline comparison
- Cross-correlation with past incident patterns
- Long-term trend analysis for predictive correlation

### 2.2 Benthos Results Storage

**Current Flow:**
1. Benthos correlates real-time anomalies
2. Outputs correlated incidents to NATS `incidents.created`
3. Incident API consumes from NATS and stores in ClickHouse `incidents` table

**Storage Schema (ClickHouse):**
```sql
CREATE TABLE incidents (
    incident_id String,
    created_at DateTime64(3),
    incident_type String,
    severity String,
    ship_id String,
    correlation_details String,
    timeline Array(String),
    status String
)
```

### 2.3 Visualization Architecture

**Current State:**
- **Grafana (port 3000):** Technical dashboards for operators
- **Data Sources:** VictoriaMetrics (metrics) + ClickHouse (logs/incidents)
- **Audience:** Technical users who understand metrics and correlation rules

**Missing Components:**
- User-friendly data flow visualization
- Plain language incident explanations
- Historical context and pattern recognition
- Predictive insights presentation

## 3. User-Friendly Correlation for Laymen

### 3.1 Current Technical Correlation

**What Benthos Does (Technical):**
```yaml
# Example correlation rule in Benthos
if this.metric_name == "cpu_usage" && related.metric_name == "memory_usage" {
  root.incident_type = "resource_pressure"
}
```

**What Users See:** Technical JSON with correlation metadata

### 3.2 Needed: Plain Language Translation

**What Users Should See:**
```
🚨 INCIDENT: High System Load Detected

WHAT HAPPENED:
Your ship's computer is working very hard (CPU at 85%) and running 
low on memory (RAM at 92%). This usually happens when too many 
programs are running at once.

WHY THIS MATTERS:
When both CPU and memory are high, your systems might slow down 
or stop responding. This could affect navigation, communication, 
or other critical operations.

SIMILAR INCIDENTS:
This happened 3 times in the past month, usually during:
- Heavy weather (satellite communication increased)
- Port approach (navigation systems working harder)
- Crew change periods (more data synchronization)

RECOMMENDED ACTIONS:
1. Check which programs are using the most resources
2. Close unnecessary applications
3. Consider restarting non-critical services
4. Monitor for the next 30 minutes

PREDICTED IMPACT:
If not addressed, there's a 75% chance of system slowdown 
within the next 2 hours, based on historical patterns.
```

## 4. Architecture Gaps and Needed Enhancements

### 4.1 Historical Context Integration

**Missing: ClickHouse Integration in Benthos**
```yaml
# Enhanced Benthos configuration needed
pipeline:
  processors:
    - sql:
        driver: "clickhouse"
        dsn: "clickhouse://clickhouse:9000/default"
        query: |
          SELECT COUNT(*) as past_occurrences,
                 AVG(resolution_time) as avg_resolution,
                 GROUP_ARRAY(resolution_action) as successful_fixes
          FROM incidents 
          WHERE incident_type = ? 
          AND ship_id = ?
          AND created_at > now() - INTERVAL 30 DAY
        args: ["${json(\"incident_type\")}", "${json(\"ship_id\")}"]
        result_codec: "json"
```

### 4.2 User-Friendly Visualization Dashboards

**Needed Dashboard: Data Flow Journey**
- Real-time visualization of data moving through the system
- Color-coded health indicators at each stage
- Interactive drill-down from high-level flow to detailed metrics

**Needed Dashboard: Incident Story**
- Plain language explanation of what happened
- Historical context ("This is the 3rd time this month")
- Predicted timeline and impact
- Success rate of recommended actions

**Needed Dashboard: Predictive Insights**
- "Based on current trends, here's what might happen"
- Seasonal patterns and capacity forecasting
- Early warning indicators before problems occur

### 4.3 Cross-Source Correlation Enhancement

**Current Limitation:** Benthos only correlates metrics-to-metrics

**Needed Enhancement:** Multi-source correlation
- Logs + Metrics + SNMP data correlation
- Weather data + satellite performance correlation
- Crew activity + system load correlation
- Port proximity + communication load correlation

## 5. Implementation Roadmap

### Phase 1: Enhanced Correlation (Current)
- ✅ Basic metric correlation in Benthos
- ✅ Incident storage in ClickHouse
- ✅ Technical dashboards in Grafana

### Phase 2: Historical Integration (Next)
- 🔄 Add ClickHouse historical queries to Benthos
- 🔄 Implement pattern recognition based on past incidents
- 🔄 Add "similar incidents" context to correlations

### Phase 3: User-Friendly Visualization (Needed)
- ⏳ Create plain language incident explanations
- ⏳ Build data flow visualization dashboard
- ⏳ Implement predictive insights panel
- ⏳ Add remediation effectiveness tracking

### Phase 4: Predictive Analytics (Future)
- ⏳ Machine learning models for pattern prediction
- ⏳ Seasonal forecasting integration
- ⏳ Proactive incident prevention

## 6. Key Questions Answered

### Q: Where does Benthos take data input from?
**A:** Currently only from NATS real-time anomaly subjects. Missing historical ClickHouse integration.

### Q: Where are Benthos results stored?
**A:** NATS → Incident API → ClickHouse incidents table

### Q: What about visualization?
**A:** Technical Grafana dashboards exist. Missing user-friendly data journey and correlation explanation dashboards.

### Q: How can laymen understand what's happening?
**A:** Major gap. Need plain language translation, historical context, and predictive insights presentation.

## 7. Next Steps

1. **Implement ClickHouse historical integration in Benthos** for better correlation
2. **Create user-friendly visualization dashboards** in Grafana
3. **Add plain language incident explanation service**
4. **Build predictive insights based on historical patterns**
5. **Implement remediation effectiveness tracking**

This architecture provides the foundation for intelligent correlation, but needs enhancement for user-friendly presentation and historical context integration.