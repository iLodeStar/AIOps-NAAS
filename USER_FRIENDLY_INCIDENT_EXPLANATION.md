# User-Friendly Incident Correlation Dashboard

## Overview

This service creates plain language explanations of technical correlations, making AIOps insights accessible to non-technical users.

## Features

### 1. Plain Language Incident Translation
Converts technical correlation data into user-friendly explanations:

```python
def translate_incident_to_plain_language(incident_data):
    """
    Convert technical incident data to user-friendly explanation
    
    Technical Input:
    {
        "incident_type": "resource_pressure",
        "metrics": {"cpu_usage": 0.85, "memory_usage": 0.92},
        "correlation_score": 0.94
    }
    
    User-Friendly Output:
    "Your ship's computer is working very hard (CPU at 85%) and 
     running low on memory (92%). This combination usually indicates 
     system overload."
    """
```

### 2. Historical Context Integration
Provides "this happened before" context:

```python
def get_historical_context(incident_type, ship_id):
    """
    Query ClickHouse for historical incident patterns
    
    Returns:
    {
        "past_occurrences": 3,
        "common_causes": ["heavy weather", "port approach", "crew change"],
        "average_resolution_time": "45 minutes",
        "successful_fixes": ["restart services", "close applications"]
    }
    """
```

### 3. Predictive Insights
Shows "what might happen next":

```python
def generate_predictive_insights(current_state, historical_patterns):
    """
    Predict likely outcomes based on current state and history
    
    Returns:
    {
        "probability_of_escalation": 0.75,
        "expected_timeline": "2 hours",
        "recommended_preventive_actions": [...],
        "confidence_level": "high"
    }
    """
```

## Implementation

### Service Structure
```
services/incident-explanation/
├── Dockerfile
├── requirements.txt
├── explanation_service.py
├── templates/
│   ├── incident_templates.json
│   └── explanation_formats.json
└── static/
    └── dashboard.html
```

### API Endpoints
- `POST /explain-incident` - Convert technical data to plain language
- `GET /historical-context/{incident_type}/{ship_id}` - Get historical patterns
- `GET /predictive-insights/{incident_id}` - Generate predictions
- `GET /dashboard` - User-friendly web interface

### Integration with Existing System
1. **Benthos Integration**: Add explanation step in correlation pipeline
2. **Incident API Integration**: Enhance incident storage with explanations
3. **Grafana Integration**: Create user-friendly dashboard panels

## Dashboard Examples

### Technical vs User-Friendly View

**Technical View (Current):**
```json
{
  "incident_type": "satellite_weather_impact",
  "metrics": {
    "signal_strength": -12.5,
    "packet_loss": 0.15,
    "latency": 800
  },
  "correlation_confidence": 0.87
}
```

**User-Friendly View (New):**
```
🛰️ COMMUNICATION ISSUE: Weather Affecting Satellite

WHAT'S HAPPENING:
Heavy weather is interfering with your satellite connection. 
Signal strength is weak (-12.5 dBm) and some data packets 
are getting lost (15% loss rate).

IMPACT:
- Internet might be slow or intermittent
- Email and messaging may be delayed
- File transfers could fail or take longer

SIMILAR SITUATIONS:
This happens during storms or heavy rain. In the past, this 
issue lasted an average of 2.5 hours and resolved naturally 
as weather improved.

WHAT TO DO:
1. Switch to backup communication if critical
2. Delay large file transfers
3. Monitor weather radar for improvement
4. Consider increasing satellite power if available

EXPECTED RESOLUTION:
Based on weather patterns, normal communication should 
return within 3-4 hours as the storm passes.
```

## Grafana Dashboard Integration

### New Dashboard Panels

1. **Data Flow Visualization**
   - Real-time data journey map
   - Health indicators at each stage
   - Interactive drill-down capabilities

2. **Incident Story Panel**
   - Plain language incident descriptions
   - Historical context and patterns
   - Recommended actions with success rates

3. **Predictive Insights Panel**
   - "What might happen next" predictions
   - Early warning indicators
   - Preventive action recommendations

4. **Remediation Tracker**
   - Track effectiveness of applied fixes
   - Success rates by incident type
   - Learning from past resolutions

### Dashboard Configuration

```json
{
  "dashboard": {
    "title": "AIOps User-Friendly Operations Center",
    "panels": [
      {
        "title": "System Health Overview",
        "type": "stat",
        "targets": [
          {
            "expr": "clickhouse_query('SELECT status FROM system_health')",
            "legendFormat": "Overall Health"
          }
        ]
      },
      {
        "title": "Active Incidents (Plain Language)",
        "type": "table",
        "targets": [
          {
            "query": "SELECT incident_explanation, predicted_resolution, recommended_actions FROM incidents WHERE status='open'",
            "datasource": "ClickHouse"
          }
        ]
      },
      {
        "title": "Data Flow Journey",
        "type": "diagram",
        "visualization": "data-flow-map"
      }
    ]
  }
}
```

## Benefits

### For Non-Technical Users
- **Clear Understanding**: Plain language explanations instead of technical jargon
- **Context Awareness**: "This happened before" historical perspective
- **Actionable Insights**: Clear recommendations with success probabilities
- **Predictive Awareness**: Understanding of potential future impacts

### For Technical Users
- **Enhanced Context**: Historical patterns and correlation insights
- **Improved Decision Making**: Data-driven recommendations based on past outcomes
- **Better Communication**: Tools to explain technical issues to stakeholders
- **Learning System**: Continuous improvement based on resolution tracking

### For Operations Teams
- **Faster Resolution**: Clear action items with historical success rates
- **Proactive Management**: Early warning systems and preventive actions
- **Knowledge Retention**: Capture and reuse successful resolution strategies
- **Training Support**: New team members can understand patterns quickly

## Example Use Cases

### Maritime-Specific Scenarios

1. **Weather Impact Correlation**
   - Technical: "Satellite signal degradation correlates with precipitation data"
   - User-Friendly: "Rain is affecting your internet connection. This usually lasts 2-3 hours during storms."

2. **Port Approach Resource Usage**
   - Technical: "CPU and network utilization spike during port proximity events"
   - User-Friendly: "Systems work harder when approaching port due to increased navigation and communication needs."

3. **Crew Change System Load**
   - Technical: "Memory usage increases during personnel transition periods"
   - User-Friendly: "Computer memory is running low, likely due to crew change data synchronization. This typically resolves within 4 hours."

4. **Equipment Maintenance Correlation**
   - Technical: "SNMP device response time degradation precedes hardware failures"
   - User-Friendly: "Network equipment is responding slowly, which often indicates upcoming maintenance needs."

This user-friendly explanation layer bridges the gap between technical AIOps capabilities and practical operational understanding, making the system valuable for all users regardless of technical background.