# AIOps NAAS Testing Documentation Summary

## 📋 Documentation Overview

This comprehensive testing suite provides step-by-step validation for the complete AIOps NAAS data pipeline from ingestion to incident creation.

### 📁 Created Files

| File | Purpose | Description |
|------|---------|-------------|
| `COMPREHENSIVE_STEP_BY_STEP_TESTING_GUIDE.md` | **Main Testing Guide** | Complete step-by-step testing procedures for all data flows |
| `scripts/comprehensive_test_execution.sh` | **Testing Assistant** | Interactive script to assist with manual testing execution |
| `ISSUE_TEMPLATE.md` | **Issue Reporting** | Standardized template for documenting and tracking issues |

---

## 🎯 Test Cases Covered

### **TC-001: Normal Syslog Flow (UDP/TCP)**
**One-line**: Validates basic syslog message processing through Vector to ClickHouse storage  
**Achievement**: Ensures operational messages are properly ingested and stored without triggering anomaly detection

### **TC-002: Anomaly Detection Flow**  
**One-line**: Validates anomaly detection and complete correlation pipeline activation  
**Achievement**: Ensures error messages trigger anomaly detection, correlation, and incident creation

### **TC-003: Host Metrics Flow**
**One-line**: Validates system metrics collection and storage in both ClickHouse and VictoriaMetrics  
**Achievement**: Ensures host monitoring data flows correctly for operational visibility

### **TC-004: SNMP Network Data Flow**
**One-line**: Validates network device monitoring via SNMP collector through NATS to storage  
**Achievement**: Ensures network infrastructure monitoring and anomaly detection for devices

### **TC-005: File-based Log Flow**
**One-line**: Validates file log ingestion from mounted volumes with rotation handling  
**Achievement**: Ensures application log files are processed correctly with no data loss

### **TC-006: End-to-End Incident Correlation**
**One-line**: Validates complete incident lifecycle with correlation, deduplication, and suppression  
**Achievement**: Ensures multiple related events are correlated into single incidents with proper rules

---

## 🔄 Data Flow Paths Validated

### **Normal Flow Path**
```
Syslog (UDP/TCP) → Vector → ClickHouse → Storage
```
**Input**: Standard operational syslog messages  
**Output**: Messages stored in ClickHouse logs.raw table  
**Validation**: Query ClickHouse for stored messages with session ID

### **Anomaly Detection Path**
```
Syslog → Vector → ClickHouse → VictoriaMetrics → Anomaly Detection → NATS → Benthos → Incidents
```
**Input**: Error/critical syslog messages  
**Output**: Incidents created via API with correlation details  
**Validation**: Query incident API for created incidents

### **Host Metrics Path**
```
Host Metrics → Vector → ClickHouse & VictoriaMetrics
```
**Input**: System CPU, memory, disk, network metrics  
**Output**: Metrics available in both storage systems  
**Validation**: Query both ClickHouse and VictoriaMetrics for metrics

### **SNMP Network Path**
```
Network Devices → SNMP Collector → NATS → Vector → ClickHouse
```
**Input**: Network device SNMP data  
**Output**: Network telemetry stored for analysis  
**Validation**: Query ClickHouse for SNMP source data

### **File Logs Path**
```
Log Files → Vector → ClickHouse
```
**Input**: Application log files in mounted volumes  
**Output**: File log entries stored with proper metadata  
**Validation**: Query ClickHouse for file source entries

---

## 📊 Execution Plans

### **Individual Test Execution (Per Test Case)**
1. **Setup Phase** (5 min): Verify service health and generate session ID
2. **Execution Phase** (10-15 min): Run test steps with input/output validation
3. **Validation Phase** (5 min): Verify results in storage and downstream systems
4. **Documentation Phase** (5 min): Record results and any issues

### **Complete Test Suite Execution (2 hours)**
1. **Phase 1: Environment Setup** (15 min) - Health checks and baseline validation
2. **Phase 2: Individual Flows** (45 min) - TC-001, TC-003, TC-004, TC-005
3. **Phase 3: Advanced Flows** (30 min) - TC-002, TC-006 with correlation
4. **Phase 4: Edge Cases** (20 min) - Performance, failure simulation, recovery
5. **Phase 5: Results** (10 min) - Compilation, analysis, recommendations

### **Correlation and Rules Configuration**
- **Benthos Correlation Rules**: Modify correlation patterns and thresholds
- **Suppression Configuration**: Adjust duplicate detection and suppression windows
- **Incident Classification**: Update incident types and severity mappings
- **Testing New Rules**: Validate custom correlation patterns work correctly

---

## 🔧 Key Features

### **Manual Step-by-Step Approach**
- **No automated scripts** - All steps executed manually for precise validation
- **Command-by-command execution** - Each command provided with expected output
- **Interactive validation** - Manual verification of each step result
- **Real console evidence** - Actual command outputs documented

### **Comprehensive Input/Output Validation**
- **Input specification** - Exact commands and data for each step
- **Output specification** - Expected results with example outputs
- **Validation criteria** - How to verify step success/failure
- **Evidence capture** - Commands to capture proof of results

### **End-to-End Message Tracking**
- **Unique session IDs** - Track individual messages through entire pipeline
- **Multi-service tracking** - Follow messages across Vector, ClickHouse, NATS, Benthos
- **Correlation validation** - Verify related events are properly correlated
- **Incident lifecycle** - Track from anomaly detection to incident creation

### **Issue Management Framework**
- **Standardized reporting** - Consistent issue template with all required information
- **Root cause analysis** - Structured approach to problem investigation
- **Resolution tracking** - Document fixes and prevention measures
- **Knowledge base** - Build repository of known issues and solutions

---

## 🎯 Success Criteria

### **Per Test Case Success**
- ✅ All test steps complete without errors
- ✅ Input/output validation confirms expected behavior
- ✅ Data flows correctly through all components
- ✅ No data loss or processing failures
- ✅ Performance within acceptable ranges

### **Overall Suite Success**  
- ✅ 100% service health checks pass
- ✅ All 6 test cases pass validation
- ✅ End-to-end message tracking functional
- ✅ Anomaly detection and correlation operational
- ✅ No critical issues identified
- ✅ Complete documentation of results

---

## 🚀 Getting Started

### **Quick Start for Testing**
1. **Read the main guide**: `COMPREHENSIVE_STEP_BY_STEP_TESTING_GUIDE.md`
2. **Use the assistant**: Run `./scripts/comprehensive_test_execution.sh`
3. **Follow step-by-step**: Execute each command manually and validate results
4. **Document issues**: Use `ISSUE_TEMPLATE.md` for any problems found

### **For Issue Reporting**
1. **Use the template**: Copy `ISSUE_TEMPLATE.md` for consistent reporting
2. **Include evidence**: Capture logs, commands, and outputs
3. **Provide context**: Include test session ID and environment details
4. **Track resolution**: Update issue status as work progresses

### **For Correlation Rules**
1. **Review current rules**: Check Benthos configuration
2. **Test modifications**: Use TC-006 to validate new correlation patterns
3. **Document changes**: Update configuration and test results
4. **Validate impact**: Ensure changes don't break existing functionality

---

## 📈 Benefits

### **For Development Teams**
- **Confidence in deployments** - Validated end-to-end functionality
- **Issue prevention** - Catch problems before production
- **Knowledge building** - Understand complete system behavior
- **Documentation** - Clear procedures for troubleshooting

### **For Operations Teams**
- **Troubleshooting guide** - Step-by-step diagnostic procedures  
- **Performance baselines** - Known good metrics and behaviors
- **Incident response** - Validated correlation and alerting
- **System validation** - Confirm proper configuration

### **For Quality Assurance**
- **Test automation** - Repeatable validation procedures
- **Regression prevention** - Catch functional regressions
- **Performance monitoring** - Validate system performance
- **Documentation quality** - Ensure procedures are accurate

This comprehensive testing framework ensures the AIOps NAAS platform functions correctly end-to-end, with precise validation procedures and structured issue management for continuous improvement.