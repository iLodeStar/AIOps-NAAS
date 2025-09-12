# One-Click Incident Debugging Implementation Summary

## What Was Created

### 🎯 Main Script: `scripts/one_click_incident_debugging.py`
- **Complete end-to-end diagnostic tool** that addresses all requested requirements
- **Test data generation**: Creates 3 trackable test scenarios with unique IDs
- **Pipeline tracking**: Follows data through Vector → NATS → Benthos → ClickHouse
- **Mismatch identification**: Compares expected vs actual values for each field
- **Automated reporting**: Generates GitHub-ready issue reports
- **Service health checks**: Validates all pipeline components

### 🖥 Interactive Interface: `scripts/one_click_debug.sh`
- **User-friendly menu system** with 6 options
- **Automatic prerequisites checking** (Docker Compose, Python dependencies)
- **Service status validation** before running diagnostics
- **Advanced options** including NATS CLI installation
- **Help and documentation** built-in

### 🐳 Docker Integration: NATS CLI Support
- **Custom NATS Dockerfile** (`nats/Dockerfile`) that includes NATS CLI
- **Updated docker-compose.yml** to build custom NATS image with debugging tools
- **Automatic CLI installation** via the diagnostic tool if not present

### 📚 Comprehensive Documentation
- **`ONE_CLICK_INCIDENT_DEBUGGING_README.md`**: Complete user guide
- **Makefile integration**: Added `make debug-incident` command
- **Sample outputs and examples** for all diagnostic modes

## Key Features Implemented

### ✅ 1. Test Data Generation
```python
# Creates 3 realistic test scenarios:
- Test Ship Alpha: Navigation system GPS accuracy issue
- Test Ship Beta: Engine monitoring fuel pressure drop  
- Test Ship Gamma: Communication system signal strength degradation

# Each with:
- Unique tracking ID (ONECLICK-{timestamp}-DATA-{number})
- Expected ship_id, service, metric_name, metric_value
- Hostname mapping for device registry
- Structured log message with tracking ID
```

### ✅ 2. End-to-End Pipeline Tracking
```bash
Log Injection → Vector Monitoring → NATS Stream Analysis → Benthos Processing → ClickHouse Validation
```

**Vector Tracking:**
- HTTP metrics endpoint monitoring
- Component activity analysis
- Log parsing verification

**NATS Tracking:**
- Stream listing and inspection
- Message flow monitoring with CLI commands
- Real-time activity tracking

**Benthos Tracking:**
- Processing statistics monitoring
- Input/output count verification
- Stream transformation analysis

**ClickHouse Tracking:**
- Direct SQL queries for test data
- Field-by-field validation
- Fallback value detection

### ✅ 3. Mismatch Data Points Analysis
```python
# Identifies specific mismatches:
DataMismatch(
    field_name='ship_id',
    expected_value='test-ship-alpha',
    actual_value='unknown-ship', 
    service_responsible='Device Registry',
    root_cause='Hostname to ship_id mapping missing',
    fix_steps=['Verify device registry is running', ...]
)
```

### ✅ 4. Reproduction Steps with Data Points
```markdown
**Test Case 1: ONECLICK-20240312-143052-DATA-001**

**Test Data:**
- Ship ID: `test-ship-alpha`
- Hostname: `alpha-bridge-01`
- Service: `navigation_system`
- Metric: `gps_accuracy_meters = 2.5`

**Reproduction Steps:**
1. Start all services: `docker-compose up -d`
2. Register device mapping: `curl -X POST http://localhost:8091/devices...`
3. Send syslog message: `echo '<134>1...' | nc localhost 514`
4. Publish metric: `curl -X POST http://localhost:8428/api/v1/import/prometheus...`
5. Query results: `SELECT * FROM logs.incidents WHERE...`

**Expected vs Actual:** Clear comparison table
```

### ✅ 5. Automated GitHub Issue Report
```markdown
# Complete GitHub-ready issue with:
- Executive summary of issues found
- Service health status table
- Data mismatch analysis with root causes  
- Test data generation details
- Reproduction steps with exact commands
- Recommended fixes prioritized by impact
- Debugging commands for manual investigation
- Environment information and metadata
```

### ✅ 6. NATS CLI Integration
```dockerfile
# Custom NATS image with CLI tools
FROM nats:alpine
RUN curl -sf https://binaries.nats.dev/nats-io/nats/v2@latest | sh && \
    mv nats /usr/local/bin/
```

```bash
# Available debugging commands:
docker exec aiops-nats nats stream ls
docker exec aiops-nats nats stream view STREAM_NAME
docker exec aiops-nats nats stream info STREAM_NAME  
```

## Usage Examples

### Quick Start (Interactive)
```bash
./scripts/one_click_debug.sh
# → Select option 1 for quick diagnostic
# → Select option 3 for full GitHub report
```

### Direct Python Execution
```bash
# Quick diagnostic (2-3 minutes)
python3 scripts/one_click_incident_debugging.py

# Deep analysis (5-7 minutes)  
python3 scripts/one_click_incident_debugging.py --deep-analysis

# Full report generation
python3 scripts/one_click_incident_debugging.py --deep-analysis --generate-issue-report
```

### Makefile Integration
```bash
make debug-incident  # Launches interactive tool
```

## Sample Output Files

### Console Output
```
🚀 ONE-CLICK INCIDENT DEBUGGING SESSION: ONECLICK-20240312-143052-a1b2c3d4
========================================================================

📋 STEP 1: SERVICE HEALTH CHECKS
✅ Vector: HTTP 200
✅ ClickHouse: Connected with admin/admin  
✅ NATS: HTTP 200

🧪 STEP 2: GENERATE TRACKABLE TEST DATA
📝 Generated: ONECLICK-20240312-143052-DATA-001 -> test-ship-alpha/navigation_system

📤 STEP 3: INJECT TEST DATA INTO PIPELINE
✅ Device registered: alpha-bridge-01 -> test-ship-alpha
✅ Anomaly detection triggered: ONECLICK-20240312-143052-DATA-001

🔍 STEP 4: TRACK DATA THROUGH SERVICES  
✅ Found in Vector metrics: ONECLICK-20240312-143052-DATA-001
❌ Not found in ClickHouse: ship_id shows 'unknown-ship'

❌ STEP 6: IDENTIFY DATA MISMATCHES
⚠️ Fallback values detected: ship_id, service, metric_name
```

### Generated Issue File
```
INCIDENT_DATA_ISSUE_REPORT_20240312_143052.md
```
→ Complete GitHub-ready issue with reproduction steps

## Technical Implementation Details

### Architecture
```python
class OneClickIncidentDebugger:
    def run_complete_diagnostic(self):
        self._setup_nats_cli()           # Install NATS CLI
        self._perform_health_checks()    # Check all services
        self._generate_test_data()       # Create trackable data
        self._inject_test_data()         # Send through pipeline
        self._track_data_through_services()  # Monitor processing
        self._analyze_current_incidents()    # Check existing data
        self._identify_data_mismatches()     # Find problems  
        self._generate_reproduction_steps()  # Create repro guide
        self._generate_github_issue()        # Create issue report
```

### Service Integration
- **Vector**: HTTP metrics API (`localhost:8686/metrics`)
- **NATS**: HTTP monitoring + CLI commands (`localhost:8222`, `nats` CLI)
- **Benthos**: Stats API (`localhost:4195/stats`)
- **ClickHouse**: Direct SQL queries with credential auto-detection
- **Victoria Metrics**: Prometheus import API (`localhost:8428/api/v1/import/prometheus`)
- **Device Registry**: REST API (`localhost:8091/devices`)
- **Incident API**: REST API (`localhost:9081/health`)

### Error Handling
- **Graceful degradation**: Continues diagnostic even if some services are down
- **Credential auto-detection**: Tries multiple ClickHouse credential combinations
- **Timeout management**: All HTTP requests have 10-15 second timeouts
- **Fallback reporting**: Generates partial reports if full diagnostic fails

## Benefits Delivered

### ✅ All Requested Features Implemented
1. **✅ Generate test data**: 3 comprehensive test scenarios with tracking IDs
2. **✅ Track through each service**: Complete pipeline monitoring Vector → NATS → Benthos → ClickHouse  
3. **✅ Provide mismatch data points**: Field-by-field comparison with root cause analysis
4. **✅ Issue reproduction steps**: Exact commands with specific data points
5. **✅ Automated GitHub report**: Copy-paste ready issue content
6. **✅ NATS CLI included**: Custom Docker image with debugging tools

### Additional Value Added
- **Interactive user interface** for ease of use
- **Multiple diagnostic modes** (quick/deep/full report)
- **Comprehensive documentation** with examples
- **Makefile integration** for workflow convenience
- **Automated service health validation**
- **Production-safe design** with read-only analysis options

## Files Created/Modified

### New Files
- `scripts/one_click_incident_debugging.py` - Main diagnostic engine
- `scripts/one_click_debug.sh` - Interactive shell interface  
- `nats/Dockerfile` - Custom NATS image with CLI
- `ONE_CLICK_INCIDENT_DEBUGGING_README.md` - Complete documentation

### Modified Files  
- `docker-compose.yml` - Updated NATS service to use custom build
- `Makefile` - Added `debug-incident` target

### Generated Files (Runtime)
- `INCIDENT_DATA_ISSUE_REPORT_YYYYMMDD_HHMMSS.md` - GitHub issue reports

---

**Result**: Complete one-click solution that addresses all requirements while providing additional value through user-friendly interfaces and comprehensive documentation.