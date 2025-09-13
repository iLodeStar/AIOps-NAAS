# Grafana Visualization Implementation Guide

## Quick Start Implementation

This guide shows how to implement the recommended visualizations in the existing AIOps platform.

### Step 1: Deploy Example Dashboards

Copy the example dashboards to the Grafana provisioning directory:

```bash
# Copy example dashboards
cp docs/visualization/examples/*.json grafana/dashboards/

# Restart Grafana to load new dashboards
docker compose restart grafana
```

### Step 2: Update Data Sources for New Visualizations

Add the following queries to your existing data sources:

#### ClickHouse Schema Extensions

```sql
-- Add AI effectiveness tracking tables
CREATE TABLE IF NOT EXISTS anomalies (
    timestamp DateTime,
    anomaly_id String,
    detection_latency_seconds Int32,
    confirmed Bool,
    converted_to_incident Bool,
    auto_resolved Bool,
    manual_intervention Bool,
    resolution_time_minutes Int32
) ENGINE = MergeTree()
ORDER BY timestamp;

-- Add model performance tracking
CREATE TABLE IF NOT EXISTS model_performance (
    timestamp DateTime,
    model_name String,
    accuracy_score Float32,
    precision_score Float32,
    recall_score Float32
) ENGINE = MergeTree()
ORDER BY (timestamp, model_name);

-- Add financial metrics tracking
CREATE TABLE IF NOT EXISTS financial_metrics (
    quarter Int8,
    year Int16,
    cost_savings_usd Float32,
    platform_cost_usd Float32
) ENGINE = MergeTree()
ORDER BY (year, quarter);
```

#### VictoriaMetrics Metrics Extensions

```yaml
# Add to your scrape configs
- job_name: 'ai-metrics'
  static_configs:
    - targets: ['localhost:8081']
  metrics_path: '/metrics/ai'
  scrape_interval: 30s

- job_name: 'business-metrics'
  static_configs:
    - targets: ['localhost:8082'] 
  metrics_path: '/metrics/business'
  scrape_interval: 300s
```

### Step 3: Enable User-Friendly Features

Update the existing `user-friendly-operations.json` dashboard:

```bash
# Backup current dashboard
cp grafana/dashboards/user-friendly-operations.json grafana/dashboards/user-friendly-operations.json.bak

# Apply enhanced version
cp docs/visualization/examples/bridge-officer-dashboard.json grafana/dashboards/bridge-officer-operations.json
```

### Step 4: Configure Role-Based Access

Add to `grafana/provisioning/datasources/datasource.yml`:

```yaml
datasources:
  - name: BusinessMetrics
    type: prometheus
    uid: business-metrics
    url: http://victoria-metrics:8428
    access: proxy
    isDefault: false
    jsonData:
      timeInterval: "5m"
      httpMethod: POST
    # Restrict access to business users only
    secureJsonData:
      basicAuthPassword: "${BUSINESS_METRICS_PASSWORD}"
```

### Step 5: Mobile Responsiveness

Add mobile-friendly CSS overrides:

```css
/* Add to grafana/grafana.ini */
[panels]
height_sm = 6
height_md = 8
height_lg = 10

[mobile]
enable_touch = true
panel_min_height = 150
font_size_base = 14
```

## Advanced Implementation

### Custom Maritime Plugins

Create custom panels for maritime-specific visualizations:

```typescript
// grafana/plugins/maritime-status/src/SimplePanel.tsx
import React from 'react';
import { PanelProps } from '@grafana/data';

export const MaritimeStatusPanel: React.FC<PanelProps> = ({ data, width, height }) => {
  return (
    <div className="maritime-status-panel">
      <div className="weather-indicator">
        <span className="weather-icon">🌊</span>
        <span className="status-text">Sea State: Calm</span>
      </div>
      <div className="vessel-position">
        <span className="position-icon">🧭</span>
        <span className="coordinates">37.7749° N, 122.4194° W</span>
      </div>
    </div>
  );
};
```

### Automated Dashboard Deployment

Create deployment scripts:

```bash
#!/bin/bash
# scripts/deploy-visualizations.sh

echo "🚀 Deploying AIOps Visualization Updates..."

# Backup existing dashboards
mkdir -p grafana/dashboards/backup/$(date +%Y%m%d)
cp grafana/dashboards/*.json grafana/dashboards/backup/$(date +%Y%m%d)/

# Deploy new dashboards
for dashboard in docs/visualization/examples/*.json; do
    filename=$(basename "$dashboard")
    echo "Deploying $filename..."
    cp "$dashboard" "grafana/dashboards/$filename"
done

# Restart Grafana
docker compose restart grafana

echo "✅ Visualization deployment complete!"
```

### Data Pipeline Integration

Integrate with existing Benthos configuration:

```yaml
# benthos/benthos.yaml - Add AI metrics processing
pipeline:
  processors:
    - branch:
        request_map: |
          root = if this.type == "anomaly_detection" {
            {
              "timestamp": now(),
              "accuracy": this.model_accuracy,
              "detection_latency": this.processing_time_ms / 1000
            }
          } else { deleted() }
        result_map: |
          root.ai_metrics = this

output:
  broker:
    outputs:
      - clickhouse:
          dsn: "tcp://clickhouse:9000/logs"
          table: "ai_effectiveness"
      - prometheus:
          address: "victoria-metrics:8428"
```

## Testing Your Implementation

### 1. Validate Data Flow

```bash
# Test ClickHouse connectivity
curl -X POST 'http://localhost:8123/' \
  --data "SELECT COUNT(*) FROM anomalies WHERE timestamp > now() - INTERVAL 1 HOUR"

# Test VictoriaMetrics queries
curl 'http://localhost:8428/api/v1/query?query=ai_detection_accuracy'
```

### 2. Dashboard Functionality

```bash
# Check dashboard provisioning
curl -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  http://localhost:3000/api/dashboards/uid/bridge-officer-001

# Test panel rendering
curl -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  http://localhost:3000/api/dashboards/uid/ai-effectiveness-001
```

### 3. User Access Validation

```bash
# Test role-based access
curl -u "bridge_user:password" \
  http://localhost:3000/api/dashboards/db/bridge-officer-dashboard

# Test business dashboard access
curl -u "executive_user:password" \
  http://localhost:3000/api/dashboards/db/business-intelligence-dashboard
```

## Performance Optimization

### Query Optimization

```sql
-- Optimize ClickHouse queries for dashboards
-- Add materialized views for common aggregations
CREATE MATERIALIZED VIEW anomaly_daily_stats
ENGINE = SummingMergeTree()
ORDER BY date
AS SELECT
  toDate(timestamp) as date,
  countState() as total_anomalies,
  sumState(CASE WHEN confirmed = 1 THEN 1 ELSE 0 END) as confirmed_anomalies,
  avgState(detection_latency_seconds) as avg_detection_time
FROM anomalies
GROUP BY date;
```

### Caching Configuration

```yaml
# grafana/grafana.ini
[caching]
enabled = true

[cache.redis]
enabled = true
connstr = redis:6379

[query_caching]
enabled = true
max_cache_size_mb = 100
```

## Troubleshooting

### Common Issues

1. **Dashboards not loading**: Check provisioning configuration
2. **Queries timing out**: Optimize ClickHouse indexes
3. **Missing data**: Verify data source connectivity
4. **Mobile display issues**: Update panel grid positions

### Debug Commands

```bash
# Check Grafana logs
docker compose logs grafana -f

# Validate dashboard JSON
jq . grafana/dashboards/bridge-officer-dashboard.json

# Test database connectivity
docker exec -it clickhouse clickhouse-client --query "SELECT 1"
```

## Next Steps

1. **Implement Phase 1** features from the roadmap
2. **Train users** on new dashboard interfaces  
3. **Monitor performance** and optimize queries
4. **Collect feedback** from bridge officers and executives
5. **Iterate** based on real-world usage patterns

For detailed feature specifications, see [grafana-visualization-analysis.md](grafana-visualization-analysis.md).