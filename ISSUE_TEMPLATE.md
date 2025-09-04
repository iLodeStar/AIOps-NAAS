# AIOps NAAS Issue Report Template

**Issue ID**: ISSUE-{YYYY}{MM}{DD}-{HHMM}{SS}-{UUID}  
**Date**: {ISO 8601 Date}  
**Reporter**: {Name/Username}  
**Test Case**: TC-{NUMBER} - {Test Case Name}  
**Priority**: {Critical|High|Medium|Low}  
**Status**: {Open|In Progress|Resolved|Closed}  

---

## Issue Summary
*Brief one-line description of the issue*

## Test Case Information
- **Test Case ID**: TC-{NUMBER}
- **Test Case Name**: {Full test case name}
- **Test Phase**: {Setup|Normal Flow|Anomaly Detection|Metrics|etc.}
- **Step Number**: {X}
- **Step Description**: {What step was being executed}

## Issue Description
*Detailed description of what went wrong*

### Expected Behavior
*What should have happened according to the test guide*

### Actual Behavior  
*What actually happened instead*

### Input Used
```bash
# Command or data that was input
{Exact command or input used}
```

### Output Received
```bash
# Actual output received
{Actual output/error message received}
```

## Environment Information
- **Test Session ID**: {TEST_SESSION_ID}
- **Timestamp**: {When the issue occurred}
- **Component(s) Affected**: {Vector|ClickHouse|NATS|Benthos|etc.}
- **Docker Compose Version**: {Version}
- **Host OS**: {Linux|macOS|Windows}
- **Docker Version**: {Version}

## Evidence and Logs

### Service Health Status
```bash
# Health check results at time of issue
curl -s http://localhost:8123/ping  # ClickHouse: {Result}
curl -s http://localhost:8686/health  # Vector: {Result}
curl -s http://localhost:8428/health  # VictoriaMetrics: {Result}
curl -s http://localhost:8222/healthz  # NATS: {Result}
curl -s http://localhost:4195/ping  # Benthos: {Result}
```

### Relevant Service Logs
```bash
# Vector logs (if relevant)
docker compose logs vector --tail=20

# ClickHouse logs (if relevant)  
docker compose logs clickhouse --tail=20

# Benthos logs (if relevant)
docker compose logs benthos --tail=20

# Any other relevant service logs
```

### Vector Metrics (if applicable)
```bash
# Vector processing metrics
curl -s http://localhost:8686/metrics | grep vector_events

# Vector error metrics
curl -s http://localhost:8686/metrics | grep vector_errors
```

### Database State (if applicable)
```bash
# ClickHouse query results
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="{Query used}"

# Table row counts
docker exec aiops-clickhouse clickhouse-client --user=default --password=clickhouse123 --query="SELECT count(*) FROM logs.raw"
```

## Reproduction Steps
1. {Step 1 - Include setup requirements}
2. {Step 2 - Specific actions taken}
3. {Step 3 - Command that triggered the issue}
4. {Step 4 - Result observation}

## Impact Assessment

### Severity Justification
*Why this priority level was chosen*

### Service Impact
- **Primary Service Affected**: {Service name}
- **Secondary Services Affected**: {Other affected services}
- **Data Flow Impact**: {Which data path is broken}
- **User Impact**: {How this affects end users}

### Business Impact
- **Functionality Lost**: {What capabilities are broken}
- **Data Loss Risk**: {Yes/No - explain}
- **Security Impact**: {Any security implications}

## Investigation Notes

### Diagnostic Commands Used
```bash
# Commands used to investigate the issue
{List all diagnostic commands used}
```

### Findings
*What was discovered during investigation*

### Root Cause Analysis
*If root cause is identified, describe it here*

## Workaround
*If a temporary workaround exists, describe it*

```bash
# Workaround commands (if applicable)
{Commands to temporarily resolve}
```

## Resolution

### Resolution Steps (if resolved)
1. {Step 1}
2. {Step 2}
3. {Step 3}

### Verification Commands
```bash
# Commands used to verify the fix
{Verification commands}
```

### Resolution Notes
*Additional notes about the resolution*

### Prevention Measures
*How to prevent this issue in the future*

## Related Information

### Related Issues
- **Depends on**: {List any prerequisite issues}
- **Blocks**: {List any issues this blocks}
- **Related to**: {List any similar/related issues}

### Documentation Updates Needed
- {List any documentation that needs updating}
- {Test guide modifications required}

### Configuration Changes
```yaml
# Any configuration changes made
{Configuration snippets}
```

---

## Issue Lifecycle

### Status History
| Date | Status | Notes | Updated By |
|------|--------|-------|------------|
| {Date} | Open | Initial report | {Reporter} |
| {Date} | In Progress | Investigation started | {Assignee} |
| {Date} | Resolved | Issue fixed | {Resolver} |

### Time Tracking
- **Time to Reproduce**: {Minutes}
- **Time to Diagnose**: {Minutes}  
- **Time to Resolve**: {Minutes}
- **Total Time**: {Minutes}

---

## Additional Notes
*Any other relevant information*

---

**Template Usage Instructions:**
1. Replace all `{placeholder}` values with actual information
2. Remove sections that are not applicable
3. Include all relevant logs and evidence
4. Use clear, specific descriptions
5. Attach screenshots if helpful
6. Update status as issue progresses