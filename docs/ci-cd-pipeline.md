# AIOps NAAS CI/CD Pipeline

This document describes the comprehensive CI/CD testing pipeline implemented for the AIOps NAAS platform.

## Overview

The CI/CD pipeline provides automated testing across four key areas:
- **Unit Testing**: Individual component validation with coverage reporting
- **Integration Testing**: Service interaction validation using docker-compose
- **System Testing**: API endpoint validation using existing test scripts
- **End-to-End Testing**: Complete workflow validation with real-time data simulation

## Pipeline Structure

### GitHub Actions Workflow (`.github/workflows/ci.yml`)

The pipeline runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Jobs

#### 1. Unit Tests (`unit`)
- **Runtime**: ~3-5 minutes
- **Coverage Threshold**: 90% (configurable)
- **Outputs**: 
  - `coverage.xml` - Coverage report in Cobertura format
  - `htmlcov/` - HTML coverage report
  - `junit-unit.xml` - JUnit test results

**Key Features**:
- Tests all components in `/src/` and `/services/`
- Enforces 90% minimum code coverage
- Generates both XML and HTML coverage reports
- Fails build if coverage drops below threshold

#### 2. Integration Tests (`integration`)
- **Runtime**: ~8-12 minutes  
- **Dependencies**: Docker, docker-compose
- **Test Scripts**: `test_v03_integration.py`, `test_v04_integration.py`
- **Outputs**: 
  - `integration_v03.log` - v0.3 integration test log
  - `integration_v04.log` - v0.4 integration test log
  - `junit-integration.xml` - JUnit test results

**Key Features**:
- Spins up complete AIOps stack via docker-compose
- Validates service interconnections
- Tests v0.3 (satellite health) and v0.4 (fleet management) features
- Includes service health checks with timeouts

#### 3. System Tests (`system`)
- **Runtime**: ~10-15 minutes
- **Dependencies**: Docker, docker-compose
- **Test Scripts**: `test_v03_apis.sh`, `test_v04_apis.sh`
- **Outputs**:
  - `system_v03.log` - v0.3 API test results
  - `system_v04.log` - v0.4 API test results  
  - `service_health.log` - Service health check results
  - `junit-system.xml` - JUnit test results

**Key Features**:
- Tests all API endpoints
- Validates service health across the stack
- Uses existing battle-tested shell scripts
- Collects comprehensive service status information

#### 4. End-to-End Tests (`e2e`)
- **Runtime**: ~8-12 minutes
- **Dependencies**: Custom data simulator
- **Test Scripts**: `e2e_test.py` with `data_simulator.py`
- **Outputs**:
  - `simulation_data.jsonl` - Generated telemetry data
  - `e2e_results.json` - E2E test results
  - `e2e_report.md` - Human-readable test report
  - `junit-e2e.xml` - JUnit test results

**Key Features**:
- Real-time maritime data generation
- 15% anomaly injection rate
- Tests complete Alert → Policy → Approval → Execution → Audit flow
- Multiple scenario validation (6 test scenarios)
- 80%+ success rate requirement

#### 5. Reporting (`reporting`)
- **Runtime**: ~2-3 minutes
- **Dependencies**: All previous jobs
- **Outputs**:
  - Technical report (`test_report_technical.md/.html`)
  - Executive summary (`test_report_non_technical.md/.html`)
  - Combined artifacts package

**Key Features**:
- Aggregates results from all test phases
- Generates both technical and business-oriented reports  
- Creates HTML versions for better readability
- Optionally publishes to GitHub Pages

## Data Simulator (`data_simulator.py`)

### Purpose
Generates realistic maritime telemetry data matching the AIOps platform's data sources:

### Data Sources Simulated
1. **Satellite & RF Equipment**
   - SNR, BER, signal strength, Es/No, rain fade margin
   - Antenna positioning (elevation, azimuth)
   - Frequency bands and modulation schemes

2. **Ship Telemetry** (NMEA-0183 style)
   - GPS coordinates, heading, speed
   - Pitch, roll, yaw measurements
   - Altitude and GPS quality indicators

3. **Weather Data**
   - Precipitation, wind conditions
   - Temperature, humidity, pressure
   - Visibility and cloud cover

4. **Network Devices** (SNMP-style)
   - CPU, memory, interface utilization
   - Packet loss, latency, error counts
   - Device temperature monitoring

5. **Application Services**
   - Response times, error rates
   - Throughput, connection counts
   - Service availability metrics

### Anomaly Scenarios
- **satellite_degradation**: SNR drops, higher BER
- **weather_impact**: Rain fade, signal attenuation
- **network_congestion**: High utilization, packet loss
- **equipment_failure**: Temperature spikes, error bursts
- **security_incident**: CPU spikes, high error rates
- **power_fluctuation**: Signal strength variations

### Usage
```bash
# Basic usage (10 minutes, 5-second intervals, 15% anomalies)
python data_simulator.py

# Custom configuration
python data_simulator.py --duration 5 --interval 2 --anomaly-rate 0.25

# Help
python data_simulator.py --help
```

### Output Formats
- **JSON Lines** (`simulation_data.jsonl`): Complete structured data
- **CSV** (`simulation_data.csv`): Flattened format for analysis
- **Console Logging**: Real-time progress and anomaly notifications

## End-to-End Testing (`e2e_test.py`)

### Test Flow
1. **Alert Generation**: Creates realistic alerts based on scenarios
2. **Policy Evaluation**: Simulates OPA policy decisions  
3. **Approval Process**: Simulates manual approval workflows
4. **Remediation Execution**: Simulates action execution with success/failure
5. **Audit Trail**: Creates comprehensive audit records

### Test Scenarios
- **satellite_degradation** (HIGH): Tests satellite failover workflows
- **weather_impact** (MEDIUM/CRITICAL): Tests weather-related responses
- **network_congestion** (CRITICAL): Tests bandwidth management
- **equipment_failure** (HIGH): Tests hardware failure responses

### Success Criteria
- 80%+ scenario success rate
- Complete audit trails for all actions
- Policy compliance validation
- Execution result tracking

## Running Tests Locally

### Prerequisites
```bash
pip install -r requirements-test.txt
```

### Individual Test Runs
```bash
# Unit tests with coverage
python -m pytest tests/ --cov=src --cov-report=term

# Integration tests (requires docker-compose)
python test_v03_integration.py

# System tests (requires running services)  
./test_v03_apis.sh

# End-to-end tests
python e2e_test.py

# Data simulator
python data_simulator.py --duration 2 --interval 1
```

### Full Local Pipeline
```bash
# Start services
docker compose up -d

# Run all tests
python -m pytest tests/ --cov=src --cov-report=html
python test_v03_integration.py  
python test_v04_integration.py
./test_v03_apis.sh
./test_v04_apis.sh
python e2e_test.py

# Stop services
docker compose down
```

## Report Formats

### Technical Report
- **Audience**: Engineers, DevOps, QA teams
- **Content**: Detailed test execution, technical metrics, error analysis
- **Format**: Markdown + HTML
- **Includes**: Service endpoints, test commands, performance metrics

### Executive Summary  
- **Audience**: Management, stakeholders, business users
- **Content**: High-level test results, business impact, recommendations
- **Format**: Markdown + HTML  
- **Includes**: Test scenarios, success rates, system readiness

## Artifacts and Storage

### Build Artifacts
All test runs generate artifacts stored for 90 days:
- Coverage reports (XML/HTML)
- JUnit test results (XML)
- Simulation data (JSON/CSV)
- Service logs
- Test reports (MD/HTML)

### GitHub Pages (Optional)
When enabled, reports are automatically published to:
`https://{org}.github.io/{repo}/test-reports/`

## Configuration

### Coverage Thresholds
- **Unit Tests**: 90% minimum (configurable in workflow)
- **Integration**: Service health validation
- **System**: API response validation  
- **E2E**: 80% scenario success rate

### Service Timeouts
- **Grafana**: 120 seconds startup timeout
- **VictoriaMetrics**: 120 seconds startup timeout
- **ClickHouse**: 120 seconds startup timeout
- **NATS**: 120 seconds startup timeout

### Data Generation
- **Default Duration**: 10 minutes (E2E), 2 minutes (CI)
- **Default Interval**: 5 seconds (configurable)
- **Anomaly Rate**: 15% (configurable)
- **Output Formats**: JSON Lines + CSV

## Troubleshooting

### Common Issues

1. **Coverage Below Threshold**
   - Add more unit tests to uncovered code
   - Review coverage report in `htmlcov/index.html`

2. **Docker Service Startup Failures**
   - Check `docker compose logs`
   - Verify port availability
   - Increase service timeout values

3. **Integration Test Failures**
   - Verify all services are healthy
   - Check service logs for errors
   - Validate test data and scenarios

4. **E2E Test Failures**
   - Review `e2e_results.json` for detailed error info
   - Check anomaly injection rate
   - Validate test scenario configurations

### Log Locations
- Unit test logs: Console output
- Integration logs: `integration_v*.log`
- System test logs: `system_v*.log`
- Service health: `service_health.log`
- E2E results: `e2e_results.json`

## Contributing

When adding new tests or modifying the pipeline:

1. Maintain the 90% coverage threshold
2. Add corresponding unit tests for new features
3. Update test scenarios for new data sources
4. Validate both technical and business report formats
5. Test locally before pushing changes

## Security Considerations

- No secrets or credentials in test data
- Service endpoints use localhost/internal networking
- Test data is generated, not production data
- Audit trails include compliance validation
- All test artifacts have retention policies