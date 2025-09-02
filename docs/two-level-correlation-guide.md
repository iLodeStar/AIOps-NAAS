# Two-Level Correlation Implementation Guide

## Overview

This implementation delivers the complete two-level correlation approach as requested:

**Level 1: Raw Data Enrichment and Correlation**
- Correlates data from multiple sources before anomaly detection
- Enriches events with contextual information (weather, satellite, system, maritime)
- Creates enriched telemetry events with operational status

**Level 2: Anomaly Correlation** 
- Correlates detected anomalies to create unified incidents
- Prevents separate incidents for related anomalies
- Enriches incidents with full correlation context

## Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Raw Data      │    │   Level 1           │    │   Enriched       │
│   Sources       │───▶│   Correlation       │───▶│   Data           │
│                 │    │   (Benthos)         │    │                  │
└─────────────────┘    └─────────────────────┘    └──────────────────┘
│ - System Metrics│                                │ - With Context   │
│ - Satellite Data│                                │ - Operational    │
│ - Weather Info  │                                │   Status         │
│ - Network Stats │                                │ - Maritime Data  │
│ - Ship Position │                                └──────────────────┘
└─────────────────┘                                          │
                                                             ▼
┌─────────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│   Incidents     │    │   Level 2           │    │   Anomaly        │
│                 │◀───│   Correlation       │◀───│   Detection      │
│                 │    │   (Benthos)         │    │   (Enhanced)     │
└─────────────────┘    └─────────────────────┘    └──────────────────┘
│ - Unified       │                                │ - Context-Aware  │
│ - Contextual    │                                │ - Maritime       │
│ - Actionable    │                                │ - Thresholds     │
└─────────────────┘                                └──────────────────┘
```

## Level 1 Implementation: Raw Data Enrichment

### Service: benthos-enrichment (Port 4196)

**Configuration**: `benthos/data-enrichment.yaml`

**Input Sources**:
- `metrics.system.*` - System performance data
- `telemetry.satellite.*` - VSAT/RF equipment data  
- `telemetry.network.*` - Network device metrics
- `external.weather.*` - Weather conditions
- `telemetry.ship.*` - Navigation/position data
- `logs.application.*` - Application performance

**Enrichment Process**:
1. **Data Correlation**: Correlates related data within 5-minute windows
2. **Context Addition**: Adds maritime, weather, and operational context
3. **Status Determination**: Calculates operational status (normal, weather_impacted, degraded_comms, etc.)
4. **Enriched Output**: Creates enriched events with full context

**Sample Input/Output**:

```json
// Input: Raw System Metrics
{
  "timestamp": "2024-01-15T10:30:00Z",
  "cpu_usage_percent": 78.5,
  "memory_usage_percent": 65.2,
  "ship_id": "ship-01"
}

// Output: Enriched Event
{
  "enrichment_id": "uuid-123",
  "data_source": "system", 
  "operational_status": "weather_impacted",
  "enrichment_context": {
    "satellite_quality": {
      "snr_db": 8.5,
      "signal_strength": -82.0
    },
    "correlation_type": "system_satellite"
  },
  "maritime_context": {
    "position": {"latitude": 25.76, "longitude": -80.19},
    "weather_conditions": "heavy_rain"
  },
  "original_data": { /* original system metrics */ },
  "correlation_score": 0.85
}
```

## Level 2 Implementation: Enhanced Anomaly Detection

### Service: enhanced-anomaly-detection (Port 8082)

**Key Features**:
- **Context-Aware Thresholds**: Adjusts detection sensitivity based on operational status
- **Maritime-Specific Detection**: Specialized algorithms for satellite, weather, navigation
- **Multi-Source Correlation**: Considers relationships between system, network, and satellite data

**Contextual Threshold Examples**:
- Normal CPU threshold: 70%
- During weather impact: 60% (more sensitive)  
- During known system overload: 75% (less sensitive)
- Satellite SNR threshold adjusted for rain conditions

**Sample Detection Logic**:
```python
if operational_status == 'weather_impacted':
    if 'satellite' in metric_name:
        threshold = base_threshold * 0.75  # 25% more sensitive
    elif 'cpu' in metric_name:
        threshold = base_threshold * 0.85  # 15% more sensitive

if enrichment_context.get('weather_impact', {}).get('rain_rate', 0) > 5:
    satellite_threshold = satellite_threshold * 0.80  # Much more sensitive
```

## Level 2 Implementation: Anomaly Correlation

### Enhanced Benthos Correlation

**Updates to**: `benthos/benthos.yaml`

**New Incident Types**:
- `weather_degradation` - Weather impacting multiple systems
- `satellite_weather_impact` - Satellite performance affected by weather
- `system_overload` - High resource usage with cascading effects
- `communication_issues` - Degraded connectivity across systems
- `network_system_correlation` - Network issues related to system load

**Enhanced Runbook Suggestions**:
```yaml
weather_degradation:
  - weather_response_protocol
  - switch_backup_comm
  - adjust_satellite_parameters

satellite_weather_impact:
  - satellite_rain_fade_mitigation
  - increase_tx_power
  - switch_to_backup_satellite
```

## Data Flow Example

### Scenario: Heavy Rain Affecting Operations

1. **Raw Data Collection**:
   ```
   Weather: rain_rate = 15 mm/hr
   Satellite: snr_db = 7.5 (poor)
   System: cpu_usage = 85% (high due to processing load)
   Network: latency = 250ms (elevated)
   ```

2. **Level 1 Enrichment**:
   ```json
   {
     "operational_status": "weather_impacted",
     "enrichment_context": {
       "weather_impact": {"rain_rate": 15, "wind_speed": 40},
       "satellite_quality": {"snr_db": 7.5, "ber": 0.003}
     }
   }
   ```

3. **Enhanced Anomaly Detection**:
   ```
   - Satellite SNR anomaly (adjusted threshold for rain)
   - CPU usage anomaly (context: weather processing)
   - Network latency anomaly (correlated with satellite issues)
   ```

4. **Level 2 Correlation**:
   ```json
   {
     "incident_type": "weather_degradation",
     "severity": "warning",
     "correlated_events": ["satellite_snr", "cpu_usage", "network_latency"],
     "suggested_runbooks": [
       "weather_response_protocol",
       "satellite_rain_fade_mitigation"
     ],
     "enrichment_metadata": {
       "weather_considered": true,
       "maritime_context_applied": true
     }
   }
   ```

## Testing the Implementation

### Start Services

```bash
# Start the complete stack with both correlation levels
docker compose up -d

# Verify new services are running
curl http://localhost:4196/ping  # Benthos enrichment
curl http://localhost:8082/health  # Enhanced anomaly detection
```

### Generate Test Data

```bash
# Install NATS client for test script
pip install nats-py

# Run correlation test scenarios
python3 scripts/test_two_level_correlation.py

# Run continuous test mode
python3 scripts/test_two_level_correlation.py continuous
```

### Monitor the Correlation Flow

1. **Level 1 Enrichment**: 
   ```bash
   curl http://localhost:4196/stats
   docker logs aiops-benthos-enrichment -f
   ```

2. **Enhanced Anomaly Detection**:
   ```bash
   curl http://localhost:8082/stats
   docker logs aiops-enhanced-anomaly-detection -f
   ```

3. **Level 2 Correlation**:
   ```bash
   curl http://localhost:4195/stats
   curl http://localhost:8081/incidents | jq .
   ```

## Benefits of Two-Level Correlation

### Level 1 Benefits
- **Rich Context**: Every data point enriched with operational context
- **Proactive Insights**: Understanding conditions before anomalies occur
- **Maritime Awareness**: Ship position, weather, and equipment status considered
- **Cross-Source Intelligence**: Network issues understood in context of satellite conditions

### Level 2 Benefits  
- **Unified Incidents**: Single incident for related anomalies
- **Intelligent Prioritization**: Context-aware severity and urgency
- **Actionable Responses**: Runbooks matched to specific operational scenarios
- **Reduced Alert Fatigue**: Fewer, more meaningful incidents

### Combined Benefits
- **Operational Intelligence**: Complete understanding of system state
- **Predictive Capabilities**: Early detection through context correlation
- **Automated Response**: Context-aware remediation suggestions
- **Maritime Optimization**: Ship-specific operational patterns

## Configuration

### Correlation Windows
- **Level 1**: 5-minute windows for raw data correlation
- **Level 2**: 5-minute windows for anomaly correlation
- **Cache TTL**: 10 minutes for enrichment context

### Thresholds
```yaml
# Base thresholds
cpu_usage: 70%
memory_usage: 60%
satellite_snr: 15 dB
network_latency: 200ms

# Contextual adjustments
weather_impacted: -15% (more sensitive)
system_overloaded: +10% (less sensitive)
degraded_comms: varies by metric
```

This implementation provides the complete two-level correlation system as requested, delivering both raw data enrichment and anomaly correlation for comprehensive maritime AIOps intelligence.