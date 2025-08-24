# AIOps NAAS Test Plan

This document outlines the comprehensive testing strategy for the AIOps NAAS platform, including unit tests, integration tests, end-to-end scenarios, and the new 10-minute simulator soak test.

## Testing Overview

### Test Pyramid

The testing strategy follows a pyramid approach:

1. **Unit Tests**: Fast, isolated tests for individual components
2. **Integration Tests**: Service interaction and API contract validation
3. **E2E Tests**: Full workflow scenarios including the soak test
4. **Performance Tests**: Load, stress, and endurance testing
5. **Manual Tests**: User acceptance and exploratory testing

### Test Environment Requirements

- **Local Development**: Docker Compose stack
- **CI Environment**: GitHub Actions with Docker support
- **Resources**: 8GB RAM, 20GB storage for full test suite

## Unit Testing

### Scope

Unit tests validate individual functions and classes:

- Data models and validation logic
- Utility functions and calculations  
- Configuration parsing
- Algorithm implementations

### Framework

- **Python**: pytest with asyncio support
- **Coverage**: minimum 70% code coverage target
- **Mocking**: unittest.mock for external dependencies

### Execution

```bash
# Run all unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ --cov=src --cov-report=html

# Run specific test module
pytest tests/unit/test_data_models.py -v
```

### Example Test Structure

```python
# tests/unit/test_link_predictor.py
import pytest
from src.link_health.predictor import LinkHealthPredictor

class TestLinkHealthPredictor:
    def test_calculate_quality_score(self):
        predictor = LinkHealthPredictor()
        score = predictor.calculate_quality_score(snr=15.0, ber=1e-6)
        assert 0.0 <= score <= 1.0
        assert score > 0.8  # Good signal should have high score
```

## Integration Testing

### Service Integration Tests

Test interactions between services and external dependencies:

- Database connectivity and queries
- Message bus (NATS) publishing/subscribing
- HTTP API endpoints and responses
- External service integrations

### Existing Integration Tests

**v0.3 Features Test**: `test_v03_integration.py`
- Predictive satellite link health monitoring
- Risk assessment and remediation selection
- Policy-based decision making
- Approval workflow simulation

**v0.4 Features Test**: `test_v04_integration.py`  
- Fleet data aggregation and reporting
- Capacity forecasting models
- Cross-ship performance benchmarking

### API Integration Tests

**v0.3 API Test**: `test_v03_apis.sh`
- Link health prediction endpoints
- Remediation action execution
- Policy evaluation services

**v0.4 API Test**: `test_v04_apis.sh`
- Fleet aggregation APIs
- Capacity forecasting endpoints
- Benchmarking service APIs

### Execution

```bash
# Run v0.3 integration test
python3 test_v03_integration.py

# Run v0.4 integration test  
python3 test_v04_integration.py

# Test v0.3 APIs
./test_v03_apis.sh

# Test v0.4 APIs
./test_v04_apis.sh
```

## End-to-End Testing

### 10-Minute Simulator Soak Test

**New E2E Test**: `tests/e2e/test_simulator_soak.py`

This comprehensive test validates the entire platform under realistic load:

#### Test Scenario

1. **Setup** (30 seconds):
   - Start data simulator with anomaly generation
   - Connect NATS consumer for message validation
   - Initialize health monitoring

2. **Execution** (600 seconds):
   - Generate realistic telemetry data with random anomalies
   - Consume and validate NATS messages
   - Perform health checks every 30 seconds
   - Monitor remediation approval queue
   - Track service availability and response times

3. **Validation** (30 seconds):
   - Generate comprehensive test report
   - Validate minimum test assertions
   - Save artifacts and metrics

#### Test Assertions

The soak test validates these critical outcomes:

- **Duration**: Test runs for at least 95% of target duration (570+ seconds)
- **Health Monitoring**: At least 10 health checks performed
- **Service Availability**: At least one service remains healthy throughout
- **Error Handling**: No critical system errors occur
- **Message Processing**: NATS messages are successfully consumed

#### Execution

```bash
# Run pytest version
pytest tests/e2e/test_simulator_soak.py -v

# Run standalone with custom settings
python3 tests/e2e/test_simulator_soak.py --duration 600 --log-level INFO

# Run via orchestration script (recommended)
bash scripts/run_soak_test.sh

# Run with custom configuration
bash scripts/run_soak_test.sh --duration 300 --config configs/vendor-integrations.yaml
```

#### Expected Outcomes

Successful soak test should produce:

- **soak-summary.json**: Comprehensive test metrics and results
- **junit-results.xml**: JUnit-compatible test results for CI
- **Service logs**: Container logs for debugging
- **Message capture**: NATS message archive for analysis

### Manual E2E Scenarios

**Scenario 1: Normal Operations**
1. Start platform with `docker compose up -d`
2. Access Grafana dashboards at http://localhost:3000
3. Verify all services show healthy status
4. Generate test data using simulator
5. Confirm data flows through pipeline to visualization

**Scenario 2: Anomaly Detection and Response**  
1. Start platform and data simulator with anomalies
2. Trigger satellite link degradation scenario
3. Verify alert generation and NATS message publishing
4. Check remediation recommendations are generated
5. Validate approval workflow for high-risk actions

**Scenario 3: Fleet Management**
1. Configure multi-ship data simulation
2. Verify fleet aggregation service collects data
3. Check cross-ship benchmarking analysis
4. Validate capacity forecasting predictions
5. Confirm fleet dashboards display correctly

## Performance Testing

### Load Testing

Test platform performance under normal and peak loads:

```bash
# Simulate high-frequency telemetry data
python3 tools/data-simulator/data_simulator.py --duration 300 --interval 1

# Monitor resource usage during test
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Measure message throughput
python3 tools/data-simulator/consumer.py --subjects "telemetry.*" --duration 300
```

### Stress Testing

Validate system behavior under extreme conditions:

- **High Message Volume**: 1000+ messages/second
- **Memory Pressure**: Constrained container memory limits
- **Network Partitions**: Simulated connection failures
- **Database Overload**: High query concurrency

### Endurance Testing

Long-running tests for stability validation:

```bash
# 24-hour endurance test (manual execution)
bash scripts/run_soak_test.sh --duration 86400 --no-cleanup

# Monitor for memory leaks and performance degradation
```

## Configuration Testing

### Vendor Configuration Validation

Test various vendor configuration scenarios:

```bash
# Validate configuration file syntax
python3 -c "import yaml; yaml.safe_load(open('configs/vendor-integrations.yaml'))"

# Test with different vendor configurations
pytest tests/config/ -v --config-file configs/test-vendor-1.yaml
pytest tests/config/ -v --config-file configs/test-vendor-2.yaml

# Test environment variable overrides
CONFIG_ENV=test pytest tests/config/ -v
```

### Simulation Configuration Testing

Validate data simulator configuration options:

```bash
# Test different anomaly scenarios
python3 tools/data-simulator/data_simulator.py --config configs/high-anomaly.yaml --duration 60

# Test realistic vs. edge-case data distributions  
python3 tools/data-simulator/data_simulator.py --config configs/extreme-weather.yaml --duration 60
```

## Continuous Integration Testing

### GitHub Actions Workflow

The CI pipeline includes:

1. **Basic CI** (runs on every push/PR):
   - Configuration validation
   - Unit test execution
   - Static code analysis
   - Documentation checks

2. **Soak Test** (manual/scheduled only):
   - 10-minute end-to-end test
   - Artifact collection
   - JUnit result publishing
   - PR comment with results

### CI Execution

```yaml
# Manual trigger
on:
  workflow_dispatch:
    inputs:
      run_soak_test:
        type: boolean
        default: false

# Scheduled execution (weekly)
on:
  schedule:
    - cron: '0 2 * * 0'  # Sundays at 02:00 UTC
```

### Artifact Collection

CI automatically collects and preserves:

- Test result summaries (JSON)
- JUnit XML for test reporting
- Service logs from soak test
- System resource metrics
- NATS message captures

## Test Data Management

### Test Data Sets

Maintain realistic test data for consistent testing:

- **Normal Operations**: Typical satellite link KPIs
- **Degraded Conditions**: Rain fade, equipment issues
- **Critical Scenarios**: Emergency situations requiring remediation
- **Fleet Data**: Multi-ship scenarios with varied performance

### Data Simulator Configuration

Configure realistic data distributions:

```yaml
simulation:
  base_distributions:
    modem:
      snr_db: {mean: 15.0, std_dev: 3.0}
      ber: {base: 1e-6, variation_factor: 10.0}
    weather:
      precipitation_mm_hr: {mean: 0.5, std_dev: 2.0}
  anomalies:
    probability: 0.1  # 10% chance per measurement
    types: ["rain_fade", "equipment_degradation"]
```

## Test Reporting

### Soak Test Report

The soak test generates comprehensive reporting:

```json
{
  "test_info": {
    "duration_seconds": 602.1,
    "completed_successfully": true
  },
  "health_monitoring": {
    "total_checks": 21,
    "overall_health_rate": 95.2,
    "service_availability": {
      "link-health": {"availability_percent": 100.0},
      "remediation": {"availability_percent": 90.5}
    }
  },
  "assertions": {
    "minimum_duration_met": true,
    "health_checks_performed": true,
    "no_critical_errors": true
  }
}
```

### Test Metrics

Key metrics tracked across all tests:

- **Test Coverage**: Code coverage percentage
- **Test Duration**: Execution time for CI optimization
- **Success Rate**: Pass/fail ratio over time
- **Service Health**: Availability during testing
- **Performance**: Resource usage and response times

## Troubleshooting Tests

### Common Test Failures

**Soak Test Timeout**
```
AssertionError: Test did not run for minimum duration
```
- Check system resources (memory/CPU)
- Verify Docker services are healthy
- Review service startup times

**NATS Connection Failures**
```
ConnectionError: Failed to connect to NATS
```
- Confirm NATS container is running
- Check port 4222 availability  
- Verify network connectivity

**Health Check Failures**
```
requests.exceptions.ConnectionError
```
- Wait longer for service startup
- Check service logs for errors
- Verify endpoint URLs are correct

### Debug Mode

Enable detailed logging for debugging:

```bash
# Run tests with debug output
pytest tests/e2e/ -v -s --log-level=DEBUG

# Run soak test with debug logging
bash scripts/run_soak_test.sh --log-level DEBUG

# Enable debug mode in data simulator
python3 tools/data-simulator/data_simulator.py --log-level DEBUG
```

## Test Schedule

### Automated Testing

- **Every Commit**: Unit tests, configuration validation
- **Every PR**: Integration tests, API validation  
- **Weekly**: Full soak test (scheduled CI)
- **Release**: Complete test suite including manual scenarios

### Manual Testing

- **Feature Development**: Component-specific tests
- **Integration Milestones**: E2E scenario validation
- **Pre-Release**: User acceptance testing
- **Production Deployment**: Smoke tests and monitoring validation

## Future Testing Enhancements

### Planned Improvements

- **Chaos Engineering**: Automated failure injection testing
- **Security Testing**: Vulnerability scanning and penetration testing  
- **Multi-Environment**: Test across different deployment scenarios
- **Performance Benchmarking**: Automated performance regression detection
- **User Interface Testing**: Grafana dashboard and UI automation

### Test Infrastructure

- **Test Data Pipeline**: Automated realistic test data generation
- **Test Environment Management**: Containerized test environments
- **Test Result Analytics**: Historical trend analysis and reporting
- **Parallel Test Execution**: Faster CI feedback through parallelization

For more information on running specific tests, see the [Local and Non-Production Deployment Guide](../deployment/local-and-nonprod.md).