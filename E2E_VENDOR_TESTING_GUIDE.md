# E2E Vendor Testing Guide

## Overview

This guide covers the comprehensive E2E testing infrastructure for unified network log normalization in the AIOps NAAS platform. The testing suite validates both the existing remediation pipeline and the new multi-vendor log parsing capabilities.

## Test Suite Architecture

### Test Components

1. **Original E2E Test** (`e2e_test.py`)
   - Tests: Alert → Policy → Approval → Execution → Audit pipeline
   - Focus: Remediation workflow and decision-making process
   - Scenarios: Satellite degradation, weather impact, network congestion, equipment failure

2. **Vendor Log Parsing E2E Test** (`test_e2e_vendor_log_parsing.py`) ⭐ **NEW**
   - Tests: Network Devices → Vector → ClickHouse log parsing pipeline
   - Focus: Multi-vendor log format parsing and normalization
   - Coverage: 20+ network equipment vendors and device types

3. **Backward Compatibility Test** (`test_e2e_backward_compatibility.py`)
   - Tests: Existing functionality remains unaffected by vendor parsing changes
   - Focus: Schema compatibility, query compatibility, configuration validation

4. **Comprehensive Test Suite** (`test_e2e_comprehensive.py`) ⭐ **NEW**
   - Orchestrates all test components together
   - Provides unified reporting and success metrics
   - Includes performance benchmarking and recommendations

## Supported Vendors and Test Coverage

### Network Equipment Vendors
- **Cisco** - IOS, IOS-XE, NX-OS, IOS-XR, AireOS (WLC), ASA firewalls
- **Juniper** - Junos OS (EX, MX, SRX, PTX, ACX series)
- **Fortinet** - FortiOS (FortiGate, FortiSwitch, FortiAP)
- **Palo Alto Networks** - PAN-OS firewalls
- **HPE/Aruba** - AOS switches, wireless controllers, access points
- **Microsoft** - Windows Event Logs (JSON format)
- **Generic** - SNMP-based and syslog-compliant devices

### Device Types Tested
- Switches (core, distribution, access)
- Routers (WAN, LAN, BGP)
- Firewalls (next-gen, UTM)
- Wireless controllers and access points
- VSAT terminals
- Servers (Windows, Linux)

### Log Formats Validated
- RFC 3164 (legacy syslog)
- RFC 5424 (modern structured syslog)
- JSON structured logs
- Key=Value vendor formats
- Proprietary vendor formats

## Running Tests

### Quick Validation
```bash
# Validate test infrastructure
./validate_e2e_vendor_tests.sh
```

### Individual Test Components
```bash
# Run vendor log parsing tests only
python3 test_e2e_vendor_log_parsing.py

# Run backward compatibility tests only  
python3 test_e2e_backward_compatibility.py

# Run original remediation pipeline tests only
python3 e2e_test.py
```

### Comprehensive Test Suite (Recommended)
```bash
# Run complete E2E test suite
python3 test_e2e_comprehensive.py

# View detailed results
cat comprehensive_e2e_results.json
```

## Test Scenarios

### Vendor Log Parsing Test Scenarios

1. **Cisco IOS Interface Events**
   ```
   %LINK-3-UPDOWN: Interface GigabitEthernet1/1, changed state to up
   Expected: vendor=cisco, device_type=switch, severity=error, facility=LINK
   ```

2. **Cisco ASA Firewall Connections**
   ```
   %ASA-6-302014: Teardown TCP connection 123456 for outside:192.168.1.100/443
   Expected: vendor=cisco, device_type=firewall, event_id=302014
   ```

3. **Juniper BGP State Changes**
   ```
   rpd.info: BGP peer 10.1.1.1 (External AS 65001) changed state from Established to Idle
   Expected: vendor=juniper, facility=rpd, severity=info, category=bgp
   ```

4. **Fortinet Traffic Logs**
   ```
   logid="0000000013" type="traffic" subtype="forward" action="accept"
   Expected: vendor=fortinet, category=traffic, event_id=0000000013
   ```

5. **Aruba Wireless Events**
   ```
   Station aa:bb:cc:dd:ee:ff associated to AP ap-guest-01 on channel 6
   Expected: vendor=aruba, device_type=wireless_controller, category=wireless
   ```

6. **Windows Security Events**
   ```
   {"event_id":"4624","message":"User login successful","source":"Microsoft-Windows-Security-Auditing"}
   Expected: vendor=microsoft, event_id=4624, category=security
   ```

### Device Classification Test Scenarios

Tests hostname-based device type and cruise segment classification:

- `sw-bridge-01` → switch, navigation
- `rtr-engine-main` → router, propulsion  
- `fw-security-01` → firewall, safety
- `wlc-guest-wifi` → wireless_controller, guest_services
- `ap-deck-12` → access_point, deck_operations
- `server-pos-01` → server, guest_services

### Backward Compatibility Test Scenarios

1. **Schema Compatibility**: All new ClickHouse fields have DEFAULT values
2. **Query Compatibility**: Existing anomaly detection queries remain functional
3. **Vector Configuration**: Enhanced config maintains existing functionality
4. **Service Integration**: Link health, incident API, and remediation services unaffected

## Expected Test Results

### Success Criteria

- **Overall Success Rate**: ≥80% for production readiness
- **Vendor Parsing**: ≥80% of vendor-specific logs correctly parsed
- **Device Classification**: ≥80% of devices correctly classified
- **Backward Compatibility**: 100% (all existing functionality must work)
- **Performance**: Average processing time <100ms per log

### Test Output Example

```
📊 COMPREHENSIVE E2E TEST SUITE SUMMARY
================================================================================
Suite Run ID: comprehensive_e2e_1705327825
Total Duration: 45.2s
Overall Success Rate: 95.0%
Tests Passed: 3/3

📋 Test Component Results:
   ✅ PASSED     Remediation Pipeline (15.4s)
                Alert->Policy->Approval->Execution->Audit pipeline working correctly
   ✅ PASSED     Vendor Log Parsing (22.8s)
                Multi-vendor log parsing and normalization working correctly
   ✅ PASSED     Backward Compatibility (7.0s)
                All changes are backward compatible with existing systems

🎯 Test Coverage:
   ✅ Remediation Pipeline (Alert->Policy->Approval->Execution->Audit)
   ✅ Multi-Vendor Log Parsing (Cisco, Juniper, Fortinet, Aruba, Microsoft)
   ✅ Device Classification & Cruise Segment Mapping
   ✅ ClickHouse Schema Backward Compatibility
   ✅ Vector Configuration Validation
   ✅ End-to-End Data Flow (Network -> Vector -> ClickHouse)

🎉 EXCELLENT! All systems working optimally.
   ✅ Ready for production deployment
```

## Troubleshooting

### Common Issues

1. **Syslog Port Permission Denied**
   ```bash
   # Run tests as user with appropriate permissions, or use alternative port
   # Tests default to localhost:514 but can be configured
   ```

2. **Vector Not Running**
   ```bash
   # Ensure Vector service is running for realistic testing
   docker-compose up vector
   ```

3. **ClickHouse Connection Issues**
   ```bash
   # Ensure ClickHouse is accessible for integration testing
   docker-compose up clickhouse
   ```

### Debug Mode
```bash
# Run with verbose logging for debugging
export PYTHONPATH=.
python3 -u test_e2e_vendor_log_parsing.py 2>&1 | tee debug.log
```

### Performance Tuning

Monitor test performance metrics:
- **Processing Time**: Average time per log message
- **Throughput**: Messages processed per second
- **Memory Usage**: Peak memory during test execution
- **Error Rates**: Parsing failures per vendor

## Integration with CI/CD

### GitHub Actions Integration
```yaml
- name: Run E2E Vendor Tests
  run: |
    python3 test_e2e_comprehensive.py
    if [ $? -eq 0 ]; then
      echo "✅ All E2E tests passed - ready for deployment"
    else
      echo "❌ E2E tests failed - blocking deployment"
      exit 1
    fi
```

### Production Deployment Gate
Use comprehensive test results as deployment gate:
- Success rate ≥95%: Automatic deployment approved
- Success rate 80-94%: Manual approval required  
- Success rate <80%: Deployment blocked

## File Structure

```
/home/runner/work/AIOps-NAAS/AIOps-NAAS/
├── e2e_test.py                           # Original remediation pipeline E2E test
├── test_e2e_vendor_log_parsing.py       # New vendor log parsing E2E test
├── test_e2e_backward_compatibility.py   # Backward compatibility validation
├── test_e2e_comprehensive.py           # Comprehensive test suite orchestrator
├── validate_e2e_vendor_tests.sh        # Quick validation script
├── E2E_VENDOR_TESTING_GUIDE.md         # This documentation
├── configs/
│   ├── vendor-log-patterns.yaml        # Vendor-specific parsing patterns
│   ├── vendor-integrations.yaml        # Device inventory and integration config
│   └── network-devices.yaml            # Network device monitoring config
├── vector/vector.toml                   # Enhanced Vector configuration
└── clickhouse/
    ├── init.sql                         # Extended schema with vendor fields
    └── migrate_schema_vendor_support.sql # Migration script
```

## Next Steps

1. **Customize Vendor Patterns**: Update `configs/vendor-log-patterns.yaml` for your specific devices
2. **Configure Device Inventory**: Update `configs/vendor-integrations.yaml` with your network devices
3. **Run Validation**: Execute `./validate_e2e_vendor_tests.sh` to verify setup
4. **Execute Comprehensive Tests**: Run `python3 test_e2e_comprehensive.py` for full validation
5. **Monitor Results**: Review `comprehensive_e2e_results.json` for detailed metrics
6. **Integrate with CI/CD**: Add tests to your deployment pipeline

## Support

For issues with E2E vendor testing:
1. Check test logs in `*_results.json` files
2. Verify vendor configurations in `configs/` directory  
3. Validate Vector and ClickHouse connectivity
4. Review firewall settings for syslog traffic
5. Consult `docs/unified-network-log-normalization.md` for detailed architecture information