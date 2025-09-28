# Modular Event Processing Pipeline Architecture

## Overview

This document describes the refactored modular event processing pipeline that ensures sequential, non-overlapping processing stages with distinct NATS topics for each service handoff.

## Architecture Diagram

```
┌─────────────────┐    logs.anomalous    ┌─────────────────────┐
│     Vector      │─────────────────────▶│   Anomaly Detection │
│ (Log Ingestion) │                      │     Service         │
└─────────────────┘                      └─────────────────────┘
                                                   │
                                                   │ anomaly.detected
                                                   ▼
┌─────────────────┐    anomaly.detected.enriched ┌─────────────────────┐
│ Enhanced Anomaly│◀─────────────────────────────│    Benthos          │
│   Detection     │                              │   Enrichment        │
│  (Level 2)      │                              │  (Level 1)          │
└─────────────────┘                              └─────────────────────┘
         │
         │ anomaly.detected.enriched.final
         ▼
┌─────────────────┐    incidents.created   ┌─────────────────────┐
│    Benthos      │─────────────────────▶│   Incident API      │
│  Correlation    │                      │    Service          │
│ (Incident Form) │                      │                     │
└─────────────────┘                      └─────────────────────┘
                                                   │
                                                   │ ClickHouse + REST API
                                                   ▼
                                         ┌─────────────────────┐
                                         │   Storage &         │
                                         │   Alerting          │
                                         └─────────────────────┘
```

## Service Details

### 1. Vector (Log Ingestion and Preprocessing)
- **Input**: Syslog UDP/TCP ports, application logs, file logs
- **Processing**: Parse, normalize, filter anomalous logs
- **Output**: 
  - ClickHouse `logs.raw` (all logs)
  - NATS `logs.anomalous` (ERROR/WARNING level logs)
- **Configuration**: `vector/vector.toml`
- **No changes required** - correctly implemented

### 2. Anomaly Detection Service (Basic)
- **Input**: NATS `logs.anomalous`
- **Processing**: Rule-based + ML anomaly detection on log messages
- **Output**: NATS `anomaly.detected`
- **Key Features**:
  - Preserves tracking IDs for traceability
  - Extracts ship_id, device_id from logs
  - Includes original error messages
  - Calculates anomaly scores
- **Configuration**: `services/anomaly-detection/`
- **Status**: ✅ Already correctly configured

### 3. Benthos Enrichment Service (Level 1 Enrichment) 
- **Input**: NATS `anomaly.detected` (ONLY)
- **Processing**: 
  - Maritime context enrichment
  - Weather data correlation
  - Device registry lookups
  - AI/ML context enhancement (placeholder)
  - Operational status determination
- **Output**: NATS `anomaly.detected.enriched`
- **Key Features**:
  - Preserves all original anomaly data
  - Adds enrichment_context with investigation suggestions
  - Sets operational_status based on anomaly characteristics
  - Maintains tracking IDs throughout
- **Configuration**: `benthos/data-enrichment.yaml`
- **Port**: 4196
- **Status**: ✅ Updated for sequential processing

### 4. Enhanced Anomaly Detection Service (Level 2 Enrichment)
- **Input**: NATS `anomaly.detected.enriched` (ONLY)
- **Processing**:
  - Context-aware anomaly thresholds
  - Maritime-specific anomaly patterns
  - Advanced grouping and correlation
  - LLM/Ollama integration for intelligent context
- **Output**: NATS `anomaly.detected.enriched.final`
- **Key Features**:
  - Leverages Level 1 enrichment context
  - Applies weather-adjusted thresholds
  - Groups related anomalies by operational context
  - Adds AI-enhanced contextual information
- **Configuration**: `services/enhanced-anomaly-detection/`
- **Port**: 9082
- **Status**: ✅ Updated for sequential processing

### 5. Benthos Correlation Service (Incident Formation)
- **Input**: NATS `anomaly.detected.enriched.final` (ONLY)
- **Processing**:
  - Final deduplication and suppression
  - Multi-event correlation
  - Incident classification and priority
  - Timeline creation
  - Runbook suggestions
- **Output**: NATS `incidents.created`
- **Key Features**:
  - Works exclusively with fully enriched anomaly events
  - Enhanced correlation logic for enriched data
  - Preserves all enrichment context in incidents
  - Maintains complete traceability chain
- **Configuration**: `benthos/benthos.yaml`
- **Port**: 4195
- **Status**: ✅ Updated for sequential processing

### 6. Incident API Service
- **Input**: NATS `incidents.created`
- **Processing**: Store incidents, provide REST API access
- **Output**: 
  - ClickHouse `logs.incidents` 
  - REST API endpoints
  - Downstream notifications
- **Configuration**: `services/incident-api/`
- **Port**: 8081
- **Status**: ✅ No changes needed

## NATS Topic Reference

| Topic | Publisher | Subscriber | Purpose |
|-------|-----------|------------|---------|
| `logs.anomalous` | Vector | Anomaly Detection Service | Filtered ERROR/WARNING logs |
| `anomaly.detected` | Anomaly Detection Service | Benthos Enrichment | Basic anomaly events |
| `anomaly.detected.enriched` | Benthos Enrichment | Enhanced Anomaly Detection | Level 1 enriched anomalies |
| `anomaly.detected.enriched.final` | Enhanced Anomaly Detection | Benthos Correlation | Level 2 enriched anomalies |
| `incidents.created` | Benthos Correlation | Incident API | Final incident objects |

## Key Design Principles

### 1. Sequential Processing
- Each service processes events from only ONE input topic
- Each service publishes to only ONE output topic  
- No parallel processing of the same topic by multiple services
- Clear data flow progression with no loops

### 2. Data Preservation
- Original error messages preserved throughout pipeline
- Tracking IDs maintained for end-to-end traceability
- All enrichment context accumulated (not replaced)
- Ship_id, device_id, service metadata preserved

### 3. Modularity
- Each service has distinct configuration files
- Services can be independently scaled or updated
- Clear service boundaries and responsibilities
- Easy to add new processing stages

### 4. Stats Collection Ready
- Each NATS topic transition can be monitored
- Service-specific metrics available via HTTP endpoints
- Processing stages clearly delineated for measurement

## Data Flow Example

### Input Log Message
```json
{
  "message": "ERROR TEST-20240101-120000-abc123 Database connection timeout",
  "level": "ERROR",
  "host": "ship-aurora",
  "service": "web-app",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### After Anomaly Detection (`anomaly.detected`)
```json
{
  "anomaly_score": 0.85,
  "severity": "high",
  "ship_id": "aurora-ship",
  "device_id": "ship-aurora",
  "tracking_id": "TEST-20240101-120000-abc123",
  "log_message": "ERROR TEST-20240101-120000-abc123 Database connection timeout",
  "metric_name": "log_anomaly",
  "correlation_id": "uuid-1234",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### After Benthos Enrichment (`anomaly.detected.enriched`)
```json
{
  "anomaly_score": 0.85,
  "severity": "high",
  "ship_id": "aurora-ship",
  "ship_name": "MSC AURORA",
  "tracking_id": "TEST-20240101-120000-abc123",
  "log_message": "ERROR TEST-20240101-120000-abc123 Database connection timeout",
  "enrichment_context": {
    "anomaly_enriched": true,
    "database_related": true,
    "suggested_investigation": ["check_database_connections", "review_connection_pool"]
  },
  "maritime_context": {
    "position": {"latitude": 45.5, "longitude": -123.5},
    "navigation": {"heading": 180, "speed": 12}
  },
  "operational_status": "system_issues",
  "correlation_level": "level_1_enriched"
}
```

### After Enhanced Anomaly Detection (`anomaly.detected.enriched.final`)
```json
{
  "anomaly_score": 0.92,
  "severity": "critical",
  "ship_id": "aurora-ship",
  "tracking_id": "TEST-20240101-120000-abc123",
  "enrichment_context": {
    "anomaly_enriched": true,
    "database_related": true,
    "enhanced_context": {
      "pattern_frequency": "increasing",
      "related_systems": ["web-app", "database"],
      "criticality_factors": ["timeout_pattern", "peak_traffic_time"]
    }
  },
  "operational_impact": "service_degradation",
  "correlation_level": "level_2_enhanced"
}
```

### Final Incident (`incidents.created`)
```json
{
  "incident_id": "inc-uuid-5678",
  "incident_type": "database_connectivity_issue",
  "incident_severity": "critical",
  "ship_id": "aurora-ship",
  "ship_name": "MSC AURORA",
  "tracking_id": "TEST-20240101-120000-abc123",
  "status": "open",
  "timeline": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "event": "incident_created",
      "description": "Database connectivity incident on MSC AURORA",
      "metadata": {
        "tracking_id": "TEST-20240101-120000-abc123",
        "anomaly_score": 0.92
      }
    }
  ],
  "suggested_runbooks": ["investigate_database_connectivity", "check_connection_pool"],
  "correlation_confidence": 0.85
}
```

## Health Monitoring

Each service provides health endpoints for monitoring:

- Vector: `http://localhost:8686/health`
- Anomaly Detection: `http://localhost:8080/health`
- Benthos Enrichment: `http://localhost:4196/stats`
- Enhanced Anomaly Detection: `http://localhost:9082/health`
- Benthos Correlation: `http://localhost:4195/stats`
- Incident API: `http://localhost:8081/health`

## Troubleshooting

### Common Issues

1. **Events not flowing**: Check NATS topic names match exactly between publishers and subscribers
2. **Missing enrichment**: Verify Benthos Enrichment is processing `anomaly.detected` correctly
3. **No incidents created**: Check that events reach `anomaly.detected.enriched.final` 
4. **Lost tracking IDs**: Verify each stage preserves `tracking_id` field

### Debugging Steps

1. Send test log with tracking ID via Vector
2. Check each NATS topic for message progression:
   ```bash
   # Monitor NATS topics (requires nats CLI)
   nats sub "logs.anomalous"
   nats sub "anomaly.detected"  
   nats sub "anomaly.detected.enriched"
   nats sub "anomaly.detected.enriched.final"
   nats sub "incidents.created"
   ```
3. Check service logs for processing errors
4. Verify service health endpoints

This modular architecture ensures clear separation of concerns, maintainable code, and traceable data flow through the entire incident processing pipeline.