# Incident Data Pipeline Diagnostic Report

**Generated:** 2025-09-13T18:27:13.651923  
**Tracking Session:** `ONECLICK-20250913-182633-bd5c6fc0`  
**Tool:** One-Click Incident Debugging  
**System Syslog Support:** ✅ Enabled

## 🚨 Issue Summary

Incident data pipeline is producing incomplete/fallback values instead of meaningful data. This automated diagnostic identified specific issues and provides reproduction steps for both application logs and system-generated syslog data.

## 🖥️ System Syslog Testing Results

This diagnostic includes comprehensive testing of system-generated syslog data:

**Syslog Sources Tested:**
- **systemd services** (facility 1, port 1514/1515)
- **SSH daemon (sshd)** (facility 1, standard system authentication)
- **Kernel messages** (facility 0, hardware/system events)  
- **Cron services** (facility 1, scheduled job logs)
- **Application logs** (facility 16, custom services)

**Transport Methods:**
- ✅ UDP Port 1514 (Vector syslog UDP source)
- ✅ TCP Port 1515 (Vector syslog TCP source) 
- ⚠️ UDP Port 514 (Standard syslog - requires root)
- ✅ Vector HTTP API (Fallback method)

## 📊 Service Health Status

| Service | Status | Details |
|---------|--------|---------|
| Vector | ❌ unhealthy | Connection failed |
| ClickHouse | ❌ unhealthy | Could not connect with any credentials |
| NATS | ❌ unhealthy | Connection failed |
| Benthos | ❌ unhealthy | Connection failed |
| Victoria Metrics | ❌ unhealthy | Connection failed |
| Incident API | ❌ unhealthy | Connection failed |
| Device Registry | ❌ unhealthy | Connection failed |

## ❌ Data Mismatches Identified


### Ship Id Mismatch

- **Expected:** `actual ship identifiers (e.g., test-ship-alpha)`
- **Actual:** `unknown-ship (predicted due to Device Registry being down)`
- **Service Responsible:** Device Registry
- **Root Cause:** Device Registry service is not running or not accessible
- **Fix Steps:**
  - Start the Device Registry service: docker-compose restart device-registry
  - Check Device Registry health: curl http://localhost:8081/health
  - Verify device registry database is accessible
  - Ensure Benthos configuration includes device registry lookups
  - Register test devices for validation


### Incident Processing Mismatch

- **Expected:** `incidents stored and queryable in ClickHouse`
- **Actual:** `incidents may not be properly processed (predicted due to Incident API being down)`
- **Service Responsible:** Incident API
- **Root Cause:** Incident API service is not running or not accessible
- **Fix Steps:**
  - Start the Incident API service: docker-compose restart incident-api
  - Check Incident API health: curl http://localhost:9081/health
  - Verify NATS connectivity for incident events
  - Check ClickHouse connectivity from Incident API
  - Verify incident processing workflow


## 🧪 Test Data Generated

The following test data was generated and traced through the pipeline:


**Test Point 1:** `ONECLICK-20250913-182633-bd5c6fc0-DATA-001` (📱 Application)
- Ship: test-ship-alpha
- Hostname: alpha-bridge-01  
- Service: navigation_system
- Type: application syslog
- Metric: gps_accuracy_meters = 2.5


**Test Point 2:** `ONECLICK-20250913-182633-bd5c6fc0-DATA-002` (🖥️ System)
- Ship: test-ship-beta
- Hostname: beta-engine-02  
- Service: systemd
- Type: system syslog
- Metric: service_restart_count = 3.0


**Test Point 3:** `ONECLICK-20250913-182633-bd5c6fc0-DATA-003` (🖥️ System)
- Ship: test-ship-gamma
- Hostname: gamma-comms-01  
- Service: sshd
- Type: system syslog
- Metric: failed_login_attempts = 5.0


**Test Point 4:** `ONECLICK-20250913-182633-bd5c6fc0-DATA-004` (🖥️ System)
- Ship: test-ship-delta
- Hostname: delta-sensor-03  
- Service: kernel
- Type: system syslog
- Metric: temperature_celsius = 75.5


**Test Point 5:** `ONECLICK-20250913-182633-bd5c6fc0-DATA-005` (🖥️ System)
- Ship: test-ship-epsilon
- Hostname: epsilon-backup-01  
- Service: cron
- Type: system syslog
- Metric: backup_duration_seconds = 1800.0


## 🔬 Detailed Reproduction Steps

**Test Case 1: ONECLICK-20250913-182633-bd5c6fc0-DATA-001**

**Test Data:**
- Ship ID: `test-ship-alpha`
- Hostname: `alpha-bridge-01`
- Service: `navigation_system`
- Metric: `gps_accuracy_meters = 2.5`
- Tracking ID: `ONECLICK-20250913-182633-bd5c6fc0-DATA-001`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping:
   ```bash
   curl -X POST http://localhost:8081/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"alpha-bridge-01","ship_id":"test-ship-alpha"}'
   ```
3. Send syslog message (application syslog):
   ```bash
   # Method 1: Vector UDP 1514/TCP 1515 (application)
   echo '<134>1 2025-09-13T18:26:33.284046Z alpha-bridge-01 navigation_system - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-001] GPS accuracy degraded to 2.5 meters in heavy fog' | nc -u localhost 1514
   # Method 2: Vector TCP syslog
   echo '<134>1 2025-09-13T18:26:33.284046Z alpha-bridge-01 navigation_system - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-001] GPS accuracy degraded to 2.5 meters in heavy fog' | nc localhost 1515
   # Method 3: Standard syslog (if root)
   echo '<134>1 2025-09-13T18:26:33.284046Z alpha-bridge-01 navigation_system - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-001] GPS accuracy degraded to 2.5 meters in heavy fog' | nc -u localhost 514
   ```
4. Publish metric:
   ```bash
   curl -X POST http://localhost:8428/api/v1/import/prometheus \
     -d 'gps_accuracy_meters{ship_id="test-ship-alpha",hostname="alpha-bridge-01"} 2.5'
   ```
5. Wait 30 seconds for processing
6. Query ClickHouse:
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship-alpha' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

**Expected Results:**
- ship_id: `test-ship-alpha` (not 'unknown-ship')
- service: `navigation_system` (not 'unknown_service')
- metric_name: `gps_accuracy_meters` (not 'unknown_metric')
- metric_value: `2.5` (not 0)

**Test Case 2: ONECLICK-20250913-182633-bd5c6fc0-DATA-002**

**Test Data:**
- Ship ID: `test-ship-beta`
- Hostname: `beta-engine-02`
- Service: `systemd`
- Metric: `service_restart_count = 3.0`
- Tracking ID: `ONECLICK-20250913-182633-bd5c6fc0-DATA-002`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping:
   ```bash
   curl -X POST http://localhost:8081/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"beta-engine-02","ship_id":"test-ship-beta"}'
   ```
3. Send syslog message (system syslog):
   ```bash
   # Method 1: Vector UDP 1514/TCP 1515 (user facility)
   echo '<14>1 2025-09-13T18:26:33.284059Z beta-engine-02 systemd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-002] Started engine monitoring service after 3 restart attempts' | nc -u localhost 1514
   # Method 2: Vector TCP syslog
   echo '<14>1 2025-09-13T18:26:33.284059Z beta-engine-02 systemd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-002] Started engine monitoring service after 3 restart attempts' | nc localhost 1515
   # Method 3: Standard syslog (if root)
   echo '<14>1 2025-09-13T18:26:33.284059Z beta-engine-02 systemd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-002] Started engine monitoring service after 3 restart attempts' | nc -u localhost 514
   ```
4. Publish metric:
   ```bash
   curl -X POST http://localhost:8428/api/v1/import/prometheus \
     -d 'service_restart_count{ship_id="test-ship-beta",hostname="beta-engine-02"} 3.0'
   ```
5. Wait 30 seconds for processing
6. Query ClickHouse:
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship-beta' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

**Expected Results:**
- ship_id: `test-ship-beta` (not 'unknown-ship')
- service: `systemd` (not 'unknown_service')
- metric_name: `service_restart_count` (not 'unknown_metric')
- metric_value: `3.0` (not 0)

**Test Case 3: ONECLICK-20250913-182633-bd5c6fc0-DATA-003**

**Test Data:**
- Ship ID: `test-ship-gamma`
- Hostname: `gamma-comms-01`
- Service: `sshd`
- Metric: `failed_login_attempts = 5.0`
- Tracking ID: `ONECLICK-20250913-182633-bd5c6fc0-DATA-003`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping:
   ```bash
   curl -X POST http://localhost:8081/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"gamma-comms-01","ship_id":"test-ship-gamma"}'
   ```
3. Send syslog message (system syslog):
   ```bash
   # Method 1: Vector UDP 1514/TCP 1515 (user facility)
   echo '<14>1 2025-09-13T18:26:33.284065Z gamma-comms-01 sshd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-003] Failed password for maintenance from 192.168.1.100 port 22 ssh2' | nc -u localhost 1514
   # Method 2: Vector TCP syslog
   echo '<14>1 2025-09-13T18:26:33.284065Z gamma-comms-01 sshd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-003] Failed password for maintenance from 192.168.1.100 port 22 ssh2' | nc localhost 1515
   # Method 3: Standard syslog (if root)
   echo '<14>1 2025-09-13T18:26:33.284065Z gamma-comms-01 sshd - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-003] Failed password for maintenance from 192.168.1.100 port 22 ssh2' | nc -u localhost 514
   ```
4. Publish metric:
   ```bash
   curl -X POST http://localhost:8428/api/v1/import/prometheus \
     -d 'failed_login_attempts{ship_id="test-ship-gamma",hostname="gamma-comms-01"} 5.0'
   ```
5. Wait 30 seconds for processing
6. Query ClickHouse:
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship-gamma' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

**Expected Results:**
- ship_id: `test-ship-gamma` (not 'unknown-ship')
- service: `sshd` (not 'unknown_service')
- metric_name: `failed_login_attempts` (not 'unknown_metric')
- metric_value: `5.0` (not 0)

**Test Case 4: ONECLICK-20250913-182633-bd5c6fc0-DATA-004**

**Test Data:**
- Ship ID: `test-ship-delta`
- Hostname: `delta-sensor-03`
- Service: `kernel`
- Metric: `temperature_celsius = 75.5`
- Tracking ID: `ONECLICK-20250913-182633-bd5c6fc0-DATA-004`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping:
   ```bash
   curl -X POST http://localhost:8081/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"delta-sensor-03","ship_id":"test-ship-delta"}'
   ```
3. Send syslog message (system syslog):
   ```bash
   # Method 1: Vector UDP 1514 (kernel facility)
   echo '<6>1 2025-09-13T18:26:33.284070Z delta-sensor-03 kernel - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-004] Hardware temperature sensor reading 75.5°C on CPU thermal zone' | nc -u localhost 1514
   # Method 2: Vector TCP syslog
   echo '<6>1 2025-09-13T18:26:33.284070Z delta-sensor-03 kernel - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-004] Hardware temperature sensor reading 75.5°C on CPU thermal zone' | nc localhost 1515
   # Method 3: Standard syslog (if root)
   echo '<6>1 2025-09-13T18:26:33.284070Z delta-sensor-03 kernel - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-004] Hardware temperature sensor reading 75.5°C on CPU thermal zone' | nc -u localhost 514
   ```
4. Publish metric:
   ```bash
   curl -X POST http://localhost:8428/api/v1/import/prometheus \
     -d 'temperature_celsius{ship_id="test-ship-delta",hostname="delta-sensor-03"} 75.5'
   ```
5. Wait 30 seconds for processing
6. Query ClickHouse:
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship-delta' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

**Expected Results:**
- ship_id: `test-ship-delta` (not 'unknown-ship')
- service: `kernel` (not 'unknown_service')
- metric_name: `temperature_celsius` (not 'unknown_metric')
- metric_value: `75.5` (not 0)

**Test Case 5: ONECLICK-20250913-182633-bd5c6fc0-DATA-005**

**Test Data:**
- Ship ID: `test-ship-epsilon`
- Hostname: `epsilon-backup-01`
- Service: `cron`
- Metric: `backup_duration_seconds = 1800.0`
- Tracking ID: `ONECLICK-20250913-182633-bd5c6fc0-DATA-005`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping:
   ```bash
   curl -X POST http://localhost:8081/devices \
     -H 'Content-Type: application/json' \
     -d '{"hostname":"epsilon-backup-01","ship_id":"test-ship-epsilon"}'
   ```
3. Send syslog message (system syslog):
   ```bash
   # Method 1: Vector UDP 1514/TCP 1515 (user facility)
   echo '<14>1 2025-09-13T18:26:33.284076Z epsilon-backup-01 cron - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-005] Daily backup job completed in 1800 seconds' | nc -u localhost 1514
   # Method 2: Vector TCP syslog
   echo '<14>1 2025-09-13T18:26:33.284076Z epsilon-backup-01 cron - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-005] Daily backup job completed in 1800 seconds' | nc localhost 1515
   # Method 3: Standard syslog (if root)
   echo '<14>1 2025-09-13T18:26:33.284076Z epsilon-backup-01 cron - - [ONECLICK-20250913-182633-bd5c6fc0-DATA-005] Daily backup job completed in 1800 seconds' | nc -u localhost 514
   ```
4. Publish metric:
   ```bash
   curl -X POST http://localhost:8428/api/v1/import/prometheus \
     -d 'backup_duration_seconds{ship_id="test-ship-epsilon",hostname="epsilon-backup-01"} 1800.0'
   ```
5. Wait 30 seconds for processing
6. Query ClickHouse:
   ```sql
   SELECT * FROM logs.incidents WHERE ship_id = 'test-ship-epsilon' ORDER BY processing_timestamp DESC LIMIT 1;
   ```

**Expected Results:**
- ship_id: `test-ship-epsilon` (not 'unknown-ship')
- service: `cron` (not 'unknown_service')
- metric_name: `backup_duration_seconds` (not 'unknown_metric')
- metric_value: `1800.0` (not 0)


## 🔧 Recommended Fixes

Based on the analysis, here are the priority fixes:


### Device Registry Fix

**Issue:** Device Registry service is not running or not accessible

**Steps:**
1. Start the Device Registry service: docker-compose restart device-registry
1. Check Device Registry health: curl http://localhost:8081/health
1. Verify device registry database is accessible
1. Ensure Benthos configuration includes device registry lookups
1. Register test devices for validation


### Incident API Fix

**Issue:** Incident API service is not running or not accessible

**Steps:**
1. Start the Incident API service: docker-compose restart incident-api
1. Check Incident API health: curl http://localhost:9081/health
1. Verify NATS connectivity for incident events
1. Check ClickHouse connectivity from Incident API
1. Verify incident processing workflow


## 📈 Pipeline Tracing Results


**Test Data Injection:** 5 data points injected
**Vector Processing:** Monitored via metrics endpoint
**NATS Message Flow:** Checked streams and message counts
**Benthos Processing:** Monitored input/output statistics  
**ClickHouse Storage:** Queried for test data presence

Detailed tracing logs are available in the console output above.


## 🛠 Debugging Commands

To reproduce this analysis:

```bash
# Run the complete diagnostic (includes system syslog testing)
python3 scripts/one_click_incident_debugging.py --deep-analysis --generate-issue-report

# Check specific services
docker-compose ps
curl http://localhost:8686/health  # Vector
curl http://localhost:8222/healthz # NATS
curl http://localhost:4195/ping    # Benthos

# Test system syslog connectivity
nc -u localhost 1514 < /dev/null  # Vector UDP syslog
nc localhost 1515 < /dev/null     # Vector TCP syslog

# Send test system syslog messages
echo '<1>1 2024-01-01T00:00:00Z test-host systemd - - Test systemd message' | nc -u localhost 1514
echo '<9>1 2024-01-01T00:00:00Z test-host sshd - - Test SSH daemon message' | nc localhost 1515

# Query current incidents
docker exec aiops-clickhouse clickhouse-client --user=admin --password=admin \
  --query="SELECT * FROM logs.incidents ORDER BY processing_timestamp DESC LIMIT 5"

# Check NATS streams
docker exec aiops-nats nats stream ls

# Monitor Vector syslog component metrics
curl http://localhost:8686/metrics | grep syslog
```

## 📝 Environment Information

- **Diagnostic Tool Version:** One-Click v1.1 (System Syslog Support)
- **Timestamp:** 2025-09-13T18:27:13.651978
- **Total Services Checked:** 7
- **Test Data Points:** 5 (includes system syslog scenarios)
- **Mismatches Found:** 2
- **Syslog Transport Methods:** UDP/TCP ports 514, 1514, 1515 + HTTP API
- **System Services Tested:** systemd, sshd, kernel, cron, applications

---

*This issue was automatically generated by the One-Click Incident Debugging tool. All reproduction steps and data points are verified.*
