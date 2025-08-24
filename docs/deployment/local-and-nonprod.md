# Local and Non-Production Deployment Guide

This guide covers deploying the AIOps NAAS platform in local development and non-production environments.

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- **Memory**: 8GB RAM minimum, 16GB recommended
- **Storage**: 20GB free disk space
- **CPU**: 4+ cores recommended for full stack

### Required Software

- **Docker**: Version 24.0+ with Docker Compose V2
- **Python**: Version 3.10+ for testing and utilities
- **Git**: For repository management
- **curl/wget**: For health checks and API testing

### Installation Commands

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin python3 python3-pip git curl

# Enable Docker for current user
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
python3 --version
```

## Configuration

### 1. Environment Variables

Create your environment configuration:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your specific values
nano .env
```

Key environment variables to configure:

```bash
# Database passwords (change defaults!)
CLICKHOUSE_PASSWORD=your_secure_password
GRAFANA_PASSWORD=your_admin_password

# External API keys (optional for basic testing)
WEATHER_API_KEY=your_openweather_api_key
SCHEDULE_API_KEY=your_scheduling_api_key

# Development settings
LOG_LEVEL=INFO
DEBUG_MODE=false
SIMULATION_MODE=false
```

### 2. Vendor Integrations

Configure vendor-specific parameters:

```bash
# Copy the vendor integration template
cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml

# Customize for your environment
nano configs/vendor-integrations.yaml
```

For detailed vendor configuration options, see the [Vendor Configuration Guide](../configuration/vendor-config.md).

### Key Configuration Sections

- **Network Devices**: Configure syslog, SNMP, NetFlow protocols
- **Satellite RF**: Set up VSAT vendor APIs and SNMP endpoints
- **Applications**: Define health check endpoints and SLAs  
- **External Context**: Weather APIs, NMEA navigation, scheduling feeds
- **Simulation**: Enable realistic data simulation for testing

### 3. Create Required Directories

```bash
# Create directories for persistent data and logs
mkdir -p logs reports data/backup
```

## Deployment

### Standard Deployment

Start the complete AIOps platform:

```bash
# Start all services
docker compose up -d

# Check service status  
docker compose ps

# View logs
docker compose logs -f
```

### Selective Service Deployment

Start only specific services for development:

```bash
# Core data services only
docker compose up -d clickhouse victoria-metrics grafana nats

# Add monitoring stack
docker compose up -d vmagent alertmanager mailhog vector

# Add AIOps services
docker compose up -d anomaly-detection incident-api link-health remediation
```

### Verification

Check that services are healthy:

```bash
# Service health checks
curl http://localhost:8123/ping          # ClickHouse
curl http://localhost:8428/health        # VictoriaMetrics
curl http://localhost:3000/api/health    # Grafana
curl http://localhost:8222/healthz       # NATS

# Application services (may take 1-2 minutes to start)
curl http://localhost:8080/health        # Anomaly Detection
curl http://localhost:8081/health        # Incident API
curl http://localhost:8082/health        # Link Health
curl http://localhost:8083/health        # Remediation
```

### Expected Resource Usage

Monitor resource consumption:

```bash
# Check resource usage
docker stats

# Expected usage with all services:
# Memory: 6-8GB total
# CPU: 10-20% on modern systems  
# Disk: ~2GB for images, ~1GB for data
```

## Service Access

### Web Interfaces

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Grafana | http://localhost:3000 | admin / admin |
| ClickHouse | http://localhost:8123 | default / (from .env) |
| NATS Monitor | http://localhost:8222 | - |
| VictoriaMetrics | http://localhost:8428 | - |
| VMAlert | http://localhost:8880 | - |
| Alertmanager | http://localhost:9093 | - |
| MailHog | http://localhost:8025 | - |
| Qdrant | http://localhost:6333 | - |

### API Endpoints

| Service | Port | Endpoint | Description |
|---------|------|----------|-------------|
| Anomaly Detection | 8080 | `/health`, `/anomalies` | Streaming anomaly detection |
| Incident API | 8081 | `/health`, `/incidents` | Incident management |
| Link Health | 8082 | `/health`, `/predict` | Satellite link prediction |
| Remediation | 8083 | `/health`, `/actions` | Auto-remediation engine |
| Fleet Aggregation | 8084 | `/health`, `/fleet` | Fleet data aggregation |
| Capacity Forecasting | 8085 | `/health`, `/forecast` | Capacity prediction |
| Cross-Ship Benchmarking | 8086 | `/health`, `/benchmark` | Performance benchmarking |

## Testing

### Integration Tests

Run the existing integration tests:

```bash
# v0.3 features test
python3 test_v03_integration.py

# v0.4 features test  
python3 test_v04_integration.py

# API functionality tests
./test_v03_apis.sh
./test_v04_apis.sh
```

### Soak Testing

Run the comprehensive 10-minute soak test:

```bash
# Run soak test locally
bash scripts/run_soak_test.sh

# Run with custom duration and config
bash scripts/run_soak_test.sh --duration 300 --config configs/vendor-integrations.yaml

# View results
cat reports/soak-summary.json
```

The soak test will:
- Start the data simulator with anomalies
- Monitor service health every 30 seconds
- Consume NATS messages for validation
- Generate a comprehensive report

### Manual Testing

Test individual components:

```bash
# Test data simulator
python3 tools/data-simulator/data_simulator.py --duration 30 --anomalies

# Test NATS consumer
python3 tools/data-simulator/consumer.py --subjects "telemetry.*" --duration 60

# Test vendor configuration
python3 -c "import yaml; yaml.safe_load(open('configs/vendor-integrations.yaml'))"
```

## Monitoring and Observability

### Grafana Dashboards

Access pre-configured dashboards at http://localhost:3000:

- **System Overview**: Infrastructure metrics and health
- **AIOps Platform**: Application performance and alerts
- **Satellite Link Health**: v0.3 predictive monitoring
- **Fleet Management**: v0.4 multi-ship visualization

### Log Monitoring

View service logs:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f link-health

# Application logs only
docker compose logs -f anomaly-detection incident-api link-health remediation

# Search logs
docker compose logs | grep "ERROR\|WARN"
```

### NATS Message Monitoring

Monitor message bus activity:

```bash
# NATS server info
curl http://localhost:8222/connz

# Consumer activity
python3 tools/data-simulator/consumer.py --subjects "telemetry.*" "link.health.*"
```

## Troubleshooting

### Common Issues

**Services fail to start**

```bash
# Check Docker status
systemctl status docker

# Check available resources
free -h
df -h

# Check for port conflicts
netstat -tulpn | grep -E ':(3000|8123|8428|4222)'
```

**Service health check failures**

```bash
# Check service logs
docker compose logs service-name

# Restart unhealthy service
docker compose restart service-name

# Check network connectivity
docker compose exec service-name ping clickhouse
```

**Configuration errors**

```bash
# Validate YAML files
python3 -c "import yaml; yaml.safe_load(open('configs/vendor-integrations.yaml'))"

# Check environment variables
docker compose config
```

**Memory or performance issues**

```bash
# Check resource usage
docker stats

# Reduce resource usage by disabling optional services
docker compose stop ollama qdrant  # Disable LLM components
docker compose stop benthos        # Disable stream processing
```

### Log Locations

Container logs are available via Docker:

```bash
docker compose logs [service-name]
```

Persistent data volumes:
- **ClickHouse data**: `clickhouse_data` volume
- **Grafana dashboards**: `grafana_data` volume  
- **VictoriaMetrics data**: `vm_data` volume
- **NATS data**: `nats_data` volume

### Performance Optimization

**Memory optimization:**

```bash
# Stop resource-intensive services if not needed
docker compose stop ollama qdrant benthos

# Reduce ClickHouse memory usage
# Edit docker-compose.yml to add memory limits
```

**Disk space optimization:**

```bash
# Clean up Docker resources
docker system prune -f

# Remove old data
docker volume prune
```

## Development Workflow

### Code Changes

When developing new features:

```bash
# Make code changes
# ...

# Rebuild specific service
docker compose build service-name

# Restart service with new code
docker compose up -d service-name

# View updated logs
docker compose logs -f service-name
```

### Testing Changes

```bash
# Run integration tests
python3 test_v03_integration.py

# Run soak test
bash scripts/run_soak_test.sh --duration 120

# Test specific components
python3 tools/data-simulator/data_simulator.py --duration 30
```

## Cleanup

### Stop Services

```bash
# Stop all services
docker compose down

# Remove volumes (WARNING: deletes data)
docker compose down -v

# Remove images
docker compose down --rmi all
```

### Reset Environment

Complete environment reset:

```bash
# Stop everything and remove data
docker compose down -v --rmi all

# Clean system
docker system prune -af

# Remove configuration
rm .env configs/vendor-integrations.yaml

# Reset to defaults
cp .env.example .env
cp configs/vendor-integrations.example.yaml configs/vendor-integrations.yaml
```

## Next Steps

After successful deployment:

1. **Configure Vendors**: Follow the [Vendor Configuration Guide](../configuration/vendor-config.md)
2. **Set up Monitoring**: Configure alerts and dashboards  
3. **Run Tests**: Execute the full [Test Plan](../testing/test-plan.md)
4. **Plan Production**: Review production deployment requirements

For production deployment, see the production deployment guide (coming in v1.0).